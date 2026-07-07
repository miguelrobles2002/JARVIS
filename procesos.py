"""
Módulo para ver los procesos/apps abiertos en JARVIS
"""
import subprocess

# Procesos del sistema que NO son "apps" del usuario (para filtrarlos)
PROCESOS_SISTEMA = {
    'svchost.exe', 'system', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe',
    'services.exe', 'lsass.exe', 'winlogon.exe', 'fontdrvhost.exe', 'dwm.exe',
    'sihost.exe', 'taskhostw.exe', 'ctfmon.exe', 'explorer.exe', 'runtimebroker.exe',
    'searchhost.exe', 'startmenuexperiencehost.exe', 'shellexperiencehost.exe',
    'textinputhost.exe', 'searchindexer.exe', 'audiodg.exe', 'conhost.exe',
    'wmiprvse.exe', 'spoolsv.exe', 'dllhost.exe', 'wudfhost.exe', 'memcompression',
    'securityhealthservice.exe', 'securityhealthsystray.exe', 'nvcontainer.exe',
    'nvdisplay.container.exe', 'applicationframehost.exe', 'systemsettings.exe',
    'backgroundtaskhost.exe', 'smartscreen.exe', 'useroobebroker.exe', 'lockapp.exe',
    'crashpad_handler.exe', 'widgets.exe', 'widgetservice.exe', 'phonelink.exe',
}

# Nombres bonitos para mostrar
NOMBRES_BONITOS = {
    'brave.exe': 'Brave', 'chrome.exe': 'Chrome', 'firefox.exe': 'Firefox',
    'msedge.exe': 'Edge', 'discord.exe': 'Discord', 'spotify.exe': 'Spotify',
    'javaw.exe': 'Minecraft', 'java.exe': 'Servidor Minecraft',
    'steam.exe': 'Steam', 'parsecd.exe': 'Parsec', 'code.exe': 'VS Code',
    'valorant.exe': 'Valorant', 'gta5.exe': 'GTA V', 'rdr2.exe': 'Red Dead 2',
    'rocketleague.exe': 'Rocket League', 'fc26.exe': 'EA FC 26',
    'hogwartslegacy.exe': 'Hogwarts Legacy', 'notepad.exe': 'Bloc de notas',
    'pythonw.exe': 'JARVIS', 'python.exe': 'Python', 'ollama.exe': 'Ollama',
    'obs64.exe': 'OBS', 'vlc.exe': 'VLC', 'whatsapp.exe': 'WhatsApp',
    'telegram.exe': 'Telegram', 'epicgameslauncher.exe': 'Epic Games',
    'cmd.exe': 'Terminal', 'powershell.exe': 'PowerShell',
    'msiafterburner.exe': 'MSI Afterburner',
}


def _listar_procesos():
    """Devuelve lista de (nombre, memoria_mb) de procesos del usuario."""
    try:
        import psutil
        procesos = {}
        for p in psutil.process_iter(['name', 'memory_info']):
            try:
                nombre = p.info['name']
                if not nombre:
                    continue
                nl = nombre.lower()
                if nl in PROCESOS_SISTEMA:
                    continue
                mem = p.info['memory_info'].rss / (1024*1024) if p.info['memory_info'] else 0
                # Agrupar por nombre (sumar memoria de procesos repetidos)
                if nl in procesos:
                    procesos[nl] += mem
                else:
                    procesos[nl] = mem
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return procesos
    except ImportError:
        return _listar_procesos_tasklist()


def _listar_procesos_tasklist():
    """Fallback sin psutil, usando tasklist."""
    try:
        r = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'],
                          capture_output=True, text=True, creationflags=0x08000000)
        procesos = {}
        for linea in r.stdout.strip().split('\n'):
            partes = linea.split('","')
            if len(partes) >= 5:
                nombre = partes[0].strip('"').lower()
                if nombre in PROCESOS_SISTEMA:
                    continue
                mem_str = partes[4].strip('"').replace('.', '').replace(' K', '').replace('.', '')
                try:
                    mem = int(mem_str.replace('.', '')) / 1024  # KB a MB
                except:
                    mem = 0
                if nombre in procesos:
                    procesos[nombre] += mem
                else:
                    procesos[nombre] = mem
        return procesos
    except:
        return {}


def _ventanas_visibles():
    """Devuelve los procesos que tienen ventana visible (apps en primer plano)."""
    try:
        import win32gui, win32process
        nombres = set()

        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).strip():
                try:
                    import psutil
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    p = psutil.Process(pid)
                    nombres.add(p.name().lower())
                except:
                    pass
            return True

        win32gui.EnumWindows(cb, None)
        return nombres
    except:
        return set()


def procesos_abiertos(modo='apps'):
    """
    modo='apps' -> apps principales (con ventana)
    modo='memoria' -> los que más memoria consumen
    """
    procesos = _listar_procesos()
    if not procesos:
        return "No pude obtener la lista de procesos."

    if modo == 'memoria':
        # Top por memoria
        top = sorted(procesos.items(), key=lambda x: x[1], reverse=True)[:6]
        lineas = []
        for nombre, mem in top:
            bonito = NOMBRES_BONITOS.get(nombre, nombre.replace('.exe', ''))
            lineas.append(f"{bonito}: {int(mem)} megas")
        return "Lo que más memoria consume: " + ", ".join(lineas) + "."

    # modo apps: solo los que tienen ventana visible
    visibles = _ventanas_visibles()
    if visibles:
        apps = []
        for nombre in visibles:
            if nombre in PROCESOS_SISTEMA:
                continue
            bonito = NOMBRES_BONITOS.get(nombre, nombre.replace('.exe', ''))
            if bonito not in apps:
                apps.append(bonito)
        if apps:
            return "Tienes abierto: " + ", ".join(sorted(apps)) + "."

    # Fallback: apps conocidas que estén corriendo
    conocidas = []
    for nombre in procesos:
        if nombre in NOMBRES_BONITOS:
            b = NOMBRES_BONITOS[nombre]
            if b not in conocidas:
                conocidas.append(b)
    if conocidas:
        return "Tienes abierto: " + ", ".join(sorted(conocidas)) + "."
    return "No detecto apps abiertas aparte del sistema."


def detectar_procesos(texto):
    """Detecta peticiones de ver procesos abiertos."""
    t = texto.lower().strip()

    es_pregunta = any(p in t for p in ['qué', 'que', 'cuáles', 'cuales', 'ver', 'dime',
                                       'muéstrame', 'muestrame', 'enséñame'])
    menciona = any(p in t for p in ['procesos', 'aplicaciones abiertas', 'apps abiertas',
                                    'programas abiertos', 'qué tengo abierto',
                                    'que tengo abierto', 'qué hay abierto', 'que hay abierto',
                                    'aplicaciones que tengo', 'programas que tengo'])

    if not menciona:
        return None

    if any(p in t for p in ['memoria', 'consume', 'consumen', 'ram', 'más memoria',
                            'mas memoria', 'gastan', 'gasta']):
        return ('memoria',)
    return ('apps',)
