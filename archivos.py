"""
Módulo de análisis de archivos para JARVIS
Lee documentos (txt, pdf, docx, código) y los analiza con Ollama
"""
import re, os, glob, subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
# Modelos desde la configuración del usuario
from configuracion import cargar_config
_CONFIG = cargar_config()
MODELO_TEXTO = _CONFIG.get("modelo_llm", "qwen3:8b")
MODELO_CODIGO = _CONFIG.get("modelo_codigo", "qwen2.5-coder:7b")

ESCRITORIO = os.path.expandvars(r"%USERPROFILE%\Desktop")
DESCARGAS  = os.path.expandvars(r"%USERPROFILE%\Downloads")
DOCUMENTOS = os.path.expandvars(r"%USERPROFILE%\Documents")
# Carpetas OneDrive por si el escritorio está sincronizado
ONEDRIVE_DESK = os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop")
ONEDRIVE_DOC  = os.path.expandvars(r"%USERPROFILE%\OneDrive\Documentos")

CARPETAS_BUSQUEDA = [ESCRITORIO, DESCARGAS, DOCUMENTOS, ONEDRIVE_DESK, ONEDRIVE_DOC]

EXT_CODIGO = ('.py', '.php', '.js', '.html', '.css', '.java', '.cpp', '.c',
              '.cs', '.go', '.rb', '.rs', '.ts', '.sql', '.sh', '.ps1')
EXT_TEXTO  = ('.txt', '.md', '.log', '.csv', '.json', '.xml', '.ini', '.cfg')


def _leer_archivo(ruta):
    """Lee el contenido de un archivo según su tipo."""
    ext = os.path.splitext(ruta)[1].lower()

    if ext == '.pdf':
        return _leer_pdf(ruta)
    elif ext == '.docx':
        return _leer_docx(ruta)
    else:
        # Texto plano / código
        try:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"__ERROR__ No pude leer el archivo: {e}"


def _leer_pdf(ruta):
    try:
        from pypdf import PdfReader
        reader = PdfReader(ruta)
        texto = ""
        for pagina in reader.pages:
            texto += pagina.extract_text() + "\n"
        return texto
    except ImportError:
        return "__ERROR__ Instala pypdf: pip install pypdf"
    except Exception as e:
        return f"__ERROR__ No pude leer el PDF: {e}"


def _leer_docx(ruta):
    try:
        from docx import Document
        doc = Document(ruta)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        return "__ERROR__ Instala python-docx: pip install python-docx"
    except Exception as e:
        return f"__ERROR__ No pude leer el Word: {e}"


def _buscar_archivo(nombre):
    """Busca un archivo por nombre en varias carpetas."""
    nombre = nombre.lower().strip()
    # Quitar extensión del término de búsqueda (caracolas.docs -> caracolas)
    nombre_sin_ext = os.path.splitext(nombre)[0]
    candidatos = []
    for carpeta in CARPETAS_BUSQUEDA:
        if not os.path.isdir(carpeta):
            continue
        for f in os.listdir(carpeta):
            f_lower = f.lower()
            # Ignorar archivos temporales (~$)
            if f_lower.startswith('~$'):
                continue
            if nombre in f_lower or nombre_sin_ext in f_lower:
                candidatos.append(os.path.join(carpeta, f))
    if candidatos:
        # Preferir el que mejor coincide (nombre completo sin extensión)
        for c in candidatos:
            base = os.path.splitext(os.path.basename(c))[0].lower()
            if base == nombre_sin_ext:
                return c
        return candidatos[0]
    return None


def _archivo_mas_reciente(extensiones):
    """Encuentra el archivo más reciente de cierto tipo."""
    archivos = []
    for carpeta in CARPETAS_BUSQUEDA:
        if os.path.isdir(carpeta):
            for ext in extensiones:
                for f in glob.glob(os.path.join(carpeta, f'*{ext}')):
                    if not os.path.basename(f).startswith('~$'):
                        archivos.append(f)
    if not archivos:
        return None
    return max(archivos, key=os.path.getmtime)


def _preguntar(prompt, modelo):
    """Envía un prompt a Ollama."""
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": modelo,
            "prompt": prompt,
            "stream": False
        }, timeout=180)
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"Error al analizar: {e}"


