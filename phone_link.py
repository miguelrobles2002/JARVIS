"""
Módulo Phone Link para JARVIS
Hace llamadas a través de Enlace Móvil (Phone Link) de Windows
"""
import time
import re

# Contactos conocidos — añade los tuyos aquí
# Ejemplo:
#   "mama": "+34600000000",
#   "juan": "+34611111111",
CONTACTOS = {
}

def _get_phone_link(auto_abrir=True):
    """Conecta a Phone Link, abriéndolo si es necesario."""
    from pywinauto import Application
    # Intentar conectar si ya está abierto
    try:
        app = Application(backend='uia').connect(
            title_re='.*Enlace.*|.*Phone.*Link.*', timeout=2)
        win = app.top_window()
        # Asegurar que está visible (no minimizado)
        try:
            win.restore()
            time.sleep(0.5)
        except:
            pass
        return win
    except:
        pass

    if not auto_abrir:
        return None

    # Abrir Phone Link
    try:
        import subprocess
        subprocess.Popen(['start', 'ms-phone:'], shell=True)
        time.sleep(4)
        app = Application(backend='uia').connect(
            title_re='.*Enlace.*|.*Phone.*Link.*', timeout=5)
        return app.top_window()
    except:
        return None

def _ir_a_llamadas(win):
    """Navega al tab de Llamadas."""
    try:
        tab = win.child_window(auto_id="CallingNodeAutomationId", control_type="TabItem")
        tab.click_input()
        time.sleep(1)
        return True
    except:
        return False

def _marcar_numero(win, numero):
    """Marca un número usando los botones del teclado de Phone Link."""
    # Mapa de botones numéricos por auto_id
    btn_map = {
        '0': 'Button0', '1': 'Button1', '2': 'Button2', '3': 'Button3',
        '4': 'Button4', '5': 'Button5', '6': 'Button6', '7': 'Button7',
        '8': 'Button8', '9': 'Button9', '*': 'ButtonStar', '#': 'ButtonPound'
    }
    # Solo dígitos (sin + ni espacios)
    digitos = [c for c in numero if c in btn_map]
    for d in digitos:
        try:
            btn = win.child_window(auto_id=btn_map[d], control_type="Button")
            btn.click_input()
            time.sleep(0.05)
        except:
            pass
    time.sleep(0.5)


def llamar_contacto(nombre):
    """Hace una llamada al contacto dado."""
    nombre_lower = nombre.lower().strip()
    numero = CONTACTOS.get(nombre_lower)

    win = _get_phone_link(auto_abrir=True)
    if not win:
        return "No pude abrir Phone Link."

    # CRÍTICO: traer al frente con win32gui (más fiable que set_focus)
    try:
        import ctypes
        hwnd = win.handle
        # Restaurar si minimizada
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.5)
        # Forzar primer plano
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
        time.sleep(1.5)
    except:
        try:
            win.restore()
            win.set_focus()
            time.sleep(1.5)
        except:
            pass

    if not _ir_a_llamadas(win):
        return "No pude navegar a llamadas."

    time.sleep(1)  # esperar a que el tab cargue

    try:
        if numero:
            # Limpiar campo
            search_box = win.child_window(auto_id="TextBox", control_type="Edit")
            search_box.set_focus()
            search_box.click_input()
            time.sleep(0.3)
            search_box.type_keys('^a{DELETE}')
            time.sleep(0.3)

            # Marcar dígitos usando botones del teclado en pantalla
            _marcar_numero(win, numero)
            time.sleep(1.2)

            # Pulsar llamar
            call_btn = win.child_window(auto_id="ButtonCall", control_type="Button")
            call_btn.set_focus()
            call_btn.click_input()
            time.sleep(0.5)

            # Minimizar Phone Link después de llamar
            try:
                win.minimize()
            except:
                pass

            return f"Llamando a {nombre}."
        else:
            # Buscar por nombre en historial
            lista = win.child_window(auto_id="CallHistory", control_type="List")
            for item in lista.items():
                if nombre_lower in item.window_text().lower():
                    item.double_click_input()
                    time.sleep(1)
                    call_btn = win.child_window(auto_id="ButtonCall", control_type="Button")
                    call_btn.click_input()
                    try:
                        win.minimize()
                    except:
                        pass
                    return f"Llamando a {nombre}."

            return f"No encontré a {nombre} en los contactos."

    except Exception as e:
        return f"Error al llamar: {e}"


def colgar_llamada():
    """Cuelga la llamada en curso."""
    try:
        win = _get_phone_link()
        if not win:
            return "Phone Link no está abierto."
        # Buscar botón de colgar (aparece durante llamada activa)
        try:
            end_btn = win.child_window(title_re=".*[Cc]olgar.*|.*[Ee]nd.*|.*[Hh]ang.*", control_type="Button")
            end_btn.click_input()
            return "Llamada colgada."
        except:
            # Intentar con tecla de teléfono
            import pywinauto.keyboard as kb
            kb.send_keys('{VK_MEDIA_STOP}')
            return "Llamada finalizada."
    except Exception as e:
        return f"Error al colgar: {e}"


def detectar_llamada(texto):
    """
    Detecta si el texto es una petición de llamada.
    Devuelve ('llamar', nombre) o ('colgar',) o None.
    """
    t = texto.lower().strip()

    # Colgar
    if any(p in t for p in ["cuelga", "colgar", "corta la llamada", "finaliza la llamada", "termina la llamada"]):
        return ("colgar",)

    # Llamar
    m = re.search(r'(?:llama(?:r)?(?:\s+a)?|llama(?:r)?\s+al?|marca(?:r)?)\s+(?:a\s+)?(.+?)(?:\s*$)', t)
    if m:
        nombre = m.group(1).strip().rstrip('.,;:¿?¡!')
        return ("llamar", nombre)

    return None
