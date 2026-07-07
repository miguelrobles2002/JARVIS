"""
Módulo de control de Parsec para JARVIS
Abre Parsec y pulsa el botón Share (clic por posición, ya que Parsec usa
su propio motor gráfico MTY_Window que pywinauto no puede leer)
"""
import os
import time
import subprocess

RUTA_PARSEC = r"C:\Program Files\Parsec\parsecd.exe"

# Posición relativa del botón "Share" dentro de la ventana de Parsec
SHARE_REL_X = 0.247
SHARE_REL_Y = 0.668
# Posición de la X roja (dejar de compartir) - aparece tras compartir
STOP_REL_X = 0.311
STOP_REL_Y = 0.667


def _pids_parsec():
    """Devuelve los PIDs de parsecd.exe."""
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq parsecd.exe', '/FO', 'CSV', '/NH'],
                          capture_output=True, text=True, creationflags=0x08000000)
        pids = []
        for linea in r.stdout.strip().split('\n'):
            if 'parsecd.exe' in linea.lower():
                partes = linea.split('","')
                if len(partes) >= 2:
                    try:
                        pids.append(int(partes[1].strip('"')))
                    except:
                        pass
        return pids
    except:
        return []


def _ventana_parsec():
    """Encuentra el hwnd de la ventana principal de Parsec (clase MTY_Window)."""
    import win32gui, win32process
    pids = _pids_parsec()
    if not pids:
        return None

    encontrada = [None]
    def cb(hwnd, _):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in pids:
                clase = win32gui.GetClassName(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                # Ventana principal: grande y de clase MTY_Window
                if 'MTY' in clase and w > 400 and h > 400:
                    encontrada[0] = hwnd
        except:
            pass
        return True
    win32gui.EnumWindows(cb, None)
    return encontrada[0]


def _abrir_parsec_interno():
    """Abre Parsec si no está corriendo. Devuelve True si arrancó o ya estaba."""
    if _pids_parsec():
        return True
    if not os.path.exists(RUTA_PARSEC):
        return False
    try:
        subprocess.Popen([RUTA_PARSEC])
        return True
    except:
        return False


def _mostrar_ventana(hwnd):
    """Trae la ventana de Parsec al frente."""
    import win32gui, win32con
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            return True
        except:
            return False


def _click_en_ventana(hwnd, rel_x, rel_y):
    """Hace clic en una posición relativa dentro de la ventana."""
    import win32gui
    rect = win32gui.GetWindowRect(hwnd)
    x = rect[0] + int((rect[2] - rect[0]) * rel_x)
    y = rect[1] + int((rect[3] - rect[1]) * rel_y)

    try:
        import pyautogui
        pyautogui.click(x, y)
        return True
    except ImportError:
        # Fallback con ctypes
        import ctypes
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # left down
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # left up
        return True


def abrir_parsec():
    """Solo abre Parsec."""
    if _pids_parsec():
        hwnd = _ventana_parsec()
        if hwnd:
            _mostrar_ventana(hwnd)
        return "Parsec ya está abierto."
    if not _abrir_parsec_interno():
        return "No encontré Parsec o no pude abrirlo."
    return "Abriendo Parsec."


def compartir_parsec(log_fn=None):
    """Abre Parsec (si hace falta) y pulsa Share por posición."""
    def _log(m):
        if log_fn:
            log_fn(m, "accion")

    recien = not bool(_pids_parsec())
    if not _abrir_parsec_interno():
        return "No encontré Parsec instalado."

    if recien:
        _log("Abriendo Parsec...")
        time.sleep(10)  # esperar a que cargue la interfaz

    hwnd = _ventana_parsec()
    if not hwnd:
        # Esperar un poco más por si tarda
        time.sleep(4)
        hwnd = _ventana_parsec()
    if not hwnd:
        return "Parsec abierto pero no encuentro su ventana. Pulsa Share manualmente."

    _mostrar_ventana(hwnd)
    time.sleep(1.5)

    # Refrescar hwnd y pulsar Share
    hwnd = _ventana_parsec()
    if hwnd:
        _click_en_ventana(hwnd, SHARE_REL_X, SHARE_REL_Y)
        return "Compartiendo el PC en Parsec."
    return "No pude pulsar Share. Hazlo manualmente."


def dejar_de_compartir(log_fn=None):
    """Deja de compartir. El botón Stop aparece en la misma posición que Share."""
    def _log(m):
        if log_fn:
            log_fn(m, "accion")

    if not _pids_parsec():
        return "Parsec no está abierto."

    hwnd = _ventana_parsec()
    if not hwnd:
        return "No encuentro la ventana de Parsec."

    _mostrar_ventana(hwnd)
    time.sleep(1.5)

    hwnd = _ventana_parsec()
    if hwnd:
        # Tras compartir, hay un campo con el enlace y una X roja a la derecha
        _click_en_ventana(hwnd, STOP_REL_X, STOP_REL_Y)
        return "He dejado de compartir el PC en Parsec."
    return "No pude pulsar Stop. Hazlo manualmente."


def detectar_parsec(texto):
    """Detecta órdenes de Parsec."""
    t = texto.lower().strip()

    menciona_parsec = any(p in t for p in ['parsec', 'parsi', 'parse', 'pársec', 'parsex'])

    # Frases de "compartir el PC" que SIEMPRE son Parsec aunque no lo nombren
    comparte_pc = any(p in t for p in ['comparte mi pc', 'comparte el pc', 'compartir mi pc',
                                       'compartir el pc', 'comparte mi ordenador',
                                       'comparte el ordenador', 'comparte mi equipo'])
    deja_compartir_pc = any(p in t for p in ['deja de compartir mi pc', 'deja de compartir el pc',
                                             'deja de compartir mi ordenador',
                                             'dejar de compartir mi pc'])

    if not menciona_parsec and not comparte_pc and not deja_compartir_pc:
        return None

    # Dejar de compartir
    if deja_compartir_pc or (menciona_parsec and any(p in t for p in [
            'deja de compartir', 'dejar de compartir', 'no compartas',
            'para de compartir', 'detén el', 'deten el', 'stop',
            'deja de hostear', 'cierra la sesión'])):
        return ('dejar',)

    # Compartir
    if comparte_pc or any(p in t for p in ['comparte', 'compartir', 'share',
                                           'hostea', 'host']):
        return ('compartir',)

    # Solo abrir (requiere mencionar parsec)
    if menciona_parsec and any(p in t for p in ['abre', 'abrir', 'lanza', 'inicia', 'arranca']):
        return ('abrir',)

    return None
