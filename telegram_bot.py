"""
Módulo de control remoto de JARVIS vía Telegram
Permite enviar órdenes desde el móvil y recibir respuestas
Con estética cyberpunk, botones, formato y "escribiendo..."
"""
import threading
import time
import requests

# ─── CONFIGURACIÓN ───────────────────────
# El token y el chat ID se leen de la configuración del usuario (config.json)
from configuracion import cargar_config
_CONFIG = cargar_config()

TOKEN = _CONFIG.get("telegram_token", "")
# Solo este Chat ID puede controlar JARVIS (seguridad)
try:
    CHAT_ID_AUTORIZADO = int(_CONFIG.get("telegram_chat_id", "0") or 0)
except (ValueError, TypeError):
    CHAT_ID_AUTORIZADO = 0

API = f"https://api.telegram.org/bot{TOKEN}"

# Callback que ejecuta una orden en JARVIS (se asigna desde jarvis.py)
_procesar_orden = None
_log_fn = None

_running = False
_ultimo_update = 0
_apagado_pendiente = False  # esperando confirmación para apagar el PC

# ─── TECLADO DE ACCESO RÁPIDO ────────────
# Botones fijos abajo del chat. Tocarlos envía ese texto como mensaje.
TECLADO = {
    "keyboard": [
        # Sonido
        ["🔇 Silenciar", "🔊 Activar sonido"],
        ["🔉 Volumen 30", "🔊 Volumen 50", "🔊 Volumen máx"],
        # Sistema / PC
        ["💻 Info PC", "🌡 Temperatura"],
        ["⚙ Procesos", "📊 Memoria", "🌐 Conexión"],
        # Comunicación
        ["📬 Correos", "⏰ Notificaciones"],
        # Calendario
        ["📅 Eventos hoy", "📆 Eventos mañana"],
        # Multimedia / captura
        ["📸 Captura", "📷 Webcam", "🖥 Compartir PC"],
        # Juegos / Minecraft
        ["🎮 Qué juego", "💾 Backup mundo"],
        ["🟢 Abrir servidor", "🔴 Cerrar servidor"],
        # Fútbol + hora/tiempo
        ["⚽ Fútbol", "🕐 Hora", "🌤 Tiempo"],
        # Seguridad / red
        ["📡 Escanear red", "🔌 Puertos", "🔗 Conexiones"],
        # Kali
        ["🐉 Arrancar Kali", "🛑 Apagar Kali", "🧪 Prueba Kali"],
        ["⏎ Enter", "✖️ Ctrl+C"],
        # Energía / ayuda
        ["⛔ Apagar PC", "❓ Ayuda"],
    ],
    "resize_keyboard": True,
    "persistent": True,
}

# Mapa de los botones a las órdenes reales que entiende JARVIS
ATAJOS = {
    # Sonido
    "🔇 silenciar": "silencia",
    "🔊 activar sonido": "activa el sonido",
    "🔉 volumen 30": "pon el volumen al 30",
    "🔊 volumen 50": "pon el volumen al 50",
    "🔊 volumen máx": "pon el volumen al máximo",
    # Sistema / PC
    "💻 info pc": "información de mi pc",
    "🌡 temperatura": "¿cuál es la temperatura del pc?",
    "⚙ procesos": "qué procesos tengo abiertos",
    "📊 memoria": "qué consume más memoria",
    "🌐 conexión": "cómo está mi conexión",
    # Comunicación
    "📬 correos": "¿qué correos tengo?",
    "⏰ notificaciones": "lee mis notificaciones",
    # Calendario
    "📅 eventos hoy": "qué eventos tengo hoy",
    "📆 eventos mañana": "qué eventos tengo mañana",
    # Multimedia / captura
    "📸 captura": "mándame una captura",
    "📷 webcam": "hazme una foto",
    "🖥 compartir pc": "comparte mi pc",
    # Juegos / Minecraft
    "🎮 qué juego": "a qué juego estoy jugando",
    "💾 backup mundo": "haz backup del mundo",
    "🟢 abrir servidor": "abre el servidor de minecraft",
    "🔴 cerrar servidor": "cierra el servidor de minecraft",
    # Fútbol + hora/tiempo
    "⚽ fútbol": "resultados de fútbol de hoy",
    "🕐 hora": "qué hora es",
    "🌤 tiempo": "qué tiempo hace",
    # Seguridad / red
    "📡 escanear red": "escanea mi red",
    "🔌 puertos": "qué puertos tengo abiertos",
    "🔗 conexiones": "conexiones activas",
    # Kali
    "🐉 arrancar kali": "arranca la kali",
    "🛑 apagar kali": "apaga la kali",
    "🧪 prueba kali": "prueba la kali",
    "⏎ enter": "kali enter",
    "✖️ ctrl+c": "kali ctrl c",
    # Energía / ayuda
    "⛔ apagar pc": "__APAGAR_PC__",
    "❓ ayuda": "/help",
}


