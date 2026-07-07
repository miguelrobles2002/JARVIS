"""
Módulo de generación de imágenes para JARVIS
Usa Juggernaut XL (SDXL afinado). Recomendado: GPU con 12GB VRAM o más.
"""
import re, os
from datetime import datetime

# Carpeta donde guardar las imágenes generadas
SALIDA_DIR = os.path.expandvars(r"%USERPROFILE%\Pictures\JARVIS")

# ─── MODELO ──────────────────────────────────────────
# Juggernaut XL: SDXL afinado, máxima calidad (más lento, ~25s en una RTX 3060)
# Para volver al rápido, pon RAPIDO = True (usa SDXL-Turbo)
MODELO_SD = "RunDiffusion/Juggernaut-XL-v9"
RAPIDO = False   # False = calidad (30 pasos) | True = turbo (4 pasos)

# Prompt negativo: lo que NO queremos (mejora mucho la calidad)
NEGATIVE_PROMPT = ("blurry, low quality, distorted, deformed, ugly, bad anatomy, "
                   "extra limbs, watermark, signature, text, jpeg artifacts, "
                   "low resolution, worst quality, bad hands")

_pipe = None


def _cargar_pipeline():
    """Carga el modelo en memoria (solo la primera vez)."""
    global _pipe
    if _pipe is not None:
        return _pipe

    import torch
    from diffusers import StableDiffusionXLPipeline, AutoPipelineForText2Image

    if RAPIDO:
        _pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16,
            variant="fp16"
        )
    else:
        # Juggernaut XL usa pesos .fp16.safetensors -> variant="fp16"
        _pipe = StableDiffusionXLPipeline.from_pretrained(
            MODELO_SD,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True
        )

    _pipe = _pipe.to("cuda")
    # Ahorro de VRAM (importante en 12GB)
    try:
        _pipe.enable_vae_slicing()
        _pipe.enable_vae_tiling()
    except Exception:
        pass
    return _pipe


def generar_imagen(descripcion, log_fn=None):
    """Genera una imagen a partir de una descripción de texto."""
    def _log(msg):
        if log_fn:
            log_fn(msg, "accion")

    try:
        import torch
    except ImportError:
        return "PyTorch no está instalado. Necesario para generar imágenes."

    _log("Cargando modelo de imagen...")
    try:
        pipe = _cargar_pipeline()
    except Exception as e:
        return f"No pude cargar el modelo: {e}"

    if pipe is None:
        return "No pude cargar el modelo de imagen."

    _log(f"Generando: {descripcion[:40]}...")

    try:
        if RAPIDO:
            imagen = pipe(
                prompt=descripcion,
                num_inference_steps=4,
                guidance_scale=0.0,
                height=1024, width=1024
            ).images[0]
        else:
            # Juggernaut XL: 30 pasos, guidance 7, con negative prompt
            imagen = pipe(
                prompt=descripcion + ", high quality, detailed, masterpiece, 8k",
                negative_prompt=NEGATIVE_PROMPT,
                num_inference_steps=30,
                guidance_scale=7.0,
                height=1024, width=1024
            ).images[0]

        # Guardar
        os.makedirs(SALIDA_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.join(SALIDA_DIR, f"jarvis_{ts}.png")
        imagen.save(ruta)

        try:
            os.startfile(ruta)
        except Exception:
            pass

        return f"Imagen generada y guardada en {ruta}"

    except Exception as e:
        if 'out of memory' in str(e).lower() or 'cuda' in str(e).lower():
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            return ("Me quedé sin memoria de vídeo. Cierra juegos o programas pesados "
                    "y prueba otra vez.")
        return f"Error al generar la imagen: {e}"


def detectar_generacion(texto):
    """Detecta peticiones de generación de imágenes."""
    t = texto.lower().strip()

    PATRONES = [
        r'(?:genera|crea|haz|dibuja|gener[aá]me|cr[eé]ame|hazme|dib[uú]jame)\s+(?:una\s+)?(?:imagen|foto|ilustración|dibujo|imagen de|foto de)\s+(?:de\s+|con\s+|sobre\s+)?(.+)',
        r'(?:imagina|visualiza)\s+(?:una\s+)?(?:imagen|escena)\s+(?:de\s+|con\s+)?(.+)',
    ]

    for patron in PATRONES:
        m = re.search(patron, t)
        if m:
            descripcion = m.group(1).strip().rstrip('.,;:')
            if descripcion and len(descripcion) > 2:
                return descripcion

    return None
