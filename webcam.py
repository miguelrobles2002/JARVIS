"""
Módulo de webcam para JARVIS
Hace una foto con la cámara y la guarda (para enviar por Telegram)
"""
import os
from datetime import datetime

SALIDA_DIR = os.path.join(os.environ.get('TEMP', 'C:\\Temp'))


def hacer_foto():
    """Captura una imagen de la webcam. Devuelve la ruta o un mensaje de error."""
    try:
        import cv2
    except ImportError:
        return None, "Necesito OpenCV. Instala: pip install opencv-python"

    # Abrir la cámara (índice 0 = cámara por defecto)
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW = más rápido en Windows

    if not cam.isOpened():
        cam.release()
        return None, "No detecto ninguna webcam conectada."

    # Descartar los primeros frames (la cámara necesita ajustar exposición/enfoque)
    for _ in range(5):
        cam.read()

    ok, frame = cam.read()
    cam.release()

    if not ok or frame is None:
        return None, "La webcam no devolvió imagen."

    # Guardar
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(SALIDA_DIR, f"jarvis_webcam_{ts}.jpg")
    try:
        cv2.imwrite(ruta, frame)
        return ruta, "Foto tomada."
    except Exception as e:
        return None, f"No pude guardar la foto: {e}"


def detectar_webcam(texto):
    """Detecta peticiones de foto con la webcam."""
    t = texto.lower().strip()

    PALABRAS = ['hazme una foto', 'haz una foto', 'sácame una foto', 'sacame una foto',
                'foto con la webcam', 'foto con la cámara', 'foto con la camara',
                'foto de la webcam', 'foto de la cámara', 'usa la webcam',
                'enciende la cámara', 'enciende la camara', 'mira por la cámara',
                'mira por la camara', 'qué ves por la cámara', 'que ves por la camara']

    if any(p in t for p in PALABRAS):
        return True
    return None