def analizar_archivo(ruta, accion='resumir', pregunta=""):
    """Analiza un archivo: resumir, errores, explicar."""
    if not os.path.exists(ruta):
        return f"No encontré el archivo {ruta}"

    contenido = _leer_archivo(ruta)
    if contenido.startswith("__ERROR__"):
        return contenido.replace("__ERROR__ ", "")

    if not contenido.strip():
        return "El archivo está vacío o no tiene texto legible."

    # Limitar tamaño (Ollama tiene límite de contexto)
    if len(contenido) > 8000:
        contenido = contenido[:8000] + "\n...(texto truncado)"

    ext = os.path.splitext(ruta)[1].lower()
    es_codigo = ext in EXT_CODIGO
    nombre = os.path.basename(ruta)

    if es_codigo:
        modelo = MODELO_CODIGO
        if accion == 'errores':
            prompt = (f"Analiza este código del archivo {nombre} y dime si tiene errores "
                      f"o problemas. Responde en español, breve.\n\n{contenido}")
        elif accion == 'explicar':
            prompt = (f"Explica brevemente qué hace este código ({nombre}). "
                      f"Responde en español.\n\n{contenido}")
        else:
            prompt = (f"Resume qué hace este código ({nombre}). Responde en español, breve.\n\n{contenido}")
    else:
        modelo = MODELO_TEXTO
        if pregunta:
            prompt = (f"Basándote en este documento ({nombre}), responde en español: "
                      f"{pregunta}\n\nDocumento:\n{contenido}")
        else:
            prompt = (f"Resume brevemente este documento ({nombre}) en español, "
                      f"destacando lo más importante.\n\nDocumento:\n{contenido}")

    return _preguntar(prompt, modelo)


def analizar_texto(texto, accion='resumir'):
    """Analiza un texto dictado directamente."""
    if accion == 'resumir':
        prompt = f"Resume este texto en español, breve:\n\n{texto}"
    elif accion == 'corregir':
        prompt = f"Corrige los errores de este texto y devuélvelo corregido en español:\n\n{texto}"
    elif accion == 'traducir':
        prompt = f"Traduce este texto al inglés:\n\n{texto}"
    else:
        prompt = f"Analiza este texto en español:\n\n{texto}"
    return _preguntar(prompt, MODELO_TEXTO)


def detectar_archivo(texto):
    """
    Detecta peticiones de análisis de archivos o texto.
    Devuelve (tipo, datos...) o None.
    """
    t = texto.lower().strip()

    # Análisis de código
    if any(p in t for p in ['analiza el código', 'analiza el codigo', 'revisa el código',
                             'revisa el codigo', 'busca errores', 'tiene errores',
                             'errores en el código', 'errores en el codigo']):
        # Buscar nombre de archivo o usar el más reciente
        m = re.search(r'(?:archivo|fichero|código de|codigo de)\s+([\w\.\-]+)', t)
        if m:
            return ('codigo', 'nombre', m.group(1), 'errores')
        return ('codigo', 'reciente', None, 'errores')

    # Leer y resumir archivo
    if any(p in t for p in ['lee el archivo', 'lee el fichero', 'resume el archivo',
                             'resume el documento', 'lee el documento', 'analiza el archivo',
                             'analiza el documento', 'qué dice el archivo', 'que dice el archivo']):
        # "llamado X" tiene prioridad
        m = re.search(r'llamad[ao]\s+([\w\.\-]+)', t)
        if not m:
            # "archivo X" pero saltando palabras como "del escritorio"
            m = re.search(r'(?:archivo|fichero|documento)\s+(?:del?\s+\w+\s+)?(?:llamad[ao]\s+)?([\w\.\-]+)', t)
        if m:
            nombre = m.group(1)
            # Evitar capturar palabras vacías
            if nombre not in ['del', 'de', 'el', 'la', 'escritorio', 'documentos', 'descargas']:
                return ('archivo', 'nombre', nombre, 'resumir')
        return ('archivo', 'reciente', None, 'resumir')

    # Explicar código
    if any(p in t for p in ['explica el código', 'explica el codigo', 'qué hace el código',
                             'que hace el codigo', 'explica este código']):
        m = re.search(r'(?:archivo|código de|codigo de)\s+([\w\.\-]+)', t)
        if m:
            return ('codigo', 'nombre', m.group(1), 'explicar')
        return ('codigo', 'reciente', None, 'explicar')

    return None