def _log(msg):
    if _log_fn:
        _log_fn(msg, "system")
    else:
        print(f"[Telegram] {msg}")


def _escribiendo(chat_id=None):
    """Muestra 'JARVIS está escribiendo...' mientras procesa."""
    destino = chat_id or CHAT_ID_AUTORIZADO
    try:
        requests.post(f"{API}/sendChatAction",
                      json={"chat_id": destino, "action": "typing"}, timeout=5)
    except Exception:
        pass


def _icono_para(texto):
    """Devuelve un emoji según el contenido de la respuesta."""
    t = texto.lower()
    if any(p in t for p in ['volumen', 'silenc', 'sonido']):
        return "🔊"
    if any(p in t for p in ['correo', 'email', 'gmail']):
        return "📬"
    if any(p in t for p in ['evento', 'calendario', 'recordatorio']):
        return "📅"
    if any(p in t for p in ['imagen', 'generad']):
        return "🎨"
    if any(p in t for p in ['captura', 'pantalla']):
        return "📸"
    if any(p in t for p in ['juego', 'jugando', 'minecraft', 'servidor']):
        return "🎮"
    if any(p in t for p in ['whatsapp', 'mensaje enviado']):
        return "💬"
    if any(p in t for p in ['parsec', 'compartiendo', 'compartir']):
        return "🖥"
    if any(p in t for p in ['proceso', 'memoria', 'cpu', 'gpu', 'temperatura', 'ram']):
        return "💻"
    if any(p in t for p in ['papelera', 'borrado', 'eliminado']):
        return "🗑"
    if any(p in t for p in ['archivo', 'carpeta', 'documento']):
        return "📁"
    if any(p in t for p in ['error', 'no pude', 'no encontré', 'no entendí']):
        return "⚠️"
    return "◈"


def enviar_mensaje(texto, chat_id=None, con_teclado=True):
    """Envía un mensaje de texto por Telegram, con formato e icono."""
    destino = chat_id or CHAT_ID_AUTORIZADO
    try:
        if len(texto) > 3900:
            texto = texto[:3900] + "\n\n_[...mensaje cortado]_"

        # Añadir icono al principio si no es ya un mensaje decorado
        _ya_decorado = (texto.startswith(('◈', '🟢', '⚡', '╔', '┌', '🎨', '📸', '📡', '⚙',
                        '📁', '🔢', '🎮', '🛠', '📱', '⛔', '✓')) or texto.startswith('```'))
        if not _ya_decorado:
            icono = _icono_para(texto)
            texto = f"{icono} {texto}"

        payload = {
            "chat_id": destino,
            "text": texto,
            "parse_mode": "Markdown",
        }
        if con_teclado:
            payload["reply_markup"] = TECLADO

        r = requests.post(f"{API}/sendMessage", json=payload, timeout=10)
        # Si Markdown falla (caracteres raros), reenviar sin formato
        if not r.json().get("ok"):
            payload.pop("parse_mode", None)
            requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        _log(f"Error enviando mensaje: {e}")


