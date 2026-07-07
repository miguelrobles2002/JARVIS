# -*- coding: utf-8 -*-
"""
configuracion.py — Sistema de configuración de JARVIS (versión pública)

La primera vez que se ejecuta JARVIS, este módulo detecta que no hay
configuración y lanza un menú que pregunta al usuario sus datos
(token de Telegram, nombre, ciudad, módulos a activar...) y los guarda
en 'config.json'. Las siguientes veces, JARVIS arranca leyendo ese archivo.

Uso desde jarvis.py:
    from configuracion import cargar_config
    CONFIG = cargar_config()
    TOKEN = CONFIG["telegram_token"]
    ...
"""

import os
import json

# El config se guarda junto al programa
_RUTA_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _detectar_escritorio():
    """Detecta la ruta del escritorio del usuario actual (funciona en cualquier PC)."""
    # Windows: intenta OneDrive y ruta clásica
    candidatos = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Escritorio"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Escritorio"),
    ]
    for ruta in candidatos:
        if os.path.isdir(ruta):
            return ruta
    # Si no encuentra, usa la carpeta del usuario
    return os.path.expanduser("~")


def _preguntar(texto, obligatorio=True, defecto=None):
    """Pide un dato al usuario por consola."""
    while True:
        if defecto:
            valor = input(f"{texto} [{defecto}]: ").strip()
            if not valor:
                return defecto
        else:
            valor = input(f"{texto}: ").strip()
        if valor or not obligatorio:
            return valor
        print("  ⚠️  Este dato es obligatorio, inténtalo de nuevo.")


def _preguntar_si_no(texto, defecto=True):
    """Pregunta sí/no al usuario."""
    d = "S/n" if defecto else "s/N"
    while True:
        valor = input(f"{texto} [{d}]: ").strip().lower()
        if not valor:
            return defecto
        if valor in ("s", "si", "sí", "y", "yes"):
            return True
        if valor in ("n", "no"):
            return False
        print("  ⚠️  Responde 's' (sí) o 'n' (no).")


