"""
Módulo de notificaciones - abre Phone Link, lee y minimiza
"""
import re, time


def _abrir_phone_link():
    """Abre Phone Link si no está abierto y devuelve la ventana."""
    import subprocess
    from pywinauto import Application

    # Intentar conectar si ya está abierto
    try:
        app = Application(backend='uia').connect(
            title_re='.*Enlace.*|.*Phone.*Link.*', timeout=2)
        return app.top_window(), False  # False = ya estaba abierto
    except:
        pass

    # Abrir Phone Link
    subprocess.Popen(['start', 'ms-phone:'], shell=True)
    time.sleep(4)

    try:
        app = Application(backend='uia').connect(
            title_re='.*Enlace.*|.*Phone.*Link.*', timeout=5)
        return app.top_window(), True  # True = lo abrimos nosotros
    except:
        return None, False


def leer_notificaciones():
    """Lee notificaciones del móvil desde Phone Link."""
    win, abrimos = _abrir_phone_link()
    if not win:
        return "No pude abrir Phone Link."

    try:
        # Asegurar que la ventana está visible para cargar datos
        try:
            win.restore()
            time.sleep(1)
        except:
            pass

        # Buscar grupo de notificaciones
        try:
            noti_group = win.child_window(auto_id="PaneContent", control_type="Group")

            # Sin notificaciones
            try:
                sin = noti_group.child_window(
                    title="No hay notificaciones nuevas", control_type="Text")
                if sin.exists():
                    return "No tienes notificaciones nuevas en el móvil."
            except:
                pass

            notificaciones = []

            # Buscar todos los textos en el grupo de notificaciones
            ignorar = {
                "Notificaciones", "Borrar las notificaciones",
                "No hay notificaciones nuevas", ""
            }

            # Intentar ListItems primero
            try:
                items = noti_group.descendants(control_type="ListItem")
                for item in items:
                    texto = item.window_text().strip()
                    if texto and len(texto) > 2 and texto not in ignorar:
                        notificaciones.append(texto)
            except:
                pass

            # Si no hay ListItems, buscar Text
            if not notificaciones:
                try:
                    texts = noti_group.descendants(control_type="Text")
                    for t in texts:
                        texto = t.window_text().strip()
                        if texto and texto not in ignorar and len(texto) > 3:
                            notificaciones.append(texto)
                except:
                    pass

            if not notificaciones:
                return "No tienes notificaciones nuevas en el móvil."

            # Quitar duplicados
            vistos = set()
            unicas = []
            for n in notificaciones:
                if n not in vistos:
                    vistos.add(n)
                    unicas.append(n)

            n = len(unicas)
            resultado = f"Tienes {n} notificación{'es' if n != 1 else ''} en el móvil. "
            resultado += ". ".join(unicas[:5])
            if n > 5:
                resultado += f". Y {n - 5} más."
            return resultado

        except Exception as e:
            return f"Error leyendo notificaciones: {e}"

    finally:
        # Si lo abrimos nosotros, minimizarlo
        if abrimos:
            try:
                win.minimize()
            except:
                pass


def detectar_notificaciones(texto):
    t = texto.lower().strip()
    patrones = [
        r'(?:dime|cuéntame|lee|leer|tengo|hay|qué|que|cuáles?)\s+(?:qué\s+)?(?:notificaciones?|avisos?|mensajes?\s+pendientes?)',
        r'notificaciones?\s+(?:del\s+móvil|nuevas?|pendientes?|que tengo)',
        r'(?:qué|que)\s+(?:me\s+)?(?:ha\s+)?(?:llegado|entrado)',
        r'(?:avisos?|alertas?)\s+(?:del\s+)?móvil',
        r'(?:hay|tengo)\s+(?:algo|mensajes?|notificaciones?)\s+nuevo',
    ]
    for p in patrones:
        if re.search(p, t):
            return True
    return False