def enviar_foto(ruta_imagen, caption="", chat_id=None):
    """Envía una imagen por Telegram."""
    destino = chat_id or CHAT_ID_AUTORIZADO
    try:
        with open(ruta_imagen, 'rb') as f:
            requests.post(f"{API}/sendPhoto",
                data={"chat_id": destino, "caption": caption},
                files={"photo": f}, timeout=30)
        return True
    except Exception as e:
        _log(f"Error enviando foto: {e}")
        return False


def enviar_documento(ruta_archivo, caption="", chat_id=None):
    """Envía un archivo cualquiera por Telegram."""
    destino = chat_id or CHAT_ID_AUTORIZADO
    try:
        with open(ruta_archivo, 'rb') as f:
            requests.post(f"{API}/sendDocument",
                data={"chat_id": destino, "caption": caption},
                files={"document": f}, timeout=60)
        return True
    except Exception as e:
        _log(f"Error enviando documento: {e}")
        return False


def _mensaje_bienvenida():
    """Devuelve la guía completa dividida en partes (Telegram limita a 4096 chars)."""
    partes = []

    partes.append(
        "```\n"
        "  \u25c8 J\u00b7A\u00b7R\u00b7V\u00b7I\u00b7S \u25c8\n"
        "  GU\u00cdA DE INSTRUCCIONES\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "```\n"
        "Por *voz* pulsa `F9` y habla. O escr\u00edbeme aqu\u00ed por *Telegram*.\n\n"
        "\ud83d\udce1 *COMUNICACI\u00d3N*\n\n"
        "_WhatsApp_\n"
        "\u2022 `Manda un WhatsApp a papá diciendo llego tarde`\n"
        "\u2022 Contactos: los que tengas guardados en tu móvil\n\n"
        "_Llamadas_\n"
        "\u2022 `Llama a [contacto]`\n\n"
        "_Notificaciones_\n"
        "\u2022 `Lee mis notificaciones`\n\n"
        "_Gmail_\n"
        "\u2022 `\u00bfCu\u00e1l es mi \u00faltimo correo?`\n"
        "\u2022 `\u00bfTengo correos nuevos?`\n\n"
        "_Google Calendar_\n"
        "\u2022 `Crea un evento hoy a las 8 de la tarde llamado cena`\n"
        "\u2022 `Recu\u00e9rdame algo el lunes a las 10`\n"
        "\u2022 `\u00bfQu\u00e9 eventos tengo hoy?`\n"
        "\u2022 `Borra el evento futbol\u00edn` \u2192 confirmas\n\n"
        "\u2022 `\u00bfQu\u00e9 eventos tengo ma\u00f1ana?`"
    )

    partes.append(
        "\u2699 *SISTEMA / PC*\n\n"
        "_Volumen_\n"
        "\u2022 `Pon el volumen al 50`\n"
        "\u2022 `Sube / baja el volumen` \u00b7 `Volumen al m\u00e1ximo`\n"
        "\u2022 `Silencia` / `Activa el sonido`\n"
        "\u2022 `Baja el volumen de Discord al 30`\n\n"
        "_Hardware_\n"
        "\u2022 `\u00bfQu\u00e9 procesador / gr\u00e1fica tengo?`\n"
        "\u2022 `\u00bfCu\u00e1nta RAM tengo?`\n"
        "\u2022 `\u00bfCu\u00e1l es la temperatura?`\n"
        "\u2022 `Informaci\u00f3n de mi PC`\n\n"
        "_Procesos_\n"
        "\u2022 `\u00bfQu\u00e9 procesos tengo abiertos?`\n"
        "\u2022 `\u00bfQu\u00e9 consume m\u00e1s memoria?`\n\n"
        "_Apps y energ\u00eda_\n"
        "\u2022 `Abre [app/web]` \u00b7 `Cierra [programa]`\n"
        "\u2022 `Cierra JARVIS` \u00b7 `Apaga el PC`\n\n"
        "_Captura y webcam_\n"
        "\u2022 `M\u00e1ndame una captura`\n"
        "\u2022 `Hazme una foto` (webcam)"
    )

    partes.append(
        "\ud83d\udcc1 *ARCHIVOS*\n\n"
        "_Explorar (cualquier disco)_\n"
        "\u2022 `Abre la carpeta [nombre]`\n"
        "\u2022 `Busca el archivo notas en el PC`\n\n"
        "_Leer / resumir_\n"
        "\u2022 `Muestra el archivo [nombre]`\n"
        "\u2022 `Resume el archivo [nombre]`\n"
        "\u2022 `Analiza el c\u00f3digo [archivo]`\n\n"
        "_Borrar (a papelera, con confirmaci\u00f3n)_\n"
        "\u2022 `Borra el archivo [nombre]` \u2192 `S\u00ed, confirma`\n\n"
        "\ud83c\udfa8 *IA / MULTIMEDIA*\n\n"
        "_Im\u00e1genes_\n"
        "\u2022 `Genera una imagen de un drag\u00f3n`\n"
        "\u2022 `\u00bfQu\u00e9 hay en mi pantalla?`\n\n"
        "_Conversaci\u00f3n / web_\n"
        "\u2022 Cualquier pregunta \u2192 responde la IA\n"
        "\u2022 `Busca en internet [tema]`\n"
        "\u2022 `\u00bfEst\u00e1s seguro?` \u2192 verifica\n\n"
        "_Memoria_\n"
        "\u2022 `Recuerda que [dato]`\n\n"
        "_F\u00fatbol_\n"
        "\u2022 `\u00bfC\u00f3mo qued\u00f3 el [equipo]?`\n"
        "\u2022 `Partidos de hoy`"
    )

    partes.append(
        "\ud83d\udd22 *C\u00c1LCULO / MATES*\n"
        "\u2022 `Cu\u00e1nto es 8 por 5` (y `m\u00e1s tres`)\n"
        "\u2022 `Soluciona 2x cuadrado m\u00e1s 4x menos 7`\n"
        "\u2022 `Deriva [funci\u00f3n]` \u00b7 `Integral de [funci\u00f3n]`\n"
        "\u2022 `Factoriza [expresi\u00f3n]`\n\n"
        "\ud83c\udfae *JUEGOS / MINECRAFT*\n"
        "\u2022 `\u00bfA qu\u00e9 juego estoy jugando?`\n"
        "\u2022 `Busca [cosa] en este juego`\n"
        "\u2022 `Haz backup del mundo`\n"
        "\u2022 `Abre / cierra el servidor`\n\n"
        "\ud83d\udee0 *HERRAMIENTAS*\n"
        "\u2022 `Pon una alarma a las [hora]`\n"
        "\u2022 `Temporizador de [X] minutos`\n"
        "\u2022 `Apunta [nota]` / `Lee mis notas`\n"
        "\u2022 `\u00bfQu\u00e9 hora es?` / `\u00bfQu\u00e9 tiempo hace?`\n"
        "\u2022 `Comparte mi PC` / `Deja de compartir`\n\n"
        "\ud83d\udcf1 *CONTROL REMOTO*\n"
        "Todo esto funciona por Telegram. Adem\u00e1s te env\u00edo aqu\u00ed: capturas, "
        "im\u00e1genes generadas y fotos de webcam.\n\n"
        "_Usa los botones de abajo para accesos r\u00e1pidos._ \u25be"
    )

    return partes

def _procesar_mensaje(mensaje):
    """Procesa un mensaje recibido."""
    chat_id = mensaje.get("chat", {}).get("id")
    texto = mensaje.get("text", "").strip()

    # Seguridad: solo responder al chat autorizado
    if chat_id != CHAT_ID_AUTORIZADO:
        _log(f"Mensaje rechazado de chat no autorizado: {chat_id}")
        return

    if not texto:
        return

    global _apagado_pendiente

    # ¿Es un botón de acceso rápido? Traducir a la orden real
    texto_lower = texto.lower().strip()
    if texto_lower in ATAJOS:
        texto = ATAJOS[texto_lower]
        texto_lower = texto.lower()

    # Apagar PC: pedir confirmación (evita apagones accidentales)
    if texto == "__APAGAR_PC__":
        _apagado_pendiente = True
        enviar_mensaje("⛔ *¿Seguro que quieres apagar el PC?*\n"
                       "Responde *sí apaga* para confirmar, o cualquier otra cosa para cancelar.")
        return

    # Confirmación de apagado pendiente
    if _apagado_pendiente:
        _apagado_pendiente = False
        if any(p in texto_lower for p in ['sí apaga', 'si apaga', 'sí, apaga', 'confirma', 'apaga ya']):
            enviar_mensaje("⛔ Apagando el PC en 10 segundos...")
            if _procesar_orden:
                _procesar_orden("apaga el pc")
            return
        else:
            enviar_mensaje("✓ Apagado cancelado.")
            return

    # Comandos especiales de bienvenida/ayuda
    if texto_lower in ('/start', '/help', 'ayuda'):
        partes = _mensaje_bienvenida()
        for i, parte in enumerate(partes):
            # Solo la última parte lleva el teclado
            enviar_mensaje(parte, con_teclado=(i == len(partes) - 1))
            time.sleep(0.3)  # pequeña pausa entre mensajes
        return

    _log(f"Orden recibida por Telegram: {texto}")

    # Mostrar "escribiendo..." mientras procesa
    _escribiendo(chat_id)

    # Ejecutar la orden en JARVIS
    if _procesar_orden:
        try:
            respuesta = _procesar_orden(texto)
            if respuesta:
                enviar_mensaje(respuesta)
            elif respuesta is None:
                # None = ya se envió troceado desde jarvis, no mandar nada más
                pass
            else:
                enviar_mensaje("✓ Hecho.")
        except Exception as e:
            enviar_mensaje(f"⚠️ Error al ejecutar: {e}")
            _log(f"Error procesando orden: {e}")
    else:
        enviar_mensaje("⚠️ JARVIS aún no está listo del todo.")


def _bucle_polling():
    """Bucle que escucha mensajes nuevos (long polling)."""
    global _ultimo_update, _running

    _log("Bot de Telegram escuchando...")

    # Limpiar mensajes viejos al arrancar
    try:
        r = requests.get(f"{API}/getUpdates", timeout=10).json()
        if r.get("result"):
            _ultimo_update = r["result"][-1]["update_id"] + 1
    except Exception:
        pass

    while _running:
        try:
            r = requests.get(f"{API}/getUpdates", params={
                "offset": _ultimo_update,
                "timeout": 30
            }, timeout=35).json()

            for update in r.get("result", []):
                _ultimo_update = update["update_id"] + 1
                if "message" in update:
                    _procesar_mensaje(update["message"])

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            _log(f"Error en polling: {e}")
            time.sleep(5)


def iniciar(procesar_orden_fn, log_fn=None):
    """
    Arranca el bot de Telegram en segundo plano.
    procesar_orden_fn: función que recibe texto y devuelve respuesta.
    """
    global _procesar_orden, _log_fn, _running

    _procesar_orden = procesar_orden_fn
    _log_fn = log_fn
    _running = True

    hilo = threading.Thread(target=_bucle_polling, daemon=True)
    hilo.start()

    # Avisar de que está en línea (con teclado y estilo)
    try:
        enviar_mensaje(
            "🟢 *JARVIS conectado*\n"
            "`Sistema en línea — listo para órdenes`",
            con_teclado=True
        )
    except Exception:
        pass

    return hilo


def detener():
    """Detiene el bot."""
    global _running
    _running = False


def verificar_token():
    """Comprueba que el token es válido."""
    try:
        r = requests.get(f"{API}/getMe", timeout=10).json()
        if r.get("ok"):
            nombre = r["result"]["username"]
            return f"Bot @{nombre} conectado correctamente."
        return "Token inválido."
    except Exception as e:
        return f"Error de conexión: {e}"
