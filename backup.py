r"""
Módulo de backup para JARVIS
Hace copias de seguridad de cualquier carpeta que el usuario configure.
Las carpetas a respaldar y el destino se leen de config.json.

El usuario configura en el menú:
  - backup_carpetas: lista de carpetas a respaldar (o una sola)
  - backup_destino:  carpeta donde guardar las copias
"""
import re, os, shutil, subprocess, threading
from datetime import datetime
from configuracion import cargar_config

_CONFIG = cargar_config()

# Carpeta(s) a respaldar y destino (desde la configuración del usuario)
BACKUP_CARPETAS = _CONFIG.get("backup_carpetas", [])   # lista de rutas
BACKUP_DESTINO  = _CONFIG.get("backup_destino", "")     # carpeta destino

# Compatibilidad con configuración antigua de Minecraft (opcional)
_mc_serv = _CONFIG.get("minecraft_servidor", "")
if _mc_serv and not BACKUP_CARPETAS:
    BACKUP_CARPETAS = [os.path.join(_mc_serv, "world")]
    BACKUP_DESTINO = _CONFIG.get("minecraft_backup", "") or BACKUP_DESTINO

# Servidor Minecraft (opcional, solo si está configurado)
SERVIDOR_DIR = _mc_serv
RUN_BAT      = _CONFIG.get("minecraft_run_bat", "")


def _servidor_activo():
    """Comprueba si hay un servidor Minecraft (java.exe) corriendo."""
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq java.exe'],
        capture_output=True, text=True, creationflags=0x08000000
    )
    return 'java.exe' in result.stdout


def _nombre_backup(origen):
    """Genera un nombre de backup a partir del nombre de la carpeta origen."""
    base = os.path.basename(os.path.normpath(origen)) or "backup"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{ts}"


def hacer_backup(carpeta=None, log_fn=None):
    """
    Hace backup de una carpeta (o de todas las configuradas si no se indica una).
    Guarda una copia con fecha y hora en la carpeta de destino.
    """
    def _log(msg):
        if log_fn:
            log_fn(msg, "accion")

    if not BACKUP_DESTINO:
        return ("No has configurado una carpeta de destino para los backups. "
                "Reconfigura JARVIS para añadirla.")

    # Decidir qué carpetas respaldar
    if carpeta:
        carpetas = [carpeta]
    elif BACKUP_CARPETAS:
        carpetas = BACKUP_CARPETAS
    else:
        return ("No has configurado ninguna carpeta para respaldar. "
                "Reconfigura JARVIS para añadirla.")

    resultados = []
    for origen in carpetas:
        if not os.path.exists(origen):
            resultados.append(f"No encontré la carpeta {origen}")
            continue

        destino = os.path.join(BACKUP_DESTINO, _nombre_backup(origen))
        _log(f"Copiando {origen} → {destino}...")

        # Aviso si es una carpeta de servidor Minecraft activo
        if SERVIDOR_DIR and origen.startswith(SERVIDOR_DIR) and _servidor_activo():
            _log("Servidor Minecraft activo — el backup puede tardar más.")

        try:
            os.makedirs(BACKUP_DESTINO, exist_ok=True)
            shutil.copytree(origen, destino)

            size_mb = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, filenames in os.walk(destino)
                for f in filenames
            ) / (1024 * 1024)

            # Limpiar backups viejos de esta misma carpeta (conservar 5)
            base = os.path.basename(os.path.normpath(origen))
            backups = sorted([
                d for d in os.listdir(BACKUP_DESTINO)
                if d.startswith(base + "_") and os.path.isdir(os.path.join(BACKUP_DESTINO, d))
            ])
            while len(backups) > 5:
                viejo = backups.pop(0)
                shutil.rmtree(os.path.join(BACKUP_DESTINO, viejo), ignore_errors=True)
                _log(f"Backup antiguo eliminado: {viejo}")

            resultados.append(f"{base}: {size_mb:.1f} MB guardados.")
        except Exception as e:
            resultados.append(f"Error copiando {origen}: {e}")

    return "Backup completado. " + " ".join(resultados)


