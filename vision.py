"""
Módulo de análisis de imágenes para JARVIS usando LLaVA (Ollama)
"""
import re, os, base64, glob, subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_VISION = "llava:latest"

# Carpeta de capturas de Windows
CAPTURAS_DIR = os.path.expandvars(r"%USERPROFILE%\Pictures\Screenshots")
ESCRITORIO = os.path.expandvars(r"%USERPROFILE%\Desktop")


def _imagen_a_base64(ruta):
    """Convierte una imagen a base64."""
    with open(ruta, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def _analizar_imagen(ruta_imagen, pregunta="¿Qué hay en esta imagen?"):
    """Envía la imagen a LLaVA y devuelve la descripción."""
    if not os.path.exists(ruta_imagen):
        return f"No encontré la imagen en {ruta_imagen}"

    try:
        img_b64 = _imagen_a_base64(ruta_imagen)
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_VISION,
            "prompt": f"Look at this image and answer in SPANISH, briefly and clearly. Question: {pregunta}",
            "images": [img_b64],
            "stream": False
        }, timeout=120)
        respuesta = r.json().get("response", "").strip()
        return respuesta if respuesta else "No pude analizar la imagen."
    except Exception as e:
        return f"Error al analizar la imagen: {e}"


def capturar_pantalla():
    """Hace una captura de pantalla y la guarda temporalmente."""
    ruta = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'jarvis_captura.png')
    try:
        # Usar PIL para captura
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(ruta)
        return ruta
    except ImportError:
        # Fallback con PowerShell
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$b = [System.Windows.Forms.SystemInformation]::VirtualScreen; "
            "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
            f"$bmp.Save('{ruta}'); $g.Dispose(); $bmp.Dispose()"
        )
        subprocess.run(['powershell', '-c', ps], creationflags=0x08000000)
        return ruta if os.path.exists(ruta) else None


def imagen_del_portapapeles():
    """Obtiene la imagen del portapapeles."""
    ruta = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'jarvis_clipboard.png')
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is None:
            return None
        img.save(ruta)
        return ruta
    except:
        return None


def ultima_captura():
    """Encuentra la captura de pantalla más reciente."""
    carpetas = [CAPTURAS_DIR, ESCRITORIO,
                os.path.expandvars(r"%USERPROFILE%\Pictures")]
    imagenes = []
    for carpeta in carpetas:
        if os.path.isdir(carpeta):
            for ext in ('*.png', '*.jpg', '*.jpeg'):
                imagenes.extend(glob.glob(os.path.join(carpeta, ext)))
    if not imagenes:
        return None
    # La más reciente por fecha de modificación
    return max(imagenes, key=os.path.getmtime)


def analizar(modo, pregunta="¿Qué hay en esta imagen?"):
    """
    modo: 'pantalla', 'portapapeles', 'ultima'
    """
    if modo == 'pantalla':
        ruta = capturar_pantalla()
        if not ruta:
            return "No pude capturar la pantalla."
    elif modo == 'portapapeles':
        ruta = imagen_del_portapapeles()
        if not ruta:
            return "No hay ninguna imagen en el portapapeles."
    elif modo == 'ultima':
        ruta = ultima_captura()
        if not ruta:
            return "No encontré ninguna captura reciente."
    else:
        return "Modo de análisis no reconocido."

    return _analizar_imagen(ruta, pregunta)


def detectar_vision(texto):
    """
    Detecta peticiones de análisis de imagen.
    Devuelve (modo, pregunta) o None.
    """
    t = texto.lower().strip()

    PALABRAS_VISION = ['analiza', 'analizar', 'qué ves', 'que ves', 'qué hay en',
                       'que hay en', 'describe', 'mira', 'qué es esto', 'que es esto',
                       'lee la imagen', 'lee esta imagen']

    es_vision = any(p in t for p in PALABRAS_VISION)
    menciona_imagen = any(p in t for p in ['imagen', 'foto', 'pantalla', 'captura',
                                            'screenshot', 'portapapeles', 'esto'])

    if not (es_vision and menciona_imagen):
        return None

    # Determinar modo
    if any(p in t for p in ['pantalla', 'screen', 'mi pantalla', 'lo que veo']):
        modo = 'pantalla'
    elif any(p in t for p in ['portapapeles', 'copiado', 'clipboard', 'lo que copié']):
        modo = 'portapapeles'
    elif any(p in t for p in ['última', 'ultima', 'reciente', 'captura']):
        modo = 'ultima'
    else:
        # Por defecto, captura de pantalla
        modo = 'pantalla'

    # Extraer pregunta específica si la hay
    pregunta = "¿Qué hay en esta imagen?"
    m = re.search(r'(?:qué|que|cuántos?|cuantos?|dónde|donde|cómo|como|hay)\s+(.+)', t)
    if m:
        posible = m.group(1).strip()
        if len(posible) > 5 and 'imagen' not in posible[:10]:
            pregunta = texto.strip()

    return (modo, pregunta)