def _menu_configuracion():
    """Muestra el menú de configuración inicial y devuelve el config completo."""
    print("\n" + "=" * 60)
    print("            CONFIGURACIÓN INICIAL DE JARVIS")
    print("=" * 60)
    print("\n¡Bienvenido! Vamos a configurar JARVIS con tus datos.")
    print("Esto solo hay que hacerlo una vez.\n")

    config = {}

    # --- DATOS BÁSICOS ---
    print("── DATOS BÁSICOS " + "─" * 44)
    config["nombre_usuario"] = _preguntar(
        "¿Cómo quieres que JARVIS te llame? (tu nombre)", defecto="Jefe")
    config["ciudad"] = _preguntar(
        "¿En qué ciudad estás? (para el tiempo)", defecto="Madrid")

    # --- TELEGRAM ---
    print("\n── TELEGRAM " + "─" * 49)
    print("Para controlar JARVIS desde el móvil necesitas un bot de Telegram.")
    print("Cómo conseguir el token:")
    print("  1. En Telegram, busca @BotFather")
    print("  2. Escríbele /newbot y sigue los pasos")
    print("  3. Te dará un TOKEN (algo como 123456:ABC-DEF...)")
    print("Cómo conseguir tu Chat ID:")
    print("  1. Busca @userinfobot en Telegram y escríbele /start")
    print("  2. Te dirá tu ID (un número)\n")

    config["usar_telegram"] = _preguntar_si_no("¿Quieres activar el control por Telegram?")
    if config["usar_telegram"]:
        config["telegram_token"] = _preguntar("  Pega tu TOKEN de Telegram")
        config["telegram_chat_id"] = _preguntar("  Pega tu CHAT ID (número)")
    else:
        config["telegram_token"] = ""
        config["telegram_chat_id"] = ""

    # --- MODELOS DE IA ---
    print("\n── INTELIGENCIA ARTIFICIAL (Ollama) " + "─" * 25)
    print("JARVIS usa Ollama para la IA. Modelos recomendados:")
    print("  · Conversación: qwen3:8b  (o llama3.1, mistral...)")
    print("  · Código:       qwen2.5-coder:7b")
    print("Asegúrate de haberlos descargado con 'ollama pull <modelo>'.\n")
    config["modelo_llm"] = _preguntar(
        "Modelo de conversación", defecto="qwen3:8b")
    config["modelo_codigo"] = _preguntar(
        "Modelo de código", defecto="qwen2.5-coder:7b")

    # --- MÓDULOS OPCIONALES ---
    print("\n── MÓDULOS OPCIONALES " + "─" * 39)
    print("Activa solo los que quieras usar (algunos necesitan configuración extra).\n")
    config["usar_voz"] = _preguntar_si_no("¿Activar control por voz (tecla F9)?")
    config["usar_imagenes"] = _preguntar_si_no(
        "¿Activar generación de imágenes con IA? (necesita GPU potente)", defecto=False)
    config["usar_correo"] = _preguntar_si_no(
        "¿Activar lectura de Gmail? (requiere configurar credenciales aparte)", defecto=False)
    config["usar_calendario"] = _preguntar_si_no(
        "¿Activar Google Calendar? (requiere credenciales aparte)", defecto=False)

    # --- FÚTBOL (opcional) ---
    print("\n── FÚTBOL (opcional) " + "─" * 40)
    print("Para consultar partidos y resultados necesitas una API key gratuita")
    print("de https://www.api-football.com (plan gratis: 100 consultas/día).")
    config["usar_futbol"] = _preguntar_si_no("¿Activar consultas de fútbol?", defecto=False)
    if config["usar_futbol"]:
        config["futbol_api_key"] = _preguntar("  Pega tu API key de API-Football")
        print("  (opcional) También puedes usar football-data.org para La Liga/Champions.")
        config["football_data_key"] = _preguntar(
            "  API key de football-data.org (Enter para saltar)", obligatorio=False, defecto="")
    else:
        config["futbol_api_key"] = ""
        config["football_data_key"] = ""

    # --- BACKUP (opcional) ---
    print("\n── COPIAS DE SEGURIDAD (opcional) " + "─" * 27)
    config["usar_backup"] = _preguntar_si_no(
        "¿Quieres que JARVIS haga copias de seguridad de tus carpetas?", defecto=False)
    if config["usar_backup"]:
        print("Escribe las carpetas que quieres respaldar, separadas por ';'")
        print("Ejemplo: C:\\Users\\tu_usuario\\Documentos ; D:\\Fotos")
        carpetas_txt = _preguntar("  Carpetas a respaldar")
        config["backup_carpetas"] = [x.strip() for x in carpetas_txt.split(";") if x.strip()]
        config["backup_destino"] = _preguntar(
            "  Carpeta donde guardar las copias (ej: D:\\backups)")
    else:
        config["backup_carpetas"] = []
        config["backup_destino"] = ""

    # --- MINECRAFT (opcional) ---
    print("\n── MINECRAFT (opcional) " + "─" * 37)
    config["usar_minecraft"] = _preguntar_si_no(
        "¿Tienes un servidor de Minecraft y quieres gestionarlo?", defecto=False)
    if config["usar_minecraft"]:
        print("Indica la carpeta de tu servidor (donde está la carpeta 'world').")
        config["minecraft_servidor"] = _preguntar(
            "  Carpeta del servidor (ej: F:\\MiServidor)")
        config["minecraft_backup"] = _preguntar(
            "  Carpeta donde guardar los backups (ej: F:\\backups)")
        run = _preguntar(
            "  Ruta del .bat para arrancar el servidor (opcional, Enter para saltar)",
            obligatorio=False, defecto="")
        config["minecraft_run_bat"] = run
    else:
        config["minecraft_servidor"] = ""
        config["minecraft_backup"] = ""
        config["minecraft_run_bat"] = ""

    # --- DETECTADO AUTOMÁTICAMENTE ---
    config["escritorio"] = _detectar_escritorio()

    # --- RESUMEN ---
    print("\n" + "=" * 60)
    print("  RESUMEN DE TU CONFIGURACIÓN")
    print("=" * 60)
    print(f"  Nombre:            {config['nombre_usuario']}")
    print(f"  Ciudad:            {config['ciudad']}")
    print(f"  Telegram:          {'Sí' if config['usar_telegram'] else 'No'}")
    print(f"  Modelo IA:         {config['modelo_llm']}")
    print(f"  Modelo código:     {config['modelo_codigo']}")
    print(f"  Voz (F9):          {'Sí' if config['usar_voz'] else 'No'}")
    print(f"  Imágenes IA:       {'Sí' if config['usar_imagenes'] else 'No'}")
    print(f"  Gmail:             {'Sí' if config['usar_correo'] else 'No'}")
    print(f"  Calendario:        {'Sí' if config['usar_calendario'] else 'No'}")
    print(f"  Fútbol:            {'Sí' if config.get('usar_futbol') else 'No'}")
    print(f"  Backups:           {'Sí' if config.get('usar_backup') else 'No'}")
    print(f"  Minecraft:         {'Sí' if config['usar_minecraft'] else 'No'}")
    print(f"  Escritorio:        {config['escritorio']}")
    print("=" * 60)

    if not _preguntar_si_no("\n¿Es correcto? (si dices 'no', vuelves a empezar)"):
        return _menu_configuracion()  # reinicia el menú

    return config