def listar_backups():
    """Lista los backups disponibles en la carpeta de destino."""
    if not BACKUP_DESTINO or not os.path.exists(BACKUP_DESTINO):
        return "No hay backups todavía."

    backups = sorted([
        d for d in os.listdir(BACKUP_DESTINO)
        if os.path.isdir(os.path.join(BACKUP_DESTINO, d))
    ], reverse=True)

    if not backups:
        return "No hay backups guardados."

    resultado = f"Tienes {len(backups)} backup{'s' if len(backups) != 1 else ''}. "
    for b in backups[:5]:
        # nombre_20260614_042100 → intenta formatear la fecha
        m = re.search(r'_(\d{8}_\d{6})$', b)
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
                nombre = b[:m.start()]
                resultado += f"{nombre} del {dt.strftime('%d/%m/%Y a las %H:%M')}. "
                continue
            except Exception:
                pass
        resultado += f"{b}. "
    return resultado.strip()


# ─── Servidor Minecraft (opcional) ───────────────────────

def abrir_servidor():
    """Abre el servidor de Minecraft ejecutando su .bat (si está configurado)."""
    if not RUN_BAT:
        return "No has configurado un servidor de Minecraft."
    if not os.path.exists(RUN_BAT):
        return f"No encontré el servidor en {RUN_BAT}"
    if _servidor_activo():
        return "El servidor de Minecraft ya está abierto."
    try:
        subprocess.Popen(
            f'start "Minecraft Server" cmd /k "{RUN_BAT}"',
            shell=True, cwd=SERVIDOR_DIR or os.path.dirname(RUN_BAT)
        )
        return "Abriendo el servidor de Minecraft. Tardará un momento en arrancar."
    except Exception as e:
        return f"Error al abrir el servidor: {e}"


def cerrar_servidor():
    """Cierra el servidor de Minecraft."""
    if not _servidor_activo():
        return "El servidor de Minecraft no está abierto."
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'java.exe'],
                       capture_output=True, creationflags=0x08000000)
        return "Servidor de Minecraft cerrado."
    except Exception as e:
        return f"Error al cerrar el servidor: {e}"


def detectar_backup(texto):
    """
    Detecta acciones de backup y de servidor Minecraft.
    Devuelve: 'hacer', 'listar', 'abrir_servidor', 'cerrar_servidor' o None.
    """
    t = texto.lower().strip()

    ES_PREGUNTA = any(t.startswith(p) for p in [
        'cuál', 'cual', 'qué', 'que', 'cómo', 'como', 'cuándo', 'cuando',
        'dónde', 'donde', 'por qué', 'porque', 'quién', 'quien', 'cuánto', 'cuanto'
    ]) or '?' in texto or '¿' in texto

    # Backup (funciona aunque sea pregunta indirecta)
    if any(p in t for p in ['backup', 'copia de seguridad', 'copia seguridad', 'respaldo', 'respalda']):
        if any(p in t for p in ['lista', 'listar', 'cuántos', 'cuantos', 'ver los', 'qué backups', 'que backups']):
            return 'listar'
        return 'hacer'

    # Órdenes de servidor Minecraft (solo si NO es pregunta)
    if ES_PREGUNTA:
        return None

    menciona_servidor = 'servidor' in t or 'mundo' in t or 'minecraft' in t
    VERBOS_ABRIR = ['abre', 'abrir', 'arranca', 'arrancar', 'inicia', 'iniciar',
                    'enciende', 'levanta', 'lanza', 'pon en marcha']
    VERBOS_CERRAR = ['cierra', 'cerrar', 'apaga', 'apagar', 'detén', 'deten',
                     'detener', 'tumba', 'para el servidor']
    hay_verbo = any(re.search(r'\b' + re.escape(v) + r'\b', t) for v in VERBOS_ABRIR + VERBOS_CERRAR)

    if not (menciona_servidor and hay_verbo):
        return None

    if any(re.search(r'\b' + p + r'\b', t) for p in VERBOS_ABRIR):
        return 'abrir_servidor'
    if any(re.search(r'\b' + p + r'\b', t) for p in VERBOS_CERRAR):
        return 'cerrar_servidor'

    return None