def cargar_config():
    """
    Devuelve la configuración de JARVIS.
    Si no existe config.json, lanza el menú de configuración inicial y lo crea.
    """
    if os.path.isfile(_RUTA_CONFIG):
        try:
            with open(_RUTA_CONFIG, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Por si falta algún campo nuevo, rellenamos con valores por defecto
            return _completar_defaults(config)
        except Exception as e:
            print(f"⚠️  Error leyendo config.json ({e}). Vamos a reconfigurar.")

    # No existe o está corrupto: configurar desde cero
    config = _menu_configuracion()
    guardar_config(config)
    print("\n✅ Configuración guardada en config.json")
    print("   JARVIS va a arrancar. La próxima vez usará estos datos directamente.\n")
    return config


def guardar_config(config):
    """Guarda la configuración en config.json."""
    with open(_RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def reconfigurar():
    """Fuerza volver a configurar (borra el config actual)."""
    config = _menu_configuracion()
    guardar_config(config)
    print("\n✅ Configuración actualizada.")
    return config


def _completar_defaults(config):
    """Rellena campos que puedan faltar con valores por defecto."""
    defaults = {
        "nombre_usuario": "Jefe",
        "ciudad": "Madrid",
        "usar_telegram": False,
        "telegram_token": "",
        "telegram_chat_id": "",
        "modelo_llm": "qwen3:8b",
        "modelo_codigo": "qwen2.5-coder:7b",
        "usar_voz": True,
        "usar_imagenes": False,
        "usar_correo": False,
        "usar_calendario": False,
        "usar_futbol": False,
        "futbol_api_key": "",
        "football_data_key": "",
        "usar_backup": False,
        "backup_carpetas": [],
        "backup_destino": "",
        "usar_minecraft": False,
        "minecraft_servidor": "",
        "minecraft_backup": "",
        "minecraft_run_bat": "",
        "escritorio": _detectar_escritorio(),
    }
    for clave, valor in defaults.items():
        if clave not in config:
            config[clave] = valor
    return config


# Permite reconfigurar ejecutando este archivo directamente:
#   python configuracion.py
if __name__ == "__main__":
    print("Reconfigurando JARVIS...")
    reconfigurar()
