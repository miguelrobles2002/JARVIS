import threading
import tempfile
import wave
import os
import sys
import subprocess
import requests
import numpy as np
import tkinter as tk
import sounddevice as sd
import whisper
import time
import keyboard
import torch
import re
import webbrowser
import math
import datetime
import shutil
from ddgs import DDGS
import jarvis_system

# ── Configuración del usuario (debe cargarse ANTES de importar módulos opcionales) ──
from configuracion import cargar_config
CONFIG = cargar_config()
try:
    import phone_link
    PHONE_LINK_OK = True
except ImportError:
    PHONE_LINK_OK = False

try:
    import notificaciones as _noti
    NOTI_OK = True
except ImportError:
    NOTI_OK = False

try:
    import calendario as _cal
    CAL_OK = True
except ImportError:
    CAL_OK = False

try:
    import backup as _mc
    MC_OK = True
except ImportError:
    MC_OK = False

try:
    import memoria as _mem
    MEM_OK = True
except ImportError:
    MEM_OK = False

try:
    import correo as _correo
    CORREO_OK = True
except ImportError:
    CORREO_OK = False

try:
    import juegos as _juegos
    JUEGOS_OK = True
except ImportError:
    JUEGOS_OK = False

try:
    import vision as _vision
    VISION_OK = True
except ImportError:
    VISION_OK = False

try:
    import archivos as _archivos
    ARCHIVOS_OK = True
except ImportError:
    ARCHIVOS_OK = False

try:
    import imagenes as _imagenes
    # Solo activo si el usuario lo activó en la configuración
    IMAGENES_OK = CONFIG.get("usar_imagenes", False)
except ImportError:
    IMAGENES_OK = False

try:
    import futbol as _futbol
    FUTBOL_OK = True
except ImportError:
    FUTBOL_OK = False

try:
    import whatsapp as _wa
    WHATSAPP_OK = True
except ImportError:
    WHATSAPP_OK = False

try:
    import telegram_bot as _telegram
    TELEGRAM_OK = True
except ImportError:
    TELEGRAM_OK = False

try:
    import parsec_control as _parsec
    PARSEC_OK = True
except ImportError:
    PARSEC_OK = False

try:
    import procesos as _procesos
    PROCESOS_OK = True
except ImportError:
    PROCESOS_OK = False

try:
    import explorador as _explorador
    EXPLORADOR_OK = True
except ImportError:
    EXPLORADOR_OK = False

try:
    import webcam as _webcam
    WEBCAM_OK = True
except ImportError:
    WEBCAM_OK = False

# (módulos de Kali retirados en la versión pública)
KALI_OK = False
KALIVM_OK = False

# ─────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────
PIPER_EXE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piper", "piper.exe")
PIPER_MODEL   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piper", "es_ES-sharvard-medium.onnx")
PIPER_WAV     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio.wav")
OLLAMA_URL    = "http://localhost:11434/api/generate"
NOMBRE_USUARIO    = CONFIG["nombre_usuario"]
CIUDAD_USUARIO    = CONFIG["ciudad"]
MODELO_LLM        = CONFIG["modelo_llm"]
FOOTBALL_DATA_KEY = CONFIG.get("football_data_key", "")  # api de football-data.org (opcional)
MODELO_CODIGO     = CONFIG["modelo_codigo"]
SYSTEM_PROMPT     = (
    f"Eres JARVIS, el asistente personal de {NOMBRE_USUARIO}. "
    "Respondes en español de España, de forma directa y concisa. "
    "Sin emojis, sin markdown, sin LaTeX. Máximo 3 frases salvo que te pidan más."
)
SYSTEM_PROMPT_CODIGO = (
    "Eres un programador experto. Generas código limpio y funcional. "
    "Devuelve SOLO el código, sin explicaciones ni markdown."
)
WHISPER_MODEL = "small"
SAMPLE_RATE   = 16000
TECLA_ACTIVAR = "f9"
ESCRITORIO    = CONFIG["escritorio"]
NOTAS_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notas.txt")
# ─────────────────────────────────────────

listening     = False
processing    = False
whisper_model = None
DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"
timer_thread  = None


# ─── WHISPER ────────────────────────────
def cargar_whisper():
    global whisper_model
    whisper_model = whisper.load_model(WHISPER_MODEL, device=DEVICE)

def grabar_audio():
    frames = []
    def callback(indata, frame_count, time_info, status):
        if listening:
            frames.append(indata.copy())
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', callback=callback):
        while listening:
            time.sleep(0.05)
    if not frames:
        return None
    return np.concatenate(frames, axis=0)

def audio_a_texto(audio_np):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_np.tobytes())
    result = whisper_model.transcribe(
        path, language="es",
        fp16=(DEVICE == "cuda"),
        condition_on_previous_text=False,
        temperature=0,
        initial_prompt=(
            "Transcripción de conversación en español de España con términos técnicos en inglés. "
            "El asistente se llama JARVIS. "
            "Ciudades españolas: Madrid, Barcelona, Sevilla, Valencia, Bilbao, Zaragoza, "
            "Málaga, Murcia, Palma, Alicante, Córdoba, Valladolid, Vigo, Gijón, Vitoria, "
            "Granada, Elche, Oviedo, Badalona, Cartagena, Huelva, Almería, Burgos, Salamanca, "
            "Albacete, Santander, Castellón, Logroño, Badajoz, Alcalá, León, Lérida, Cádiz, Huelva. "
            "Términos técnicos: ransomware, malware, virus, phishing, CPU, GPU, RAM, SSD, WiFi, "
            "Discord, Spotify, Chrome, Firefox, Valorant, Minecraft, Steam, GitHub, Docker, "
            "streaming, gaming, fps, ping, lag, mute, screenshot, software, hardware, driver, "
            "update, download, upload, backup, cache, firewall, VPN, Bitcoin, NFT. "
            "Documentos: Word, Excel, PowerPoint, PDF, CSV, LibreOffice, OpenOffice."
        )
    )
    os.unlink(path)
    return result["text"].strip()


# ─── TTS ────────────────────────────────
# Global speaking state
_speaking_process = None
_speaking = False

# Historial de conversación (contexto entre frases)
_historial = []  # lista de {"role": "user"/"assistant", "content": "..."}
MAX_HISTORIAL = 10  # máximo de turnos a recordar

# Último resultado calculado - usando threading.local para compartir entre hilos
import threading as _threading
_state = threading.Event.__new__(threading.Event)  # dummy
_ultimo_resultado = None
_ultima_pregunta = None
_borrado_pendiente = None  # (archivo, carpeta) esperando confirmación
_evento_pendiente = None   # (evento_id, titulo) esperando confirmación de borrado
_ULTIMO_RES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultimo_resultado.txt")

def _set_ultimo(val):
    global _ultimo_resultado
    _ultimo_resultado = str(val)
    try:
        with open(_ULTIMO_RES_FILE, 'w', encoding='utf-8') as _f:
            _f.write(str(val))
    except: pass

def _get_ultimo():
    global _ultimo_resultado
    # Siempre leer del archivo para que todos los hilos vean el valor actualizado
    try:
        with open(_ULTIMO_RES_FILE, 'r', encoding='utf-8') as _f:
            val = _f.read().strip()
            if val:
                _ultimo_resultado = val
                return val
    except: pass
    return _ultimo_resultado
_ultimo_resultado = None  # último resultado numérico calculado

def detener_habla():
    """Detiene el audio en curso."""
    global _speaking_process, _speaking
    _speaking = False
    if _speaking_process:
        try:
            _speaking_process.kill()
        except:
            pass
        _speaking_process = None
    # Matar PowerShell que reproduce WAV y matar proceso de audio
    try:
        subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq Windows PowerShell'],
                       capture_output=True, creationflags=0x08000000)
        subprocess.run(['taskkill', '/F', '/IM', 'powershell.exe'],
                       capture_output=True, creationflags=0x08000000)
    except:
        pass

def hablar(texto):
    global _speaking_process, _speaking
    texto = re.sub(r'[*_`#>•]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    if not texto:
        return
    _speaking = True
    try:
        proc = subprocess.Popen(
            [PIPER_EXE, "--model", PIPER_MODEL, "--output_file", PIPER_WAV],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _speaking_process = proc
        proc.communicate(input=texto.encode("utf-8"))
        if not _speaking:
            return
        proc = subprocess.Popen(
            ["powershell", "-c", f'(New-Object Media.SoundPlayer "{PIPER_WAV}").PlaySync()'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _speaking_process = proc
        proc.wait()
    except Exception as e:
        pass
    finally:
        _speaking = False
        _speaking_process = None


def preguntar_ollama(texto):
    global _historial
    try:
        # Construir prompt con historial de conversación (SIN memoria automática)
        historial_txt = ""
        for turno in _historial[-MAX_HISTORIAL:]:
            if turno["role"] == "user":
                historial_txt += f"Usuario: {turno['content']}\n"
            else:
                historial_txt += f"JARVIS: {turno['content']}\n"

        prompt_completo = f"{SYSTEM_PROMPT}\n\n{historial_txt}Usuario: {texto}\nJARVIS:"

        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_LLM,
            "prompt": prompt_completo,
            "stream": False
        }, timeout=60)
        return r.json().get("response", "No pude obtener respuesta.").strip()
    except Exception as e:
        return f"Error al conectar con Ollama: {e}"

def preguntar_ollama_con_contexto(pregunta, contexto):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_LLM,
            "prompt": (f"{SYSTEM_PROMPT}\n\n"
                       f"Pregunta: {pregunta}\n"
                       f"Información: {contexto}\n"
                       f"Resume en 2-3 frases naturales para hablar:\nJARVIS:"),
            "stream": False
        }, timeout=60)
        return r.json().get("response", "No pude resumir.").strip()
    except Exception as e:
        return f"Error: {e}"

def generar_codigo(descripcion, lenguaje="python"):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_CODIGO,
            "prompt": f"{SYSTEM_PROMPT_CODIGO}\n\nCrea un programa en {lenguaje} que: {descripcion}\nCódigo:",
            "stream": False
        }, timeout=120)
        codigo = r.json().get("response", "").strip()
        codigo = re.sub(r'^```\w*\n?', '', codigo)
        codigo = re.sub(r'\n?```$', '', codigo)
        return codigo.strip()
    except Exception as e:
        return f"# Error: {e}"

def modificar_archivo_con_ia(ruta, instruccion):
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except Exception as e:
        return None, f"No pude leer el archivo: {e}"
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_CODIGO,
            "prompt": (f"{SYSTEM_PROMPT_CODIGO}\n\n"
                       f"Archivo actual:\n{contenido}\n\n"
                       f"Instrucción: {instruccion}\n"
                       f"Devuelve el archivo completo modificado:"),
            "stream": False
        }, timeout=120)
        nuevo = r.json().get("response", "").strip()
        nuevo = re.sub(r'^```\w*\n?', '', nuevo)
        nuevo = re.sub(r'\n?```$', '', nuevo)
        return nuevo.strip(), None
    except Exception as e:
        return None, f"Error Ollama: {e}"


# ─── DOCUMENTOS OFFICE ──────────────────
LIBREOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    r"C:\Program Files\OpenOffice 4\program\soffice.exe",
]

OFFICE_EXTS = {
    "word":        ".docx", "documento":   ".docx", "doc":         ".docx",
    "docx":        ".docx", "writer":      ".docx",
    "excel":       ".xlsx", "hoja":        ".xlsx", "xlsx":        ".xlsx",
    "calc":        ".xlsx", "spreadsheet": ".xlsx", "hoja de cálculo": ".xlsx",
    "powerpoint":  ".pptx", "presentación":".pptx", "presentacion":".pptx",
    "pptx":        ".pptx", "impress":     ".pptx", "diapositivas":".pptx",
    "pdf":         ".pdf",
    "csv":         ".csv",  "tabla":       ".csv",
}

# Programas Windows nativos como fallback
OFFICE_WINDOWS = {
    ".docx": ["winword", "wordpad"],
    ".xlsx": ["excel"],
    ".pptx": ["powerpnt"],
    ".pdf":  [],
    ".csv":  ["excel", "notepad"],
}

def crear_documento_office(tipo, nombre):
    """Crea un documento Office/LibreOffice con el nombre dado."""
    ext = OFFICE_EXTS.get(tipo.lower(), ".docx")

    # Limpiar nombre
    nombre = re.sub(r'[<>:"/\\|?*]', '', nombre).strip()
    if not nombre:
        nombre = f"documento_{datetime.datetime.now().strftime('%H%M%S')}"
    if not nombre.endswith(ext):
        nombre = nombre + ext

    ruta = os.path.join(ESCRITORIO, nombre)

    try:
        if ext == ".docx":
            try:
                from docx import Document
                doc = Document()
                doc.save(ruta)
            except ImportError:
                # Crear docx mínimo sin librería
                _crear_docx_minimo(ruta)

        elif ext == ".xlsx":
            try:
                import openpyxl
                wb = openpyxl.Workbook()
                wb.save(ruta)
            except ImportError:
                # CSV como fallback
                with open(ruta.replace(".xlsx", ".csv"), 'w') as f:
                    f.write("")
                ruta = ruta.replace(".xlsx", ".csv")

        elif ext == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation()
                prs.save(ruta)
            except ImportError:
                _crear_pptx_minimo(ruta)

        elif ext == ".pdf":
            # Crear PDF vacío mínimo
            _crear_pdf_minimo(ruta)

        elif ext == ".csv":
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("")

        # Abrir con LibreOffice si está disponible
        soffice = next((p for p in LIBREOFFICE_PATHS if os.path.isfile(p)), None)
        if soffice and ext != ".pdf":
            subprocess.Popen([soffice, ruta])
            return f"Documento {nombre} creado y abierto en LibreOffice."

        # Fallback: abrir con programa asociado de Windows
        if ext == ".pdf":
            os.startfile(ruta)
            return f"PDF {nombre} creado."
        else:
            os.startfile(ruta)
            return f"Documento {nombre} creado y abierto."

    except Exception as e:
        return f"No pude crear el documento: {e}"


def _crear_docx_minimo(ruta):
    """Crea un .docx vacío mínimo sin python-docx."""
    import zipfile, io
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    document = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t></w:t></w:r></w:p></w:body>
</w:document>'''
    word_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''
    with zipfile.ZipFile(ruta, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', document)
        z.writestr('word/_rels/document.xml.rels', word_rels)

def _crear_pptx_minimo(ruta):
    """Crea un .pptx vacío mínimo sin python-pptx."""
    import zipfile
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
    presentation = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst/><p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''
    with zipfile.ZipFile(ruta, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('ppt/presentation.xml', presentation)

def _crear_pdf_minimo(ruta):
    """Crea un PDF mínimo válido."""
    pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
    with open(ruta, 'wb') as f:
        f.write(pdf)


# ─── FÚTBOL API ─────────────────────────
def buscar_futbol_api(query):
    t = query.lower()
    if any(p in t for p in ["champions", "champion"]):
        comp_id, comp_nombre = "CL", "Champions League"
    elif any(p in t for p in ["copa del rey", "copa"]):
        comp_id, comp_nombre = "CDR", "Copa del Rey"
    else:
        comp_id, comp_nombre = "PD", "La Liga"
    try:
        r = requests.get(
            f"https://api.football-data.org/v4/competitions/{comp_id}/matches",
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params={"status": "FINISHED", "limit": 10}, timeout=8
        )
        if r.status_code != 200:
            raise Exception(f"API {r.status_code}")
        partidos = r.json().get("matches", [])
        if not partidos:
            return f"No hay partidos recientes de {comp_nombre}."
        equipos_filtro = [e for e in ["real madrid","barcelona","atletico","atletico de madrid",
            "sevilla","valencia","betis","villarreal","athletic","sociedad","osasuna",
            "girona","mallorca","celta","espanyol","valladolid","leganes"] if e in t]
        resultados = []
        for m in partidos[-8:]:
            local     = m["homeTeam"]["shortName"] or m["homeTeam"]["name"]
            visitante = m["awayTeam"]["shortName"] or m["awayTeam"]["name"]
            gl = m["score"]["fullTime"]["home"]
            gv = m["score"]["fullTime"]["away"]
            fecha = m["utcDate"][:10]
            if equipos_filtro:
                nombres = (local + " " + visitante).lower()
                if not any(e in nombres for e in equipos_filtro):
                    continue
            if gl is not None and gv is not None:
                resultados.append(f"{local} {gl}-{gv} {visitante} ({fecha})")
        if not resultados:
            return f"No encontré partidos recientes para ese equipo en {comp_nombre}."
        return preguntar_ollama_con_contexto(query,
            comp_nombre + ": " + ". ".join(resultados[-5:]))
    except Exception as e:
        try:
            with DDGS() as ddgs:
                res = list(ddgs.text(query + " resultado LaLiga España", max_results=4))
            if res:
                return preguntar_ollama_con_contexto(query,
                    " | ".join([r.get("body","")[:250] for r in res[:3]]))
        except:
            pass
        return f"No pude obtener resultados: {e}"


def partidos_de_hoy(fecha=None):
    """Devuelve todos los partidos de una fecha (por defecto hoy)."""
    from datetime import datetime
    hoy = fecha if fecha else datetime.now().strftime("%Y-%m-%d")
    # Principales competiciones
    competiciones = {
        "WC": "Mundial", "PD": "La Liga", "PL": "Premier", "SA": "Serie A",
        "BL1": "Bundesliga", "FL1": "Ligue 1", "CL": "Champions",
        "EC": "Eurocopa",
    }
    todos = []
    for comp_id, nombre in competiciones.items():
        try:
            r = requests.get(
                f"https://api.football-data.org/v4/competitions/{comp_id}/matches",
                headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
                params={"dateFrom": hoy, "dateTo": hoy}, timeout=8  # hoy = fecha objetivo
            )
            if r.status_code != 200:
                continue
            partidos = r.json().get("matches", [])
            for m in partidos:
                local     = m["homeTeam"]["shortName"] or m["homeTeam"]["name"]
                visitante = m["awayTeam"]["shortName"] or m["awayTeam"]["name"]
                estado    = m["status"]
                gl = m["score"]["fullTime"]["home"]
                gv = m["score"]["fullTime"]["away"]
                if estado == "FINISHED" and gl is not None:
                    todos.append(f"{nombre}: {local} {gl}-{gv} {visitante}")
                elif estado in ("IN_PLAY", "PAUSED"):
                    todos.append(f"{nombre}: {local} {gl or 0}-{gv or 0} {visitante} (en juego)")
                elif estado in ("SCHEDULED", "TIMED"):
                    hora = m["utcDate"][11:16]
                    todos.append(f"{nombre}: {local} contra {visitante} a las {hora}")
        except:
            continue

    if not todos:
        # Fallback: buscar en web
        resultado_api = _partidos_livescore(fecha=hoy)
        if resultado_api:
            return resultado_api
        return "No encontré partidos para esa fecha."

    n = len(todos)
    cuando = "Hoy" if not fecha else "Ese día"
    return f"{cuando} hay {n} partido{'s' if n != 1 else ''}. " + ". ".join(todos[:12])


def _partidos_livescore(fecha=None):
    """Obtiene partidos de una fecha buscando en webs de resultados."""
    try:
        from datetime import datetime
        # Construir query con la fecha
        if fecha:
            try:
                dt = datetime.strptime(fecha, "%Y-%m-%d")
                fecha_txt = dt.strftime("%d de %B de %Y").lower()
                meses_es = {'january':'enero','february':'febrero','march':'marzo',
                           'april':'abril','may':'mayo','june':'junio','july':'julio',
                           'august':'agosto','september':'septiembre','october':'octubre',
                           'november':'noviembre','december':'diciembre'}
                for en, es in meses_es.items():
                    fecha_txt = fecha_txt.replace(en, es)
                query = f"resultados mundial 2026 {fecha_txt} todos los marcadores"
            except:
                query = "resultados mundial 2026 hoy marcadores"
        else:
            query = "resultados mundial 2026 hoy marcadores en directo"
        with DDGS() as ddgs:
            res = list(ddgs.text(query, max_results=8))

        if not res:
            return None

        # Juntar todo el texto de los resultados
        texto_total = " ".join(r.get("body", "") for r in res)

        # Varios patrones de marcador
        patrones = [
            # "Alemania 7-1 Curazao"
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
            # "Alemania 7 - 1 Curazao"
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(\d{1,2})\s+[-–]\s+(\d{1,2})\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',
            # "Alemania vs Curazao 7-1"
            r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(?:vs\.?|contra|-)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})',
        ]
        partidos = []
        vistos = set()
        for i, patron in enumerate(patrones):
            for m in re.finditer(patron, texto_total):
                g = m.groups()
                if i == 2:  # patrón "vs" tiene orden distinto
                    local, visit, gl, gv = g[0], g[1], g[2], g[3]
                else:
                    local, gl, gv, visit = g[0], g[1], g[2], g[3]
                local, visit = local.strip(), visit.strip()
                clave = f"{local.lower()}{visit.lower()}"
                if clave not in vistos and len(local) > 2 and len(visit) > 2:
                    vistos.add(clave)
                    partidos.append(f"{local} {gl}-{gv} {visit}")

        if partidos:
            n = len(partidos)
            return f"Resultados: " + ". ".join(partidos[:12])

        # Si no hay marcadores claros, extraer con Ollama de forma estricta
        return preguntar_ollama_con_contexto(
            "Extrae y lista los partidos con sus marcadores del texto. "
            "Formato: 'Equipo1 X-Y Equipo2'. Una línea por partido. "
            "NO añadas explicaciones ni menciones webs. Solo la lista.",
            texto_total[:1500])
    except Exception:
        return None


def buscar_partido_equipo(equipo, fecha=None):
    """Busca el resultado de un partido concreto de un equipo."""
    from datetime import datetime
    try:
        cuando = ""
        if fecha:
            try:
                dt = datetime.strptime(fecha, "%Y-%m-%d")
                cuando = dt.strftime("%d de %B").lower()
                for en, es in {'january':'enero','february':'febrero','march':'marzo',
                              'april':'abril','may':'mayo','june':'junio','july':'julio',
                              'august':'agosto','september':'septiembre','october':'octubre',
                              'november':'noviembre','december':'diciembre'}.items():
                    cuando = cuando.replace(en, es)
            except:
                pass

        query = f"resultado {equipo} {cuando} marcador partido"
        with DDGS() as ddgs:
            res = list(ddgs.text(query, max_results=5))

        if not res:
            return f"No encontré el partido de {equipo}."

        texto_total = " ".join(r.get("body", "") for r in res)

        # Buscar marcador donde aparezca el equipo
        patron = (r'([A-ZÁÉÍÓÚÑ][\w\sáéíóúñ\.]{2,25}?)\s+(\d{1,2})\s*[-:]\s*'
                  r'(\d{1,2})\s+([A-ZÁÉÍÓÚÑ][\w\sáéíóúñ\.]{2,25}?)(?:\s|,|\.|$)')
        for m in re.finditer(patron, texto_total):
            local, gl, gv, visit = m.groups()
            if equipo.lower() in (local + " " + visit).lower():
                return f"{local.strip()} {gl}-{gv} {visit.strip()}."

        # Si no hay marcador claro, dejar que Ollama lo extraiga
        return preguntar_ollama_con_contexto(
            f"¿Cómo quedó el partido de {equipo}? Responde solo con el marcador, directo.",
            texto_total[:1000])
    except Exception as e:
        return f"No pude buscar el partido de {equipo}: {e}"


# ─── UTILIDADES ─────────────────────────
def get_tiempo(ciudad="Madrid"):
    try:
        # format=3 da solo temperatura actual, usamos format más completo
        r = requests.get(
            f"https://wttr.in/{ciudad}?format=%l:+%C,+temp+%t,+max+%T,+lluvia+%p&lang=es",
            timeout=5
        )
        resultado = r.text.strip()
        if "Unknown" in resultado or not resultado:
            r2 = requests.get(f"https://wttr.in/{ciudad}?format=3", timeout=5)
            resultado = r2.text.strip()
        return resultado
    except:
        return f"No pude obtener el tiempo de {ciudad}."

def calcular(expr):
    try:
        expr_limpia = re.sub(r'[^\d\+\-\*\/\(\)\.\s]', '', expr)
        resultado = eval(expr_limpia, {"__builtins__": {}}, {"sqrt": math.sqrt, "pi": math.pi})
        return str(resultado)
    except:
        return preguntar_ollama(f"Calcula esto y responde solo el número: {expr}")



def calcular_expresion_hablada(texto):
    """Convierte expresión matemática hablada a número."""
    import math as _math
    t = texto.lower().strip().rstrip(".,;:¿?¡!")

    # Resolver referencias al último resultado: "por 9", "y le sumo 3", "entre 2"
    if _ultimo_resultado is not None:
        ref_patterns = [
            (r'^(?:y\s+)?(?:m[aá]s|súmale?|añade?)\s+([\d,.]+)', lambda m: f"{_ultimo_resultado} más {m.group(1)}"),
            (r'^(?:y\s+)?(?:menos|réstale?)\s+([\d,.]+)', lambda m: f"{_ultimo_resultado} menos {m.group(1)}"),
            (r'^(?:y\s+)?(?:por|multiplica(?:do)?\s+por)\s+([\d,.]+)', lambda m: f"{_ultimo_resultado} por {m.group(1)}"),
            (r'^(?:y\s+)?(?:entre|divide?\s+(?:entre|por))\s+([\d,.]+)', lambda m: f"{_ultimo_resultado} entre {m.group(1)}"),
            (r'^por\s+([\d,.]+)$', lambda m: f"{_ultimo_resultado} por {m.group(1)}"),
            (r'^entre\s+([\d,.]+)$', lambda m: f"{_ultimo_resultado} entre {m.group(1)}"),
            (r'^m[aá]s\s+([\d,.]+)$', lambda m: f"{_ultimo_resultado} más {m.group(1)}"),
            (r'^menos\s+([\d,.]+)$', lambda m: f"{_ultimo_resultado} menos {m.group(1)}"),
        ]
        for pat, repl in ref_patterns:
            m = re.match(pat, t)
            if m:
                t = repl(m)
                break
    # Convertir números en letras a dígitos
    NUMS_PALABRAS = {
        r'\bcero\b': '0', r'\bun[oa]?\b': '1', r'\bdos\b': '2',
        r'\btres\b': '3', r'\bcuatro\b': '4', r'\bcinco\b': '5',
        r'\bseis\b': '6', r'\bsiete\b': '7', r'\bocho\b': '8',
        r'\bnueve\b': '9', r'\bdiez\b': '10', r'\bonce\b': '11',
        r'\bdoce\b': '12', r'\btrece\b': '13', r'\bcatorce\b': '14',
        r'\bquince\b': '15', r'\bdieciséis\b': '16', r'\bdiecisiete\b': '17',
        r'\bdieciocho\b': '18', r'\bdiecinueve\b': '19', r'\bveinte\b': '20',
        r'\bveintiuno\b': '21', r'\bveintidós\b': '22', r'\bveintitrés\b': '23',
        r'\bveinticuatro\b': '24', r'\bveinticinco\b': '25',
        r'\btreinta\b': '30', r'\bcuarenta\b': '40', r'\bcincuenta\b': '50',
        r'\bsesenta\b': '60', r'\bsetenta\b': '70', r'\bochenta\b': '80',
        r'\bnoventa\b': '90', r'\bcien\b': '100', r'\bciento\b': '100',
        r'\bdoscientos\b': '200', r'\btrescientos\b': '300',
        r'\bcuatrocientos\b': '400', r'\bquinientos\b': '500',
        r'\bseiscientos\b': '600', r'\bsetecientos\b': '700',
        r'\bochocientos\b': '800', r'\bnovecientos\b': '900',
        r'\bmil\b': '1000',
    }
    for patron, num in NUMS_PALABRAS.items():
        t = re.sub(patron, num, t)

    sustituciones = [
        (r'\bm[aá]s\b', '+'),
        (r'\bplus\b', '+'),
        (r'\bmenos\b', '-'),
        (r'\bminus\b', '-'),
        (r'\bpor\b', '*'),
        (r'\btimes\b', '*'),
        (r'\bmultiplied\s+by\b', '*'),
        (r'\bentre\b', '/'),
        (r'\bdivided\s+by\b', '/'),
        (r'\bsobre\b', '/'),
        (r'\bdividido\b', '/'),
        (r'\bal\s+cuadrado\b', '**2'),
        (r'\bcuadrado\b', '**2'),
        (r'\bal\s+cubo\b', '**3'),
        (r'\bcubo\b', '**3'),
        (r'\belevado\s+al?\s+(\d+)\b', r'**\1'),
        (r'\bal\s+(\d+)\b', r'**\1'),
        (r'\bpi\b', str(_math.pi)),
    ]
    for patron, reemplazo in sustituciones:
        t = re.sub(patron, reemplazo, t)
    # Raíz cuadrada, seno, coseno, tangente con valores numéricos
    def repl_sqrt(m): return str(round(_math.sqrt(float(m.group(1))), 8))
    def repl_sin(m): return str(round(_math.sin(_math.radians(float(m.group(1)))), 8))
    def repl_cos(m): return str(round(_math.cos(_math.radians(float(m.group(1)))), 8))
    def repl_tan(m): return str(round(_math.tan(_math.radians(float(m.group(1)))), 8))
    # Variantes de raíz que Whisper puede transcribir
    for _rv in ['raíz cuadrada de', 'raiz cuadrada de', 'raíz de', 'raiz de',
                'rais de', 'rais cuadrada de', 'rise de', 'race de',
                'race cuadrada de', 'rise cuadrada de',
                'rise de', 'race de', 'rais', 'rise', 'race']:
        t = t.replace(_rv, '__SQRT__ ')
    # Limpiar dobles espacios por si acaso
    import re as _re_sqrt
    t = _re_sqrt.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'__SQRT__\s+([\d\.]+)', repl_sqrt, t)
    t = re.sub(r'seno\s+de\s+([\d\.]+)', repl_sin, t)
    t = re.sub(r'coseno\s+de\s+([\d\.]+)', repl_cos, t)
    t = re.sub(r'tangente\s+de\s+([\d\.]+)', repl_tan, t)
    # Convertir dígito-x-dígito antes de quitar letras (evita "2x2" -> "22")
    # Aplicar dos veces para "3x3x3" -> "3*3*3"
    t = re.sub(r'(\d)[xX×](\d)', r'\1*\2', t)
    t = re.sub(r'(\d)[xX×](\d)', r'\1*\2', t)
    expr = re.sub(r'[^\d\+\-\*\/\(\)\.\s]', '', t).strip()
    if not expr:
        return None
    try:
        resultado = eval(expr, {"__builtins__": {}}, {})
        if isinstance(resultado, float):
            resultado = round(resultado, 8)
            if resultado == int(resultado): resultado = int(resultado)
        return str(resultado)
    except:
        return None


def formatear_resultado(expr):
    """Convierte expresión SymPy a notación matemática limpia: -3x² + 2x"""
    import sympy as sp
    import re

    try:
        expr = sp.nsimplify(expr, rational=True)
        s = str(expr)

        # Potencias: x**2 -> x^2, x**3 -> x^3
        def repl_pow(m):
            return f"{m.group(1)}^{m.group(2)}"

        s = re.sub(r'([a-zA-Z])\*\*(\d+)', repl_pow, s)

        # Coeficientes: 3*x -> 3x
        s = re.sub(r'(\d)\*([a-zA-Z])', r'\1\2', s)

        # Funciones especiales
        s = s.replace('log(x)', 'ln(x)')
        s = s.replace('sqrt(', '√(')

        return s.strip()
    except:
        return str(expr)


def calcular_mates(texto):
    """Calculadora matemática avanzada con SymPy."""
    import re as _re
    from sympy import symbols, diff, integrate, limit, solve, simplify, sin, cos, tan, exp, log, sqrt, pi, oo, factor, expand, sympify
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    x, y, z = symbols('x y z')
    transformations = standard_transformations + (implicit_multiplication_application,)

    t = texto.lower().strip()

    def limpiar_expr(s):
        s = s.lower().strip().rstrip('.,;:¿?¡! ')
        s = s.replace('\u00b2','**2').replace('\u00b3','**3').replace('\u00b2','**2')
        s = s.replace('²','**2').replace('³','**3')
        reemplazos = [
            (_re.compile(r'\b(?:al\s+)?cuadrado\b'), '**2'),
            (_re.compile(r'\b(?:al\s+)?cubo\b'), '**3'),
            (_re.compile(r'\belevado\s+al?\s+(\d+)\b'), r'**\1'),
            (_re.compile(r'\bal\s+(\d+)\b'), r'**\1'),
            (_re.compile(r'\bmenos\b'), '-'),
            (_re.compile(r'\bm[a\u00e1]s\b'), '+'),
            (_re.compile(r'\bpor\b'), '*'),
            (_re.compile(r'\bentre\b'), '/'),
            (_re.compile(r'\bsobre\b'), '/'),
            (_re.compile(r'\bra[i\u00ed]z\s+(?:cuadrada\s+)?de\b'), 'sqrt('),
            (_re.compile(r'\blogaritmo\s+neperiano\s+de\s+(\w+)'), r'log(\1)'),
            (_re.compile(r'\blogaritmo\s+neperiano\b'), 'log(x)'),
            (_re.compile(r'\bseno\s+de\b'), 'sin('),
            (_re.compile(r'\bcoseno\s+de\b'), 'cos('),
            (_re.compile(r'\btangente\s+de\b'), 'tan('),
        ]
        for pat, rep in reemplazos:
            s = pat.sub(rep, s)
        abiertos = s.count('(') - s.count(')')
        s += ')' * max(0, abiertos)
        s = s.replace('^','**').replace('ln(','log(').replace('tg(','tan(')
        s = _re.sub(r'sen\b', 'sin', s)
        # x2 -> x**2 (Whisper omite superíndice)
        # x2/x3 sin espacio y variantes habladas
        s = _re.sub(r'x([23456789])(?=[^\d]|$)', r'x**\1', s)
        # "x dos" "x tres" etc (Whisper con espacio)
        nums_spoken = {'dos':'2','tres':'3','cuatro':'4','cinco':'5',
                       'seis':'6','siete':'7','ocho':'8','nueve':'9','diez':'10'}
        for palabra, num in nums_spoken.items():
            s = _re.sub(rf'x\s+{palabra}\b', f'x**{num}', s)
        return s

    # ── Derivada ──────────────────────────────────────────
    m = _re.search(r'(?:deriva(?:da)?|diferencial)\s+(?:de\s+)?(.+?)(?:\s+respecto|\s*$)', t)
    if m and any(p in t for p in ['deriva','derivada','diferencial']):
        expr_str = limpiar_expr(m.group(1).strip())
        try:
            expr = parse_expr(expr_str, transformations=transformations)
            r = formatear_resultado(diff(expr, x))
            if r != '0' or not any(v in expr_str for v in ['x','y','z']):
                return r
        except:
            pass

    # ── Integral doble ────────────────────────────────────
    if 'doble' in t and any(p in t for p in ['integral','integra']):
        m = _re.search(r'(?:integr(?:al|a))\s+(?:doble\s+)?(?:de\s+)?(.+)', t)
        if m:
            expr_str = limpiar_expr(m.group(1).strip())
            try:
                expr = parse_expr(expr_str, transformations=transformations)
                return formatear_resultado(integrate(integrate(expr, x), y)) + " + C"
            except: pass

    # ── Integral triple ───────────────────────────────────
    if 'triple' in t and any(p in t for p in ['integral','integra']):
        m = _re.search(r'(?:integr(?:al|a))\s+(?:triple\s+)?(?:de\s+)?(.+)', t)
        if m:
            expr_str = limpiar_expr(m.group(1).strip())
            try:
                expr = parse_expr(expr_str, transformations=transformations)
                return formatear_resultado(integrate(integrate(integrate(expr, x), y), z)) + " + C"
            except: pass

    # ── Integral simple ───────────────────────────────────
    m = _re.search(r'(?:integr(?:al|a))\s+(?:de\s+)?(.+?)(?:\s+d[xyz]|\s*$)', t)
    if m and any(p in t for p in ['integral','integra','primitiva']):
        expr_str = limpiar_expr(m.group(1).strip())
        try:
            expr = parse_expr(expr_str, transformations=transformations)
            return formatear_resultado(integrate(expr, x)) + " + C"
        except: pass

    # ── Límite ────────────────────────────────────────────
    m = _re.search(r'l[i\u00ed]mite?\s+(?:de\s+)?(.+?)\s+(?:cuando|si|para)?\s*x\s*(?:tiende|->|→)\s*([\d\-\+inf]+|infinito)', t)
    if m and any(p in t for p in ['límite','limite','lim']):
        expr_str = limpiar_expr(m.group(1).strip())
        punto_str = m.group(2).strip()
        punto = oo if 'inf' in punto_str or 'infinito' in punto_str else sympify(punto_str)
        try:
            expr = parse_expr(expr_str, transformations=transformations)
            return str(limit(expr, x, punto))
        except: pass

    # ── Resolver ecuación ─────────────────────────────────
    m = _re.search(r'(?:resuelve?|soluciona?|halla?\s+x|despeja?\s+x)\s+(?:la\s+ecuaci[o\u00f3]n\s+)?(.+)', t)
    if m and any(p in t for p in ['resuelve','soluciona','ecuación','ecuacion','despeja']):
        expr_str = limpiar_expr(m.group(1).strip())
        if '=' in expr_str:
            partes = expr_str.split('=')
            expr_str = f"({partes[0]}) - ({partes[1]})"
        try:
            expr = parse_expr(expr_str, transformations=transformations)
            sols = solve(expr, x)
            if sols:
                return "x = " + ", ".join(str(s) for s in sols)
            return "Sin solución real."
        except: pass

    # ── Simplificar ───────────────────────────────────────
    m = _re.search(r'simplifica?\s+(.+)', t)
    if m:
        try:
            expr = parse_expr(limpiar_expr(m.group(1).strip()), transformations=transformations)
            return str(simplify(expr))
        except: pass

    # ── Factorizar ────────────────────────────────────────
    m = _re.search(r'factori[zs]a?\s+(.+)', t)
    if m:
        try:
            expr = parse_expr(limpiar_expr(m.group(1).strip()), transformations=transformations)
            return str(factor(expr))
        except: pass

    return None


# ─── APPS ───────────────────────────────
APPS = {
    "notepad":  ["bloc de notas", "notepad", "bloc"],
    "calc":     ["calculadora", "calc"],
    "explorer": ["explorador de archivos", "explorador", "explorer"],
    "mspaint":  ["paint", "pintura"],
    "taskmgr":  ["administrador de tareas", "task manager"],
    "msedge":   ["edge", "microsoft edge"],
    os.path.join(ESCRITORIO, r"Google Chrome.lnk"):                       ["chrome", "google chrome", "navegador"],
    os.path.join(ESCRITORIO, r"Firefox.exe"):                             ["firefox"],
    os.path.join(ESCRITORIO, r"Discord.lnk"):                            ["discord"],
    os.path.join(ESCRITORIO, r"Spotify.lnk"):                            ["spotify"],
    os.path.join(ESCRITORIO, r"Visual Studio Code.lnk"):                 ["visual studio code", "vscode", "vs code", "visual studio"],
    os.path.join(ESCRITORIO, r"Docker Desktop.lnk"):                     ["docker", "docker desktop"],
    os.path.join(ESCRITORIO, r"Battle.net.lnk"):                         ["battle.net", "battlenet", "blizzard"],
    os.path.join(ESCRITORIO, r"Battlefront.lnk"):                        ["battlefront", "star wars battlefront"],
    os.path.join(ESCRITORIO, r"CrystalDiskInfo.lnk"):                    ["crystaldiskinfo", "crystal disk"],
    os.path.join(ESCRITORIO, r"EA.lnk"):                                  ["ea", "ea games"],
    os.path.join(ESCRITORIO, r"Hogwarts Legacy.url"):                     ["hogwarts", "hogwarts legacy"],
    os.path.join(ESCRITORIO, r"Jugar a Grand Theft Auto V Enhanced.lnk"): ["gta", "gta 5", "grand theft auto"],
    os.path.join(ESCRITORIO, r"Jugar a Red Dead Redemption 2.lnk"):       ["red dead", "rdr2", "red dead redemption"],
    os.path.join(ESCRITORIO, r"Minecraft Launcher - Acceso directo.lnk"): ["minecraft"],
    os.path.join(ESCRITORIO, r"Movavi Video Editor Plus 2020.lnk"):       ["movavi", "editor de video", "editor de vídeo"],
    os.path.join(ESCRITORIO, r"MSI Afterburner.lnk"):                     ["msi afterburner", "afterburner", "overclock"],
    os.path.join(ESCRITORIO, r"Rocket League®.url"):                      ["rocket league", "rocket"],
    os.path.join(ESCRITORIO, r"Rockstar Games Launcher.lnk"):             ["rockstar", "rockstar games"],
    os.path.join(ESCRITORIO, r"Ubisoft Connect.lnk"):                     ["ubisoft", "uplay", "ubisoft connect"],
    os.path.join(ESCRITORIO, r"Far Cry Primal.url"):                      ["far cry", "far cry primal"],
    r"C:\Riot Games\Riot Client\RiotClientServices.exe":            ["valorant", "riot"],
    "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe": ["brave", "navegador brave"],
    # Microsoft Office 2010
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Microsoft Office\Microsoft Word 2010.lnk": ["word", "microsoft word"],
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Microsoft Office\Microsoft Excel 2010.lnk": ["excel", "microsoft excel"],
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Microsoft Office\Microsoft PowerPoint 2010.lnk": ["powerpoint", "power point", "presentaciones"],
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Microsoft Office\Microsoft Outlook 2010.lnk": ["outlook", "correo outlook"],
}

EXTENSIONES = {
    "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
    "html": ".html", "css": ".css", "java": ".java", "c": ".c",
    "cpp": ".cpp", "typescript": ".ts", "texto": ".txt", "txt": ".txt",
    "markdown": ".md", "json": ".json", "bash": ".sh", "powershell": ".ps1",
}

WEBS = {
    "youtube":      ("https://youtube.com", "YouTube"),
    "twitter":      ("https://twitter.com", "Twitter"),
    "instagram":    ("https://instagram.com", "Instagram"),
    "gmail":        ("https://mail.google.com", "Gmail"),
    "correo":       ("https://mail.google.com", "tu correo"),
    "google":       ("https://google.com", "Google"),
    "twitch":       ("https://twitch.tv", "Twitch"),
    "github":       ("https://github.com", "GitHub"),
    "chatgpt":      ("https://chat.openai.com", "ChatGPT"),
    "whatsapp":     ("https://web.whatsapp.com", "WhatsApp Web"),
    "reddit":       ("https://reddit.com", "Reddit"),
    "netflix":      ("https://netflix.com", "Netflix"),
    "disney plus":  ("https://disneyplus.com", "Disney Plus"),
    "disney":       ("https://disneyplus.com", "Disney Plus"),
    "crunchyroll":  ("https://crunchyroll.com", "Crunchyroll"),
    "crunchiroll":  ("https://crunchyroll.com", "Crunchyroll"),
    "prime":        ("https://primevideo.com", "Prime Video"),
    "amazon prime": ("https://primevideo.com", "Prime Video"),
    "hbo":          ("https://max.com", "Max"),
    "max":          ("https://max.com", "Max"),
    "pornhub":      ("https://pornhub.com", "Pornhub"),
    "xvideos":      ("https://xvideos.com", "Xvideos"),
    "twitter x":    ("https://x.com", "X"),
}




def traducir(texto, idioma_destino="inglés"):
    """Traduce texto usando Ollama."""
    idiomas = {
        "inglés": "English", "ingles": "English",
        "francés": "French", "frances": "French",
        "alemán": "German", "aleman": "German",
        "italiano": "Italian",
        "portugués": "Portuguese", "portugues": "Portuguese",
        "chino": "Chinese",
        "japonés": "Japanese", "japones": "Japanese",
        "árabe": "Arabic", "arabe": "Arabic",
        "ruso": "Russian",
        "español": "Spanish",
    }
    idioma_en = idiomas.get(idioma_destino.lower(), idioma_destino)
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO_LLM,
            "prompt": (
                f"Translate the following text to {idioma_en}. "
                f"Reply ONLY with the translation, nothing else:\n\n{texto}"
            ),
            "stream": False
        }, timeout=60)
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"Error al traducir: {e}"

# ─── DETECCIÓN ──────────────────────────
def detectar_accion(texto):
    t = texto.lower().strip().rstrip('.,;:¿?¡! ')

    # Confirmación de borrado pendiente (alta prioridad)
    if _borrado_pendiente is not None:
        if any(p in t for p in ['sí confirma', 'si confirma', 'sí, confirma', 'confirma',
                                'confírmalo', 'confirmalo', 'sí bórralo', 'si borralo',
                                'sí borra', 'si borra', 'adelante', 'hazlo', 'sí hazlo']):
            return ("confirmar_borrado",)
        if any(p in t for p in ['no', 'cancela', 'cancelar', 'déjalo', 'dejalo', 'mejor no']):
            return ("cancelar_borrado",)

    # Confirmación de borrado de EVENTO pendiente
    if _evento_pendiente is not None:
        if any(p in t for p in ['sí confirma', 'si confirma', 'sí, confirma', 'confirma',
                                'confírmalo', 'confirmalo', 'sí bórralo', 'si borralo',
                                'sí borra', 'si borra', 'adelante', 'hazlo', 'sí hazlo']):
            return ("confirmar_borrado_evento",)
        if any(p in t for p in ['no', 'cancela', 'cancelar', 'déjalo', 'dejalo', 'mejor no']):
            return ("cancelar_borrado_evento",)

    # Cerrar JARVIS (alta prioridad)
    if any(p in t for p in ['cierra jarvis', 'cierra el programa', 'apágate', 'apagate',
                            'ciérrate', 'cierrate', 'cierra el asistente', 'adiós jarvis',
                            'adios jarvis', 'apaga jarvis']):
        return ("cerrar_jarvis",)

    # Parsec (abrir / compartir / dejar de compartir)
    if PARSEC_OK:
        _pq = _parsec.detectar_parsec(t)
        if _pq:
            return ("parsec", _pq[0])

    # Procesos abiertos
    if PROCESOS_OK:
        _proc = _procesos.detectar_procesos(t)
        if _proc:
            return ("procesos", _proc[0])

    # Borrar evento del calendario (ANTES que explorador, para que no lo confunda con archivos)
    if CAL_OK:
        _nom_ev = _cal.detectar_borrado_evento(t)
        if _nom_ev:
            return ("borrar_evento", _nom_ev)

    # Explorador de carpetas/archivos
    if EXPLORADOR_OK:
        _exp = _explorador.detectar_explorador(t)
        if _exp:
            return ("explorador",) + _exp

    # Captura de pantalla (para enviar por Telegram)
    if any(p in t for p in ['mándame una captura', 'mandame una captura',
                            'captura de pantalla', 'haz una captura',
                            'pantallazo', 'manda captura', 'envíame una captura',
                            'enviame una captura', 'foto de la pantalla',
                            'mándame la pantalla', 'mandame la pantalla']):
        return ("captura_telegram",)

    # Foto con webcam (para enviar por Telegram)
    if WEBCAM_OK:
        if _webcam.detectar_webcam(t):
            return ("webcam_foto",)

    # WhatsApp / mensajes (PRIORIDAD MÁXIMA si menciona whatsapp/mensaje)
    # Evita que "manda whatsapp ¿a qué hora...?" dispare hora_fecha
    # Incluye variantes que Whisper transcribe mal: mándalo -> vandalon, vándalo
    VERBOS_ENVIAR = ['manda', 'mándale', 'mandale', 'mándalo', 'mandalo',
                     'vandalon', 'vándalo', 'vandalo', 'bandalo', 'bándalo',
                     'envía', 'envia', 'enviale', 'envíale', 'enviar',
                     'escribe', 'escríbele', 'escribele', 'mensajea']
    if WHATSAPP_OK and any(p in t for p in ['whatsapp', 'wasap', 'wasá', 'guasap', 'guasá', 'wasapea']):
        # Si menciona WhatsApp explícitamente, va a WhatsApp aunque tenga "qué hora"
        if any(v in t for v in VERBOS_ENVIAR) or t.split()[0] in VERBOS_ENVIAR:
            wa = _wa.detectar_whatsapp(texto)
            if wa:
                return ("whatsapp", wa[0], wa[1])
        # Aunque no detecte el verbo claro, si dice "whatsapp a X" es envío
        import re as _re_wa
        if _re_wa.search(r'whatsapp\s+a\s+\w+|wasap\s+a\s+\w+', t):
            wa = _wa.detectar_whatsapp(texto)
            if wa:
                return ("whatsapp", wa[0], wa[1])

    # Generación de imágenes (PRIORIDAD ALTA - antes que fútbol, etc.)
    if IMAGENES_OK:
        desc = _imagenes.detectar_generacion(t)
        if desc:
            return ("generar_imagen", desc)

    # Operación encadenada usando último resultado
    _ult = _get_ultimo()
    if _ult is not None:
        # Números en letras
        NUMS_LETRAS = {
            'cero':0,'uno':1,'una':1,'dos':2,'tres':3,'cuatro':4,'cinco':5,
            'seis':6,'siete':7,'ocho':8,'nueve':9,'diez':10,'once':11,
            'doce':12,'trece':13,'catorce':14,'quince':15,'veinte':20,
            'veintiuno':21,'veintidos':22,'veintidos':22,'veintitrés':23,
            'treinta':30,'cuarenta':40,'cincuenta':50,'sesenta':60,
            'setenta':70,'ochenta':80,'noventa':90,'cien':100,'ciento':100,
            'mil':1000,'un millón':1000000
        }
        ops_map = {'más':'+', 'mas':'+', 'plus':'+',
                   'menos':'-', 'minus':'-',
                   'por':'*', 'times':'*',
                   'entre':'/', 'dividido':'/', 'divided by':'/'}

        m_chain = re.match(
            r'^(m[aá]s|menos|por|entre|dividido(?:\s+entre)?|plus|minus|times|divided\s+by)'
            r'\s+([\d\.]+|[a-záéíóúñ\s]+?)$', t)
        if m_chain:
            op_str = m_chain.group(1).strip()
            num_str = m_chain.group(2).strip()
            op = ops_map.get(op_str)
            # Convertir número en letras si es necesario
            num_val = None
            try:
                num_val = float(num_str)
            except:
                num_val = NUMS_LETRAS.get(num_str)
            if op and num_val is not None:
                try:
                    res = eval(f"{_ult}{op}{num_val}", {'__builtins__': {}}, {})
                    if isinstance(res, float):
                        if res == int(res):
                            res = int(res)
                        else:
                            res = round(res, 6)
                    return ("calcular_directo", str(res))
                except:
                    pass

    # Expresión aritmética directa: "7x2x3", "3+5", "12/4", números con operadores
    # Solo si el texto ES una expresión numérica pura (sin palabras)
    expr_directa_test = re.sub(r'\s+', '', t)
    # Convertir dígito-x-dígito ANTES de reemplazar x->* para evitar pegar números
    expr_directa_test = re.sub(r'(\d)x(\d)', r'\1*\2', expr_directa_test)
    expr_directa_test = expr_directa_test.replace('x', '*').replace('×', '*').replace('÷', '/')
    if re.match(r'^[\d\+\-\*\/\.\(\)]+$', expr_directa_test) and re.search(r'[\+\-\*\/]', expr_directa_test):
        try:
            resultado = eval(expr_directa_test, {"__builtins__": {}}, {})
            if isinstance(resultado, float) and resultado == int(resultado):
                resultado = int(resultado)
            return ("calcular_directo", str(round(resultado, 8) if isinstance(resultado, float) else resultado))
        except:
            pass

    # Media / promedio directos sin "cuánto es"
    if any(p in t for p in ["media de", "media del", "promedio de", "promedio del",
                              "la media", "el promedio", "calcular media", "calcular promedio"]):
        numeros = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', t)]
        if numeros:
            media = sum(numeros) / len(numeros)
            media = round(media, 4) if media != int(media) else int(media)
            return ("calcular_directo", str(media))

    # Hora y fecha
    if any(p in t for p in ["qué hora", "que hora", "qué día", "que dia", "qué fecha", "que fecha", "día es hoy", "fecha de hoy"]):
        return ("hora_fecha",)

    # Tiempo meteorológico — ciudad explícita primero
    CIUDADES_ES = [
        "madrid", "barcelona", "sevilla", "valencia", "bilbao", "zaragoza",
        "málaga", "malaga", "murcia", "palma", "alicante", "córdoba", "cordoba",
        "valladolid", "vigo", "gijón", "gijon", "vitoria", "granada", "elche",
        "oviedo", "badalona", "cartagena", "huelva", "vuelvo", "huelba", "welva", "almería", "almeria",
        "burgos", "salamanca", "albacete", "santander", "castellón", "castellon",
        "logroño", "logrono", "badajoz", "alcalá", "alcala", "león", "leon",
        "lérida", "lerida", "cádiz", "cadiz", "tarragona", "marbella", "jerez",
        "pamplona", "donostia", "san sebastián", "san sebastian", "tenerife",
        "las palmas", "alcobendas", "getafe", "móstoles", "mostoles"
    ]
    # Correcciones de ciudades mal transcritas por Whisper
    CORRECCIONES = {
        "vuelvo": "huelva", "huelba": "huelva", "welva": "huelva",
        "vallecas": "valladolid", "coruña": "a coruña",
    }
    for mal, bien in CORRECCIONES.items():
        if mal in t:
            t = t.replace(mal, bien)

    ciudad_encontrada = None
    for ciudad in CIUDADES_ES:
        if ciudad in t:
            ciudad_encontrada = ciudad
            break
    if ciudad_encontrada and any(p in t for p in [
        "temperatura", "tiempo", "grados", "clima", "llueve", "lluvia",
        "calor", "frío", "frio", "hace", "qué", "que", "cuánto", "cuanto"
    ]):
        return ("tiempo", ciudad_encontrada)
    m = re.search(r'(?:temperatura|tiempo|clima|grados|hace).{0,20}en\s+([a-záéíóúñ][a-záéíóúñ\s]{2,20})(?:\?|\.|$)', t)
    if m:
        return ("tiempo", m.group(1).strip())
    if any(p in t for p in ["qué tiempo", "que tiempo", "hace calor fuera", "va a llover"]):
        return ("tiempo", "Madrid")

    # Temperatura hardware
    if any(p in t for p in ["temperatura del procesador", "temperatura de la cpu", "temperatura cpu",
                              "temperatura del pc", "temperatura del ordenador", "a qué temperatura está",
                              "a que temperatura esta", "cuántos grados está", "cuantos grados esta",
                              "temperatura del hardware", "temperatura hardware", "temperatura de mis componentes"]):
        return ("sistema_temp",)
    if any(p in t for p in ["temperatura de la gpu", "temperatura gpu", "temperatura de la gráfica",
                              "temperatura grafica", "temperatura tarjeta"]):
        return ("sistema_gpu",)

    # Documentos Office — ANTES que crear_archivo genérico
    # Patrones: "crea un word llamado X", "hazme un excel llamado X", "crea un pdf llamado X"
    m = re.search(
        r'(?:crea?(?:r)?|hazme?|genera?(?:r)?|abre?|nuevo?)\s+'
        r'(?:un(?:a)?\s+)?'
        r'(word|documento|doc|docx|excel|hoja|xlsx|calc|powerpoint|presentaci[oó]n|pptx|impress|diapositivas|pdf|csv|tabla|writer)'
        r'(?:\s+(?:llamado?|con\s+nombre|que\s+se\s+llame?|titulado?|de\s+nombre))?\s+'
        r'(?:llamado?|con\s+nombre|titulado?)?\s*'
        r'"?([^"]{2,50})"?'
        r'(?:\s+(?:por\s+favor|porfavor|please))?$',
        t
    )
    if m:
        tipo_doc = m.group(1).strip()
        nombre_doc = m.group(2).strip()
        return ("crear_documento", tipo_doc, nombre_doc)

    # Sin nombre específico: "crea un word", "hazme un excel"
    m = re.search(
        r'(?:crea?(?:r)?|hazme?|genera?(?:r)?|nuevo?)\s+'
        r'(?:un(?:a)?\s+)?'
        r'(word|documento|doc|docx|excel|hoja|xlsx|calc|powerpoint|presentaci[oó]n|pptx|impress|diapositivas|pdf|csv|tabla|writer)'
        r'(?:\s+(?:por\s+favor|porfavor))?$',
        t
    )
    if m:
        tipo_doc = m.group(1).strip()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return ("crear_documento", tipo_doc, f"documento_{ts}")

    # Alarma a hora fija — ANTES que temporizador
    # Captura hora completa incluyendo "y media", "y 17", "menos cuarto", "de la noche"
    patron_hora = r'(\d{1,2}(?:[:.h]\d{0,2})?(?:\s+y\s+(?:media|cuarto|\d{1,2}))?(?:\s+menos\s+cuarto)?(?:\s+(?:de\s+la\s+)?(?:noche|mañana|madrugada|tarde))?)' 
    m = re.search(r'(?:pon|poner|activa|crea|programa|quiero|despiértame|despertarme|conme|ponme|ponme)\s+(?:una?\s+)?alarma\s+(?:a\s+las?\s+|para\s+las?\s+)?' + patron_hora, t)
    if m:
        return ("alarma", m.group(1).strip())
    m = re.search(r'alarma\s+(?:a\s+)?(?:las?\s+)?' + patron_hora, t)
    if m:
        return ("alarma", m.group(1).strip())
    m = re.search(r'(?:despiértame|despertarme|avísame)\s+(?:a\s+)?(?:las?\s+)?' + patron_hora, t)
    if m:
        return ("alarma", m.group(1).strip())

    # Temporizador
    m = re.search(r'(?:pon|poner|activa|crea|avísame|avisame).{0,20}(?:temporizador|alarma|timer|aviso).{0,20}(?:de\s+)?(\d+)\s*(minuto|segundo|hora)', t)
    if m:
        cantidad = int(m.group(1))
        unidad   = m.group(2)
        segundos = cantidad * (60 if "minuto" in unidad else 3600 if "hora" in unidad else 1)
        return ("temporizador", segundos, cantidad, unidad)

    # Volumen de una APP concreta: "baja el volumen de Discord al 30"
    # Mapa con variantes fonéticas que Whisper puede transcribir
    APPS_VARIANTES = {
        'discord': ['discord', 'discor', 'discordia', 'díscord'],
        'spotify': ['spotify', 'spotifai', 'espotify', 'spoti'],
        'chrome': ['chrome', 'crome', 'crom', 'gugel chrome'],
        'brave': ['brave', 'breve', 'brais', 'braif', 'breif', 'breiv', 'braive'],
        'firefox': ['firefox', 'fairfox', 'fire fox', 'faiyerfox'],
        'edge': ['edge', 'ets', 'eich'],
        'minecraft': ['minecraft', 'maincraft', 'maincraft'],
        'steam': ['steam', 'estim', 'estín'],
        'valorant': ['valorant', 'balorant', 'valorán'],
    }
    if 'volumen' in t:
        app_detectada = None
        for app_real, variantes in APPS_VARIANTES.items():
            if any(v in t for v in variantes):
                app_detectada = app_real
                break
        if app_detectada:
            app = app_detectada
            import re as _re_app
            # Porcentaje
            m_pct = _re_app.search(r'(\d{1,3})\s*(?:por\s+ciento|%|por\s+cien)?', t)
            if any(p in t for p in ['máximo', 'maximo']):
                return ("volumen_app", app, "maximo", None)
            if any(p in t for p in ['silencia', 'mute', 'quita el sonido']):
                return ("volumen_app", app, "silenciar", None)
            if any(p in t for p in ['activa', 'dessilencia', 'quita el mute']):
                return ("volumen_app", app, "activar", None)
            if m_pct and any(p in t for p in ['pon', 'pone', 'ajusta', 'sube', 'baja', 'al ', 'a ']):
                pct = int(m_pct.group(1))
                if 0 <= pct <= 100:
                    return ("volumen_app", app, "poner", pct)
            if any(p in t for p in ['sube', 'subir', 'más', 'mas']):
                return ("volumen_app", app, "subir", None)
            if any(p in t for p in ['baja', 'bajar', 'menos']):
                return ("volumen_app", app, "bajar", None)

    # Volumen a porcentaje exacto: "pon el volumen al 50", "volumen al 30 por ciento"
    import re as _re_vol
    m_vol = _re_vol.search(r'volumen\s+(?:al?\s+|a\s+)?(\d{1,3})\s*(?:por\s+ciento|%|por\s+cien)?', t)
    if m_vol and any(p in t for p in ['pon', 'pone', 'ajusta', 'sube', 'baja', 'al ', 'a ']):
        pct = int(m_vol.group(1))
        if 0 <= pct <= 100:
            return ("volumen", "poner", pct)
    if any(p in t for p in ["volumen al máximo", "volumen al maximo", "máximo volumen", "maximo volumen"]):
        return ("volumen", "maximo")

    # Volumen
    if any(p in t for p in ["sube el volumen", "subir volumen", "más volumen", "mas volumen", "volumen arriba"]):
        return ("volumen", "subir")
    if any(p in t for p in ["baja el volumen", "bajar volumen", "menos volumen", "volumen abajo"]):
        return ("volumen", "bajar")
    if any(p in t for p in ["silencia", "silenciar", "mute", "sin sonido", "quita el sonido"]):
        return ("volumen", "silenciar")
    if any(p in t for p in ["dessilencia", "activa el sonido", "quita el mute"]):
        return ("volumen", "activar")

    # Apagar / reiniciar
    if any(p in t for p in ["apaga el ordenador", "apagar el ordenador", "apaga el pc", "apagar pc"]):
        m = re.search(r'(\d+)\s*minuto', t)
        mins = int(m.group(1)) if m else 0
        return ("apagar", mins)
    if any(p in t for p in ["reinicia", "reiniciar", "restart"]):
        return ("reiniciar",)
    if any(p in t for p in ["cancela el apagado", "cancelar apagado", "no apagues"]):
        return ("cancelar_apagado",)

    # Captura
    if any(p in t for p in ["captura de pantalla", "screenshot", "captura pantalla", "haz una captura"]):
        return ("captura",)

    # Minimizar
    if any(p in t for p in ["minimiza todo", "minimizar todo", "muestra el escritorio", "oculta todo"]):
        return ("minimizar",)

    # Notas
    m = re.search(r'(?:anota|apunta|guarda una nota|escribe una nota)[:\s]+(.+)', t)
    if m:
        return ("guardar_nota", m.group(1).strip())
    if any(p in t for p in ["mis notas", "lee mis notas", "qué apunté", "que apunte", "mis apuntes"]):
        return ("leer_notas",)

    # Cerrar proceso (genérico) - EXCLUIR servidor/minecraft (los maneja el módulo MC)
    m = re.search(r'(?:cierra|cerrar|mata|kill)\s+(?:el\s+|la\s+)?(\w+)', t)
    if m and not any(p in t for p in ["ventana", "esto", "eso", "servidor", "minecraft", "mundo"]):
        return ("cerrar_proceso", m.group(1))

    # Ping
    if any(p in t for p in ["ping", "cómo está mi conexión", "como esta mi conexion", "velocidad internet", "latencia"]):
        return ("ping",)

    # Calculadora — si menciona mates avanzadas redirigir
    # Traducción explícita
    m = re.search(r'(?:traduce?|tradúceme?|cómo\s+se\s+dice|como\s+se\s+dice)\s+(.+?)\s+(?:al?|en)\s+([a-záéíóúñ]+)\s*(?:\?|$)', t)
    if m:
        return ("traducir", m.group(1).strip(), m.group(2).strip())
    m = re.search(r'(?:traduce?|tradúceme?)\s+(?:al?|en)\s+([a-záéíóúñ]+)[:\s]+(.+)', t)
    if m:
        return ("traducir", m.group(2).strip(), m.group(1).strip())
    # "cómo se dice X" sin idioma → inglés por defecto
    m = re.search(r'(?:cómo\s+se\s+dice|como\s+se\s+dice)\s+(.+?)\s*(?:\?|$)', t)
    if m:
        return ("traducir", m.group(1).strip(), "inglés")

    m = re.search(r'(?:cu[aá]n(?:to)?\s+es|cuanto es|calcula|cu[aá]nto\s+son|cuanto son)\s+(.+)', t)
    if m:
        expr = m.group(1).strip()
        expr_lower = expr.lower()
        MATES_KEYWORDS = ["integral", "derivada", "deriva", "límite", "limite",
                          "logaritmo", "seno", "coseno", "tangente", "raíz de",
                          "primitiva", "antiderivada"]
        OFFICE_KEYWORDS = ["word", "excel", "powerpoint"]
        if any(k in expr_lower for k in MATES_KEYWORDS) and not any(k in expr_lower for k in OFFICE_KEYWORDS):
            return ("mates_avanzadas", expr)

        es_media = any(p in expr_lower for p in ["la media", "el promedio", "media de", "promedio de", "media"])
        if es_media:
            numeros = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', expr)]
            if numeros:
                media = sum(numeros) / len(numeros)
                media = round(media, 4) if media != int(media) else int(media)
                return ("calcular_directo", str(media))
        resultado_hablado = calcular_expresion_hablada(expr)
        if resultado_hablado:
            return ("calcular_directo", resultado_hablado)
        return ("calcular", expr)

    # Aritmética directa sin verbo: "7 más 8 por 3", "raíz de 16"
    OPERADORES_HABLADOS = ["más", "menos", "por", "entre", "dividido", "al cuadrado",
                            "al cubo", "raíz de", "raiz de", "rais de", "rais",
                            "rise de", "rise", "race de", "race", "elevado a", "elevado al", "minus", "plus", "times", "divided by",
                            "seno de", "coseno de", "tangente de", "por ciento", "porciento"]
    PALABRAS_MATES_CHECK = ["deriva", "derivada", "diferencial", "integral", "integra",
                              "límite", "limite", "primitiva", "simplifica", "factori",
                              "resuelve", "ecuación", "ecuacion", "logaritmo", "neperiano"]
    # No calcular si es una expresión matemática simbólica
    if any(p in t for p in PALABRAS_MATES_CHECK):
        pass  # dejar que lo procese mates_avanzadas más adelante
    elif any(p in t for p in OPERADORES_HABLADOS) and re.search(r'\d', t):
        # Excluir frases que no son cálculos aunque contengan operadores
        FALSOS_POSITIVOS = ["más bien", "más o menos", "más tarde", "más o", "por favor",
                            "por cierto", "por eso", "por qué", "menos mal", "a menos que"]
        if any(fp in t for fp in FALSOS_POSITIVOS):
            pass
        elif not any(p in t for p in ["abre", "busca", "pon", "crea", "dime", "qué", "que",
                                      "cuándo", "cuando", "cómo", "como", "quién", "quien"]):
            resultado = calcular_expresion_hablada(t)
            if resultado:
                return ("calcular_directo", resultado)

    # Listar unidad
    m = re.search(r'(?:qué|que|cuales?|cuáles?).{0,20}(?:hay|tengo|tienes?).{0,10}(?:en\s+(?:el\s+)?(?:disco\s+)?|en\s+)([a-fA-F])[:\\/]?', t)
    if m:
        return ("listar_unidad", m.group(1))
    m = re.search(r'(?:archivos?|carpetas?|contenido).{0,15}(?:del?\s+)?(?:disco\s+)?([a-fA-F])[\:\\/]', t)
    if m:
        return ("listar_unidad", m.group(1))
    if re.search(r'(?:disco|unidad)\s+([a-fA-F])', t):
        m = re.search(r'(?:disco|unidad)\s+([a-fA-F])', t)
        if m and any(p in t for p in ["qué", "que", "hay", "tengo", "lista", "muestra", "archivos", "carpetas"]):
            return ("listar_unidad", m.group(1))

    # Batalla de rap
    if any(p in t for p in ["batalla de rap", "batalla rap", "rapea", "echa una barra",
                              "suéltame una barra", "sueltame una barra", "freestyle"]):
        return ("batalla_rap", texto)

    # Listar escritorio
    if any(p in t for p in ["qué tengo en el escritorio", "que tengo en el escritorio",
                              "programas del escritorio", "qué hay en el escritorio",
                              "que hay en el escritorio", "archivos del escritorio"]):
        return ("listar_escritorio",)

    # Spotify
    m = re.search(r'(?:reproduce?|pon|escucha?|busca?(?:r)?\s+en\s+spotify|abre?\s+spotify\s+y\s+pon)\s+(.+?)\s+(?:en\s+spotify|en\s+música)?$', t)
    if m and "spotify" in t:
        return ("spotify", m.group(1).strip())
    m = re.search(r'(?:pon|reproduce?)\s+(.+?)\s+en\s+spotify', t)
    if m:
        return ("spotify", m.group(1).strip())
    if "spotify" in t and any(p in t for p in ["pon ", "reproduce ", "escucha ", "busca "]):
        # Extraer nombre eliminando el verbo y "en spotify" del final
        nombre_raw = re.sub(r'^.*?(?:pon|reproduce|escucha|busca)\s+(?:a\s+)?', '', t).strip()
        nombre_raw = re.sub(r'\s+en\s+spotify.*', '', nombre_raw, flags=re.IGNORECASE).strip()
        if nombre_raw:
            return ("spotify", nombre_raw)

    # YouTube
    m = re.search(r'(?:busca?(?:r)?|pon|reproduce?|abre?|encuentra?)\s+(.+?)\s+en\s+(?:youtube|you\s*tube|yt|yutu|yutú|yutube)', t)
    if m:
        return ("youtube", m.group(1).strip())
    m = re.search(r'(?:busca?(?:r)?\s+en\s+(?:youtube|yt|yutu|yutube))\s+(.+)', t)
    if m:
        return ("youtube", m.group(1).strip())

    # Abrir app
    # NO abrir el launcher si habla del "servidor" o "mundo" (eso es el servidor MC)
    _es_servidor = ('servidor' in t or 'mundo' in t)
    if not _es_servidor:
        for exe, palabras in APPS.items():
            for p in palabras:
                if p in t and any(v in t for v in ["abre", "abrir", "lanza", "lanzar", "inicia", "iniciar", "pon", "pon en marcha"]):
                    return ("abrir_app", exe)

    # Abrir web
    for clave, (url, nombre) in sorted(WEBS.items(), key=lambda x: len(x[0]), reverse=True):
        if clave in t:
            if any(p in t for p in ["abre", "abrir", "entra", "ve a", "pon", "ir a", "mete"]):
                return ("abrir_web", url, nombre)

    # Crear código
    patrones_codigo = [
        r'(?:crea?(?:r)?|escribe?|genera?(?:r)?|haz(?:me)?)\s+(?:un(?:a)?\s+)?(?:programa|código|script|función|clase|archivo)\s+(?:en\s+)?(\w+)\s+(?:que|para|con|de)\s+(.+)',
        r'(?:crea?(?:r)?|escribe?|genera?(?:r)?|haz(?:me)?)\s+(?:un(?:a)?\s+)?(?:programa|código|script|función|clase|archivo)\s+(?:en\s+)?(\w+)[,\.\s]+(?:que|para|con|el cual)?\s*(.+)',
        r'(?:en|usando|con)\s+(python|php|javascript|js|html|css|powershell|bash)\s+(?:que|para|con)?\s*(.+)',
        r'(?:crea?(?:r)?|haz(?:me)?)\s+(?:un(?:a)?\s+)?(python|php|javascript|js|html|css|powershell)\s+(?:que|para|con)?\s*(.+)',
    ]
    for patron in patrones_codigo:
        m = re.search(patron, t)
        if m:
            lang = m.group(1).strip().lower()
            desc = m.group(2).strip()
            if lang in EXTENSIONES and len(desc) > 2:
                return ("crear_codigo", lang, desc)

    # Patrón simple: "crea un archivo en python"
    m = re.search(r'(?:crea?(?:r)?|abre?|hazme?)\s+(?:un(?:a)?\s+)?(?:archivo|fichero)?\s*(?:en\s+)?(python|php|javascript|js|html|css|powershell|bash)(?:\s|\.|$)', t)
    if m:
        lang = m.group(1).strip().lower()
        if lang in EXTENSIONES:
            return ("crear_archivo_vacio_vscode", lang)

    # Modificar archivo
    m = re.search(
        r'(?:modifica?(?:r)?|edita?(?:r)?|cambia?(?:r)?|actualiza?(?:r)?)\s+'
        r'(?:el\s+)?(?:archivo\s+)?([A-Za-z]:\\[\w\\\.\-]+|\S+\.\w+)\s+(?:y\s+|para\s+)?(.+)', t)
    if m:
        return ("modificar_archivo", m.group(1).strip(), m.group(2).strip())

    # Crear carpeta
    m = re.search(r'crea(?:r)?\s+(?:una\s+)?carpeta\s+(?:llamada\s+|con\s+nombre\s+)?["\']?([^"\']+?)["\']?(?:\s+en\s+(.+))?$', t)
    if m:
        return ("crear_carpeta", m.group(1).strip(), m.group(2).strip() if m.group(2) else ESCRITORIO)

    # Crear archivo vacío
    m = re.search(r'crea(?:r)?\s+(?:un\s+)?(?:archivo|fichero)\s+(?:llamado\s+|con\s+nombre\s+)?["\']?([^"\']+?)["\']?(?:\s+en\s+(.+))?$', t)
    if m:
        nombre = m.group(1).strip().lower()
        if not any(lang in nombre.split()[0] for lang in ["python","php","javascript","js","html","css","powershell","bash"]):
            return ("crear_archivo", m.group(1).strip(), m.group(2).strip() if m.group(2) else ESCRITORIO)

    # Fútbol con API-Football (datos reales)
    # NO activar si es una orden de crear evento/recordatorio
    _es_evento_cal = any(p in t for p in ['crea el evento', 'crea un evento', 'crear evento',
                                          'pon el evento', 'pon un evento', 'añade el evento',
                                          'añade un evento', 'agéndame', 'recuérdame', 'recuerdame',
                                          'apunta el evento', 'créame un evento', 'crea el', 'crea un evento'])
    if FUTBOL_OK and not _es_evento_cal:
        f = _futbol.detectar_futbol(t)
        if f:
            if f[0] == 'equipo':
                return ("futbol_equipo", f[1], f[2])
            else:
                return ("futbol_lista", f[1])


    # Fútbol — NO activar si es una orden de crear evento/recordatorio/calendario
    _orden_evento = any(p in t for p in ['crea el evento', 'crea un evento', 'crear evento',
                                         'pon el evento', 'pon un evento', 'añade el evento',
                                         'añade un evento', 'agéndame', 'recuérdame', 'recuerdame',
                                         'apunta el evento', 'créame un evento'])
    if not _orden_evento and any(p in t for p in ["resultado", "resultados", "marcador", "partido",
                              "futbol", "fútbol",
                              "liga", "champions", "copa del rey", "real madrid", "barcelona",
                              "atletico", "atlético", "sevilla", "valencia", "betis", "villarreal"]):
        return ("buscar_futbol", texto)

    # Info sistema
    if any(p in t for p in ["mis componentes", "componentes del pc", "especificaciones", "specs", "hardware"]):
        return ("sistema_todo",)
    if any(p in t for p in ["procesador", "cpu"]):
        return ("sistema_cpu",)
    if any(p in t for p in ["grafica", "gráfica", "gpu", "tarjeta grafica", "tarjeta gráfica"]):
        return ("sistema_gpu",)
    if any(p in t for p in ["temperatura", "temperaturas", "calor", "caliente"]):
        return ("sistema_temp",)
    if any(p in t for p in ["cuanta ram", "cuánta ram", "memoria ram", "ram libre", "ram usada"]):
        return ("sistema_ram",)
    if any(p in t for p in ["disco", "almacenamiento", "espacio", "ssd", "hdd"]):
        return ("sistema_disco",)
    if any(p in t for p in ["procesos", "proceso", "programas abiertos", "que esta corriendo"]):
        return ("sistema_procesos",)
    if any(p in t for p in ["mi ip", "mi red", "ip local", "conexion de red", "wifi"]):
        return ("sistema_red",)
    if any(p in t for p in ["mi ordenador", "mi pc", "información del sistema", "sistema operativo"]):
        return ("sistema_todo",)



    # Traducción / idiomas / matemáticas → conversación directa con Ollama, no búsqueda
    if any(p in t for p in ["cómo se dice", "como se dice", "cómo se traduce", "como se traduce",
                              "qué significa", "que significa", "tradúceme", "traduceme",
                              "en inglés", "en francés", "en alemán", "en italiano", "en portugués"]):
        return None  # va a Ollama directamente

    # Matemáticas con variables complejas sin verbo claro → Ollama directamente
    # (NO incluir resuelve/ecuacion/despeja que son manejados por SymPy)
    if any(p in t for p in ["cuánto vale", "cuanto vale", "cuánto es si", "cuanto es si",
                              "polinomio", "cuánto da", "cuanto da"]) and        any(c in t for c in ["x", "y", "z", "cuadrado", "elevado"]):
        return None

    # Calendario / eventos
    # Listar eventos del día (antes que crear)
    if CAL_OK and any(p in t for p in ['qué eventos', 'que eventos', 'eventos tengo',
                                       'eventos hoy', 'eventos de hoy', 'eventos para hoy',
                                       'eventos mañana', 'eventos de mañana', 'mi agenda',
                                       'qué tengo hoy', 'que tengo hoy', 'tengo planes']):
        dia = 'mañana' if 'mañana' in t or 'manana' in t else 'hoy'
        return ("listar_eventos", dia)

    if CAL_OK:
        ev = _cal.detectar_evento(t)
        if ev:
            return ("calendario", ev[0], ev[1])

    # Memoria persistente
    if MEM_OK:
        mem_accion = _mem.detectar_memoria(t)
        if mem_accion:
            return ("memoria",) + mem_accion

    # Corrección / verificación de respuesta anterior
    PALABRAS_CORRECCION = [
        'estás seguro', 'estas seguro', 'seguro de eso', 'estás segura',
        'no es correcto', 'eso no es correcto', 'eso es incorrecto',
        'corrígete', 'corrigete', 'vuelve a buscar', 'busca de nuevo',
        'busca otra vez', 'verifica', 'compruébalo', 'comprúebalo',
        'no me convence', 'estoy seguro de que', 'revísalo', 'revisalo',
    ]
    if any(p in t for p in PALABRAS_CORRECCION) and _ultima_pregunta:
        return ("verificar", _ultima_pregunta)

    # Backup Minecraft
    if MC_OK:
        mc_accion = _mc.detectar_backup(t)
        if mc_accion:
            return ("minecraft_backup", mc_accion)

    # Análisis de archivos / código
    if ARCHIVOS_OK:
        a = _archivos.detectar_archivo(t)
        if a:
            return ("archivo",) + a

    # Análisis de imágenes (LLaVA)
    if VISION_OK:
        v = _vision.detectar_vision(t)
        if v:
            return ("vision", v[0], v[1])

    # Videojuegos
    if JUEGOS_OK:
        jq = _juegos.detectar_consulta_juego(t)
        if jq:
            return ("juego",) + jq

    # Correo Gmail
    if CORREO_OK:
        c = _correo.detectar_correo(t)
        if c:
            return ("correo",) + c

    # Preguntas personales → consultar memoria
    if MEM_OK:
        PREGUNTAS_FIJAS = [
            'cómo me llamo', 'como me llamo', 'cuál es mi nombre', 'cual es mi nombre',
            'quién soy', 'quien soy', 'qué recuerdas', 'que recuerdas',
            'qué sabes de mí', 'que sabes de mi', 'qué tienes guardado',
            'cuál es mi', 'cual es mi', 'cómo se llama mi', 'como se llama mi',
            'dónde vivo', 'donde vivo', 'tengo coche', 'tengo novia',
        ]
        if any(p in t for p in PREGUNTAS_FIJAS):
            return ("memoria", "consultar", t)
        # Detectar preguntas sobre claves guardadas en memoria
        # Excluir si la pregunta es sobre correo, notificaciones, calendario, etc.
        EXCLUIR_MEM = ['correo', 'email', 'e-mail', 'gmail', 'mail', 'notificac',
                       'evento', 'calendario', 'bus', 'whatsapp', 'wasap', 'llama']
        if not any(ex in t for ex in EXCLUIR_MEM):
            try:
                mem_data = _mem._cargar()
                for clave in mem_data:
                    palabras_clave = clave.lower().replace('nombre de ', '').replace('nombre ', '').split()
                    if any(palabra in t for palabra in palabras_clave if len(palabra) > 3):
                        if any(p in t for p in ['cuál', 'cual', 'cómo', 'como', 'qué', 'que',
                                                 'quién', 'quien', 'dónde', 'donde', 'tengo',
                                                 'tienes', 'mi ', 'tu ', 'es ']):
                            return ("memoria", "consultar", t)
            except:
                pass

    # Notificaciones del móvil
    if NOTI_OK and _noti.detectar_notificaciones(t):
        return ("notificaciones",)

    # Llamadas por Phone Link
    if PHONE_LINK_OK:
        llamada = phone_link.detectar_llamada(texto)
        if llamada:
            return ("phone_llamada",) + llamada

    # WhatsApp
    if WHATSAPP_OK:
        wa = _wa.detectar_whatsapp(texto)
        if wa:
            return ("whatsapp", wa[0], wa[1])

    # Matemáticas avanzadas con SymPy
    # Excluir si menciona documentos Office
    PALABRAS_OFFICE = ["word", "excel", "powerpoint", "power point", "hoja de calculo",
                       "documento", "presentacion", "presentación"]
    PALABRAS_MATES = ["deriva", "derivada", "diferencial", "integral", "integra", "primitiva",
                      "límite", "limite", "lim", "resuelve", "soluciona", "ecuación", "ecuacion",
                      "simplifica", "factori", "logaritmo", "neperiano", "seno", "coseno",
                      "tangente", "triple integral", "doble integral"]
    if any(p in t for p in PALABRAS_MATES) and not any(p in t for p in PALABRAS_OFFICE) and not any(p in t for p in ['cómo se dice','como se dice']):
        return ("mates_avanzadas", texto)

    # Buscar en internet
    if any(p in t for p in ["busca", "buscar", "qué es", "que es", "quién es", "quien es",
                              "como funciona", "cuánto", "dónde", "donde está", "información sobre"]):
        return ("buscar_web", texto)

    return None


# ─── EJECUTAR ACCIÓN ────────────────────
def controlar_volumen(accion_vol, valor=None):
    """Controla el volumen del sistema. accion_vol: subir/bajar/silenciar/activar/poner."""
    # Intentar con pycaw para control preciso
    try:
        import comtypes
        # Inicializar COM en este hilo (necesario en hilos secundarios de JARVIS)
        try:
            comtypes.CoInitialize()
        except:
            pass
        from pycaw.utils import AudioUtilities as _AU
        vol = _AU.GetSpeakers().EndpointVolume

        if accion_vol == 'poner' and valor is not None:
            nivel = max(0, min(100, valor)) / 100.0
            vol.SetMute(0, None)  # quitar mute al ajustar volumen
            vol.SetMasterVolumeLevelScalar(nivel, None)
            return f"Volumen al {valor} por ciento."
        elif accion_vol == 'subir':
            vol.SetMute(0, None)  # quitar mute al subir
            actual = vol.GetMasterVolumeLevelScalar()
            nuevo = min(1.0, actual + 0.1)
            vol.SetMasterVolumeLevelScalar(nuevo, None)
            return f"Volumen al {int(nuevo*100)} por ciento."
        elif accion_vol == 'bajar':
            vol.SetMute(0, None)  # quitar mute al bajar
            actual = vol.GetMasterVolumeLevelScalar()
            nuevo = max(0.0, actual - 0.1)
            vol.SetMasterVolumeLevelScalar(nuevo, None)
            return f"Volumen al {int(nuevo*100)} por ciento."
        elif accion_vol == 'silenciar':
            vol.SetMute(1, None)
            return "Volumen silenciado."
        elif accion_vol == 'activar':
            vol.SetMute(0, None)
            return "Volumen activado."
        elif accion_vol == 'maximo':
            vol.SetMute(0, None)  # quitar mute al poner máximo
            vol.SetMasterVolumeLevelScalar(1.0, None)
            return "Volumen al máximo."
    except ImportError:
        pass  # pycaw no instalado, usar fallback
    except Exception:
        pass

    # Fallback con SendKeys
    try:
        import subprocess
        acciones = {
            'subir': 'for($i=0;$i -lt 5;$i++){$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]175)}',
            'bajar': 'for($i=0;$i -lt 5;$i++){$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]174)}',
            'silenciar': '$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]173)',
            'activar': '$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]173)',
            'maximo': 'for($i=0;$i -lt 50;$i++){$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys([char]175)}',
        }
        cmd = acciones.get(accion_vol, acciones['subir'])
        subprocess.run(['powershell', '-c', cmd], creationflags=0x08000000)
        return f"Volumen: {accion_vol}."
    except Exception as e:
        return f"Error de volumen: {e}"


def controlar_volumen_app(nombre_app, accion_vol, valor=None):
    """Controla el volumen de una app concreta (Discord, Spotify, Chrome...)."""
    try:
        import comtypes
        try:
            comtypes.CoInitialize()
        except:
            pass
        from pycaw.pycaw import AudioUtilities

        sesiones = AudioUtilities.GetAllSessions()
        nombre_lower = nombre_app.lower()

        # Mapa de nombres hablados a procesos
        ALIAS = {
            'discord': 'discord', 'spotify': 'spotify', 'chrome': 'chrome',
            'brave': 'brave', 'firefox': 'firefox', 'edge': 'msedge',
            'navegador': 'brave', 'youtube': 'brave', 'juego': None,
            'minecraft': 'javaw', 'steam': 'steam', 'valorant': 'valorant',
        }
        proceso = ALIAS.get(nombre_lower, nombre_lower)

        encontrada = None
        for s in sesiones:
            if s.Process and s.Process.name():
                pname = s.Process.name().lower()
                if proceso and proceso in pname:
                    encontrada = s
                    break

        if not encontrada:
            return f"No encontré {nombre_app} abierto reproduciendo sonido."

        vol = encontrada.SimpleAudioVolume

        if accion_vol == 'poner' and valor is not None:
            nivel = max(0, min(100, valor)) / 100.0
            vol.SetMasterVolume(nivel, None)
            return f"Volumen de {nombre_app} al {valor} por ciento."
        elif accion_vol == 'subir':
            actual = vol.GetMasterVolume()
            nuevo = min(1.0, actual + 0.15)
            vol.SetMasterVolume(nuevo, None)
            return f"Volumen de {nombre_app} al {int(nuevo*100)} por ciento."
        elif accion_vol == 'bajar':
            actual = vol.GetMasterVolume()
            nuevo = max(0.0, actual - 0.15)
            vol.SetMasterVolume(nuevo, None)
            return f"Volumen de {nombre_app} al {int(nuevo*100)} por ciento."
        elif accion_vol == 'silenciar':
            vol.SetMute(1, None)
            return f"{nombre_app} silenciado."
        elif accion_vol == 'activar':
            vol.SetMute(0, None)
            return f"{nombre_app} activado."
        elif accion_vol == 'maximo':
            vol.SetMasterVolume(1.0, None)
            return f"Volumen de {nombre_app} al máximo."

        return f"No entendí qué hacer con el volumen de {nombre_app}."

    except ImportError:
        return "Necesito pycaw. Instala: pip install pycaw"
    except Exception as e:
        return f"Error con el volumen de {nombre_app}: {e}"


def apagar_pc(minutos=0):
    """Apaga el PC."""
    try:
        import subprocess
        if minutos > 0:
            subprocess.run(['shutdown', '/s', '/t', str(minutos * 60)], creationflags=0x08000000)
            return f"El PC se apagará en {minutos} minutos."
        subprocess.run(['shutdown', '/s', '/t', '10'], creationflags=0x08000000)
        return "El PC se apagará en 10 segundos."
    except Exception as e:
        return f"Error al apagar: {e}"


def reiniciar_pc():
    """Reinicia el PC."""
    try:
        import subprocess
        subprocess.run(['shutdown', '/r', '/t', '10'], creationflags=0x08000000)
        return "El PC se reiniciará en 10 segundos."
    except Exception as e:
        return f"Error al reiniciar: {e}"


def cancelar_apagado():
    """Cancela el apagado programado."""
    try:
        import subprocess
        subprocess.run(['shutdown', '/a'], creationflags=0x08000000)
        return "Apagado cancelado."
    except Exception as e:
        return f"Error: {e}"


def guardar_nota(texto):
    """Guarda una nota de voz."""
    try:
        import datetime, os
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notas.txt")
        ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(ruta, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {texto}\n")
        return "Nota guardada."
    except Exception as e:
        return f"Error al guardar nota: {e}"


def leer_notas():
    """Lee las notas guardadas."""
    try:
        import os
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notas.txt")
        if not os.path.isfile(ruta):
            return "No hay notas guardadas."
        with open(ruta, 'r', encoding='utf-8') as f:
            notas = f.read().strip()
        if not notas:
            return "No hay notas guardadas."
        lineas = notas.split('\n')
        ultimas = lineas[-3:]
        return "Últimas notas: " + ". ".join(ultimas)
    except Exception as e:
        return f"Error al leer notas: {e}"


def listar_escritorio():
    """Lista archivos del escritorio."""
    try:
        import os
        archivos = os.listdir(ESCRITORIO)
        if not archivos:
            return "El escritorio está vacío."
        return f"En el escritorio: {', '.join(archivos[:10])}."
    except Exception as e:
        return f"Error: {e}"


def listar_unidad(letra):
    """Lista archivos de una unidad."""
    try:
        import os
        ruta = f"{letra.upper()}:\\"
        archivos = os.listdir(ruta)
        return f"En {letra.upper()}: {', '.join(archivos[:10])}."
    except Exception as e:
        return f"Error: {e}"


def get_ping():
    """Alias para ping_red."""
    return ping_red()


def batalla_rap(texto):
    """Genera una batalla de rap con Ollama."""
    return preguntar_ollama(
        f"Eres un rapero español agresivo y gracioso. Suéltame 4 barras de freestyle sobre: {texto}. "
        f"Solo las barras, sin explicaciones."
    )


def cerrar_proceso(nombre):
    """Cierra un proceso por nombre."""
    try:
        import subprocess
        result = subprocess.run(['taskkill', '/F', '/IM', f'{nombre}.exe'],
                               capture_output=True, text=True, creationflags=0x08000000)
        if result.returncode == 0:
            return f"{nombre} cerrado."
        # Intentar sin .exe
        result2 = subprocess.run(['taskkill', '/F', '/IM', nombre],
                                capture_output=True, text=True, creationflags=0x08000000)
        if result2.returncode == 0:
            return f"{nombre} cerrado."
        return f"No encontré el proceso {nombre}."
    except Exception as e:
        return f"Error al cerrar {nombre}: {e}"


def ping_red():
    """Comprueba la conexión a internet."""
    try:
        import subprocess
        result = subprocess.run(['ping', '-n', '1', '8.8.8.8'],
                               capture_output=True, text=True, creationflags=0x08000000, timeout=5)
        if result.returncode == 0:
            return "Conexión a internet: OK."
        return "Sin conexión a internet."
    except:
        return "No pude comprobar la conexión."


def captura_pantalla():
    """Hace una captura de pantalla."""
    try:
        import datetime, subprocess, os
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.join(ESCRITORIO, f"captura_{ts}.png")
        subprocess.run(['powershell', '-c',
            f'Add-Type -AssemblyName System.Windows.Forms; '
            f'[System.Windows.Forms.Screen]::PrimaryScreen | Out-Null; '
            f'$b = [System.Drawing.Bitmap]::new([System.Windows.Forms.SystemInformation]::PrimaryMonitorSize.Width, '
            f'[System.Windows.Forms.SystemInformation]::PrimaryMonitorSize.Height); '
            f'$g = [System.Drawing.Graphics]::FromImage($b); '
            f'$g.CopyFromScreen(0,0,0,0,$b.Size); '
            f'$b.Save("{ruta}")'],
            creationflags=0x08000000)
        return f"Captura guardada en el escritorio."
    except Exception as e:
        return f"No pude hacer la captura: {e}"


def minimizar_todo():
    """Minimiza todas las ventanas."""
    try:
        import subprocess
        subprocess.run(['powershell', '-c',
            '(New-Object -ComObject Shell.Application).MinimizeAll()'],
            creationflags=0x08000000)
        return "Ventanas minimizadas."
    except:
        return "No pude minimizar las ventanas."


def abrir_web(url, nombre):
    """Abre una URL en Brave."""
    import subprocess, os
    BRAVE = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
    if os.path.isfile(BRAVE):
        subprocess.Popen([BRAVE, url])
    else:
        import webbrowser
        webbrowser.open(url)
    return f"Abriendo {nombre}."


def poner_alarma(hora_str, log_fn):
    """Pone una alarma a una hora específica."""
    import datetime as _dt
    try:
        texto_hora = hora_str.lower().strip()
        minutos_extra = 0
        if "y media" in texto_hora:
            minutos_extra = 30
            texto_hora = re.sub(r'y\s+media', '', texto_hora)
        elif "y cuarto" in texto_hora:
            minutos_extra = 15
            texto_hora = re.sub(r'y\s+cuarto', '', texto_hora)
        elif "menos cuarto" in texto_hora:
            minutos_extra = -15
            texto_hora = re.sub(r'menos\s+cuarto', '', texto_hora)

        es_tarde = any(p in texto_hora for p in ["tarde", "pm"])
        es_noche = any(p in texto_hora for p in ["noche", "madrugada"])

        partes = re.findall(r'\d+', texto_hora)
        if len(partes) >= 2:
            h, m_min = int(partes[0]), int(partes[1])
        elif len(partes) == 1:
            h, m_min = int(partes[0]), 0
        else:
            return "No entendí la hora de la alarma."

        m_min += minutos_extra
        if m_min >= 60:
            h += 1; m_min -= 60
        elif m_min < 0:
            h -= 1; m_min += 60

        if es_tarde and h < 12:
            h += 12  # 3 de la tarde -> 15:00
        elif es_noche:
            if h == 12:
                h = 0   # 12 de la noche = medianoche
            elif h < 12:
                h += 12  # 10 de la noche -> 22:00
        h = h % 24

        ahora = _dt.datetime.now()
        objetivo = ahora.replace(hour=h, minute=m_min, second=0, microsecond=0)
        if objetivo <= ahora:
            objetivo += _dt.timedelta(days=1)

        segundos = (objetivo - ahora).total_seconds()
        hora_fmt = objetivo.strftime("%H:%M")

        def _alarma():
            import time as _time
            _time.sleep(segundos)
            msg = f"{NOMBRE_USUARIO}, son las {hora_fmt}. Suena tu alarma."
            log_fn(msg, "jarvis")
            hablar(msg)
            try:
                import winsound
                for _ in range(5):
                    winsound.Beep(1000, 600)
                    _time.sleep(0.2)
            except:
                pass

        threading.Thread(target=_alarma, daemon=True).start()
        return f"Alarma puesta para las {hora_fmt}."
    except Exception as e:
        return f"No pude poner la alarma: {e}"


def poner_temporizador(segundos, log_fn, callback=None):
    """Pone un temporizador."""
    import time as _time
    def _timer():
        _time.sleep(segundos)
        mins = segundos // 60
        secs = segundos % 60
        if mins > 0:
            msg = f"{NOMBRE_USUARIO}, el temporizador de {mins} minuto{'s' if mins>1 else ''} ha terminado."
        else:
            msg = f"{NOMBRE_USUARIO}, el temporizador de {secs} segundos ha terminado."
        log_fn(msg, "jarvis")
        hablar(msg)
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(800, 400)
                _time.sleep(0.3)
        except:
            pass
    threading.Thread(target=_timer, daemon=True).start()


def buscar_en_youtube(query):
    """Busca en YouTube en Brave."""
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    import subprocess
    BRAVE = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
    import os
    if os.path.isfile(BRAVE):
        subprocess.Popen([BRAVE, url])
    else:
        import webbrowser
        webbrowser.open(url)
    return f"Buscando {query} en YouTube."


def reproducir_en_spotify(query):
    """Busca en Spotify en Brave."""
    url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}"
    import subprocess
    BRAVE = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
    import os
    if os.path.isfile(BRAVE):
        subprocess.Popen([BRAVE, url])
    else:
        import webbrowser
        webbrowser.open(url)
    return f"Buscando {query} en Spotify."


def ejecutar_accion(accion, log_fn):
    global _borrado_pendiente, _evento_pendiente
    import subprocess as sp
    tipo = accion[0]

    if tipo == "cerrar_jarvis":
        # Despedida y cierre del programa
        import threading as _th
        def _cerrar():
            import time as _t
            _t.sleep(2)  # dar tiempo a que hable
            import os as _os
            _os._exit(0)
        _th.Thread(target=_cerrar, daemon=True).start()
        return f"Hasta luego, {NOMBRE_USUARIO}. Cerrando sistema."

    elif tipo == "parsec":
        if not PARSEC_OK:
            return "Módulo de Parsec no disponible."
        sub = accion[1]
        if sub == 'abrir':
            return _parsec.abrir_parsec()
        elif sub == 'compartir':
            log_fn("Abriendo Parsec y compartiendo...", "accion")
            return _parsec.compartir_parsec(log_fn)
        elif sub == 'dejar':
            log_fn("Dejando de compartir en Parsec...", "accion")
            return _parsec.dejar_de_compartir(log_fn)

    elif tipo == "procesos":
        if not PROCESOS_OK:
            return "Módulo de procesos no disponible."
        log_fn("Mirando procesos abiertos...", "accion")
        return _procesos.procesos_abiertos(accion[1])

    elif tipo == "confirmar_borrado":
        if _borrado_pendiente is None:
            return "No hay nada pendiente de borrar."
        archivo, carpeta = _borrado_pendiente
        _borrado_pendiente = None
        log_fn(f"Moviendo {archivo} a la papelera...", "accion")
        return _explorador.borrar_archivo(archivo, carpeta)

    elif tipo == "borrar_evento":
        if not CAL_OK:
            return "Módulo de calendario no disponible."
        nombre = accion[1]
        log_fn(f"Buscando evento {nombre}...", "accion")
        encontrado = _cal.buscar_evento_por_nombre(nombre)
        if not encontrado:
            return f"No encontré ningún evento llamado '{nombre}' en los próximos días."
        ev_id, titulo, fecha_txt = encontrado
        _evento_pendiente = (ev_id, titulo)
        return f"¿Seguro que quieres borrar el evento '{titulo}' del {fecha_txt}? Di 'sí, confirma' para borrarlo."

    elif tipo == "confirmar_borrado_evento":
        if _evento_pendiente is None:
            return "No hay ningún evento pendiente de borrar."
        ev_id, titulo = _evento_pendiente
        _evento_pendiente = None
        log_fn(f"Borrando evento {titulo}...", "accion")
        if _cal.borrar_evento(ev_id):
            return f"He borrado el evento '{titulo}'."
        return f"No pude borrar el evento '{titulo}'."

    elif tipo == "cancelar_borrado_evento":
        _evento_pendiente = None
        return "Vale, no borro el evento."

    elif tipo == "cancelar_borrado":
        _borrado_pendiente = None
        return "Vale, no borro nada."

    elif tipo == "explorador":
        if not EXPLORADOR_OK:
            return "Módulo de explorador no disponible."
        sub = accion[1]
        if sub == 'listar':
            log_fn(f"Explorando carpeta {accion[2]}...", "accion")
            return _explorador.listar_carpeta(accion[2])
        elif sub == 'leer':
            log_fn(f"Leyendo {accion[2]}...", "accion")
            return _explorador.leer_archivo_de_carpeta(accion[2], accion[3])
        elif sub == 'buscar_archivo':
            log_fn(f"Buscando {accion[2]} en el PC...", "accion")
            return _explorador.buscar_archivo_global(accion[2])
        elif sub == 'borrar':
            # Guardar como pendiente y pedir confirmación
            archivo = accion[2]
            carpeta = accion[3]
            _borrado_pendiente = (archivo, carpeta)
            destino = f" de la carpeta {carpeta}" if carpeta else ""
            return f"¿Seguro que quieres mover {archivo}{destino} a la papelera? Di 'sí, confirma' para hacerlo."

    elif tipo == "captura_telegram":
        # Captura de pantalla y envío por Telegram
        if not (VISION_OK and TELEGRAM_OK):
            return "Necesito los módulos de visión y Telegram para esto."
        log_fn("Haciendo captura de pantalla...", "accion")
        ruta = _vision.capturar_pantalla()
        if ruta and _telegram.enviar_foto(ruta, "Captura de tu pantalla"):
            return "Captura enviada a Telegram."
        return "No pude hacer o enviar la captura."

    elif tipo == "webcam_foto":
        if not WEBCAM_OK:
            return "Módulo de webcam no disponible."
        log_fn("Tomando foto con la webcam...", "accion")
        ruta, msg = _webcam.hacer_foto()
        if ruta:
            if TELEGRAM_OK:
                _telegram.enviar_foto(ruta, "Foto de la webcam")
                return "Foto tomada y enviada a Telegram."
            return f"Foto guardada en {ruta}."
        return msg

    elif tipo == "hora_fecha":
        ahora = datetime.datetime.now()
        DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
                 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        dia_sem = DIAS[ahora.weekday()]
        mes = MESES[ahora.month - 1]
        return f"Son las {ahora.strftime('%H:%M')} del {dia_sem} {ahora.day} de {mes} de {ahora.year}."

    elif tipo == "tiempo":
        return get_tiempo(accion[1])

    elif tipo == "alarma":
        return poner_alarma(accion[1], log_fn)

    elif tipo == "temporizador":
        _, segundos, cantidad, unidad = accion
        poner_temporizador(segundos, log_fn, None)
        return f"Temporizador de {cantidad} {unidad}{'s' if cantidad>1 else ''} puesto."

    elif tipo == "volumen":
        valor = accion[2] if len(accion) > 2 else None
        return controlar_volumen(accion[1], valor)

    elif tipo == "volumen_app":
        # accion = ("volumen_app", nombre_app, accion_vol, valor)
        return controlar_volumen_app(accion[1], accion[2], accion[3])

    elif tipo == "apagar":
        return apagar_pc(accion[1])

    elif tipo == "reiniciar":
        return reiniciar_pc()

    elif tipo == "cancelar_apagado":
        return cancelar_apagado()

    elif tipo == "captura":
        return captura_pantalla()

    elif tipo == "minimizar":
        return minimizar_todo()

    elif tipo == "guardar_nota":
        return guardar_nota(accion[1])

    elif tipo == "leer_notas":
        return leer_notas()

    elif tipo == "cerrar_proceso":
        return cerrar_proceso(accion[1])

    elif tipo == "ping":
        return get_ping()

    elif tipo == "calcular":
        return calcular(accion[1])

    elif tipo == "calcular_directo":
        _set_ultimo(accion[1])
        return accion[1]

    elif tipo == "listar_escritorio":
        return listar_escritorio()

    elif tipo == "listar_unidad":
        return listar_unidad(accion[1])

    elif tipo == "batalla_rap":
        return batalla_rap(accion[1])

    elif tipo == "spotify":
        return reproducir_en_spotify(accion[1])

    elif tipo == "youtube":
        return buscar_en_youtube(accion[1])

    elif tipo == "abrir_web":
        return abrir_web(accion[1], accion[2])

    elif tipo == "crear_documento":
        tipo_doc, nombre_doc = accion[1], accion[2]
        log_fn(f"Creando documento {tipo_doc}: {nombre_doc}...", "accion")
        return crear_documento_office(tipo_doc, nombre_doc)

    elif tipo == "abrir_app":
        exe = accion[1]
        try:
            if exe.endswith((".lnk", ".url")):
                sp.Popen(f'start "" "{exe}"', shell=True)
            elif os.path.isfile(exe):
                sp.Popen([exe], shell=False)
            else:
                sp.Popen(exe, shell=True)
            nombre = os.path.splitext(os.path.basename(exe))[0] if ("/" in exe or "\\" in exe) else exe
            return f"Abriendo {nombre}."
        except Exception as e:
            return f"No pude abrir {exe}: {e}"

    elif tipo == "crear_carpeta":
        nombre, lugar = accion[1], accion[2]
        lugar = lugar.replace("el escritorio", ESCRITORIO).replace("escritorio", ESCRITORIO)
        ruta = os.path.join(lugar, nombre)
        try:
            os.makedirs(ruta, exist_ok=True)
            return f"Carpeta '{nombre}' creada."
        except Exception as e:
            return f"No pude crear la carpeta: {e}"

    elif tipo == "crear_archivo":
        nombre, lugar = accion[1], accion[2]
        lugar = lugar.replace("el escritorio", ESCRITORIO).replace("escritorio", ESCRITORIO)
        ruta = os.path.join(lugar, nombre)
        try:
            open(ruta, 'w').close()
            return f"Archivo '{nombre}' creado."
        except Exception as e:
            return f"No pude crear el archivo: {e}"

    elif tipo == "crear_archivo_vacio_vscode":
        lang = accion[1]
        ext = EXTENSIONES.get(lang, ".txt")
        ts = datetime.datetime.now().strftime("%H%M%S")
        nombre_archivo = f"nuevo_{lang}_{ts}{ext}"
        ruta = os.path.join(ESCRITORIO, nombre_archivo)
        try:
            open(ruta, 'w').close()
            vscode_paths = [
                os.path.join(os.path.expanduser("~"), r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
                r"C:\Program Files\Microsoft VS Code\Code.exe",
            ]
            vscode_exe = next((v for v in vscode_paths if os.path.isfile(v)), None)
            if vscode_exe:
                sp.Popen([vscode_exe, ruta])
            else:
                sp.Popen(f'code "{ruta}"', shell=True)
            return f"Archivo {lang} creado y abierto en VSCode."
        except Exception as e:
            return f"No pude crear el archivo: {e}"

    elif tipo == "crear_codigo":
        lenguaje, descripcion = accion[1], accion[2]
        ext = EXTENSIONES.get(lenguaje, ".txt")
        ts = datetime.datetime.now().strftime("%H%M%S")
        nombre_archivo = f"jarvis_{lenguaje}_{ts}{ext}"
        ruta = os.path.join(ESCRITORIO, nombre_archivo)
        log_fn(f"Generando código {lenguaje}...", "accion")
        codigo = generar_codigo(descripcion, lenguaje)
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(codigo)
        except Exception as e:
            return f"No pude guardar el código: {e}"
        vscode_paths = [
            os.path.join(os.path.expanduser("~"), r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]
        vscode_exe = next((v for v in vscode_paths if os.path.isfile(v)), None)
        if vscode_exe:
            sp.Popen([vscode_exe, ruta])
        else:
            sp.Popen(f'code "{ruta}"', shell=True)
        time.sleep(1)
        l = lenguaje.lower()
        python_exe = sys.executable
        if not os.path.isfile(python_exe):
            python_exe = "python"
        if l in ("python", "py"):
            sp.Popen(f'start "JARVIS — Python" cmd /k "{python_exe}" "{ruta}"', shell=True)
        elif l in ("javascript", "js"):
            sp.Popen(f'start "JARVIS — Node" cmd /k node "{ruta}"', shell=True)
        elif l in ("php",):
            sp.Popen(f'start "JARVIS — PHP" cmd /k php "{ruta}"', shell=True)
        elif l in ("powershell", "ps1"):
            sp.Popen(['powershell', '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', ruta])
        elif l in ("html", "css"):
            sp.Popen(f'start "" "{ruta}"', shell=True)
        return f"Código {lenguaje} creado, abierto en VSCode y ejecutándose."

    elif tipo == "modificar_archivo":
        ruta, instruccion = accion[1], accion[2]
        if not os.path.exists(ruta):
            return f"No encontré el archivo {ruta}."
        log_fn(f"Modificando {os.path.basename(ruta)}...", "accion")
        nuevo, error = modificar_archivo_con_ia(ruta, instruccion)
        if error:
            return error
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(nuevo)
            sp.Popen(["code", ruta], shell=True)
            return f"Archivo modificado y abierto en VSCode."
        except Exception as e:
            return f"No pude guardar: {e}"

    elif tipo == "futbol_lista":
        fecha = accion[1] if len(accion) > 1 else None
        log_fn("Buscando partidos...", "accion")
        return _futbol.partidos_por_fecha(fecha)

    elif tipo == "futbol_equipo":
        equipo = accion[1]
        fecha = accion[2]
        log_fn(f"Buscando partido de {equipo}...", "accion")
        return _futbol.buscar_partido_equipo(equipo, fecha)

    elif tipo == "buscar_futbol":
        return buscar_futbol_api(accion[1])

    elif tipo == "sistema_todo":
        info = jarvis_system.get_todo()
        return preguntar_ollama_con_contexto("Resume los componentes del PC", info)
    elif tipo == "sistema_cpu":
        return jarvis_system.get_cpu_info()
    elif tipo == "sistema_gpu":
        try:
            return jarvis_system.get_gpu_info()
        except Exception as e:
            return f"No pude leer la GPU: {e}"
    elif tipo == "sistema_ram":
        return jarvis_system.get_ram_info()
    elif tipo == "sistema_disco":
        return jarvis_system.get_discos_info()
    elif tipo == "sistema_temp":
        try:
            return jarvis_system.get_temperaturas()
        except Exception as e:
            return f"No pude leer temperaturas: {e}"
    elif tipo == "sistema_procesos":
        return jarvis_system.get_procesos_top()
    elif tipo == "sistema_red":
        return jarvis_system.get_red_info()

    elif tipo == "buscar_web":
        query = accion[1]
        t_query = query.lower()
        if any(p in t_query for p in ["youtube", "yutu", "you tube", "yt"]):
            nombre = re.sub(r'(?:busca?(?:r)?|pon|reproduce?|encuentra?)\s+', '', t_query)
            nombre = re.sub(r'\s+en\s+(?:youtube|yutu|you\s*tube|yt).*', '', nombre).strip()
            return buscar_en_youtube(nombre or query)
        if "spotify" in t_query:
            nombre = re.sub(r'(?:busca?|pon|reproduce?)\s+', '', t_query)
            nombre = re.sub(r'\s+en\s+spotify.*', '', nombre).strip()
            return reproducir_en_spotify(nombre or query)
        query_busqueda = query if any(p in t_query for p in ["españa","spain","madrid","barcelona"]) else query + " España"
        try:
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query_busqueda, max_results=5))
            if not resultados:
                return "No encontré resultados."
            resumen = " | ".join([r.get("body","")[:250] for r in resultados[:3]])
            return preguntar_ollama_con_contexto(query, resumen)
        except Exception as e:
            return f"Error al buscar: {e}"

    elif tipo == "mates_avanzadas":
        resultado_sympy = calcular_mates(accion[1])
        if resultado_sympy:
            # Devolver en formato matemático limpio: 2x^2 - 3x
            return resultado_sympy
        # Si SymPy no pudo parsear, intentar con Ollama pero con prompt específico de mates
        try:
            r = requests.post(OLLAMA_URL, json={
                "model": MODELO_LLM,
                "prompt": (
                    "Eres un profesor de matemáticas. Responde en español de España, "
                    "sin LaTeX, sin símbolos raros, en texto natural para hablar en voz alta. "
                    "Máximo 2 frases, solo el resultado. "
                    f"Pregunta: {accion[1]}"
                ),
                "stream": False
            }, timeout=60)
            resp = r.json().get("response", "No pude calcular eso.").strip()
            # Limpiar LaTeX
            import re as _re
            resp = _re.sub(r'\$+', '', resp)
            resp = _re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 entre \2', resp)
            resp = _re.sub(r'\\[a-zA-Z]+\{?', '', resp)
            resp = _re.sub(r'\{|\}|\\', '', resp)
            resp = resp.replace('ln', 'logaritmo neperiano de')
            return resp
        except:
            return "No pude resolver esa expresión. Intenta decirla más despacio y completa."

    elif tipo == "traducir":
        texto_orig, idioma = accion[1], accion[2]
        return traducir(texto_orig, idioma)

    elif tipo == "verificar":
        pregunta_original = accion[1]
        log_fn(f"Buscando en internet: {pregunta_original[:40]}...", "accion")
        # Verificar con búsqueda web directa
        return ejecutar_accion(("buscar_web", pregunta_original), log_fn)

    elif tipo == "memoria":
        if not MEM_OK:
            return "Módulo de memoria no disponible."
        subtipo = accion[1]
        if subtipo == 'listar':
            return _mem.listar_memoria()
        elif subtipo == 'olvidar':
            return _mem.olvidar(accion[2])
        elif subtipo == 'recordar':
            return _mem.recordar(accion[2], accion[3])
        elif subtipo == 'consultar':
            # Responder pregunta personal usando memoria + Ollama
            pregunta = accion[2]
            contexto = _mem.obtener_contexto()
            if not contexto:
                return "No tengo nada guardado sobre ti. Dime algo con 'recuerda que...'."
            try:
                r = requests.post(OLLAMA_URL, json={
                    "model": MODELO_LLM,
                    "prompt": (
                        f"{SYSTEM_PROMPT}\n\n{contexto}\n\n"
                        f"Basándote SOLO en la información anterior, responde brevemente: {pregunta}\nJARVIS:"
                    ),
                    "stream": False
                }, timeout=20)
                return r.json().get("response", "").strip()
            except:
                return _mem.listar_memoria()

    elif tipo == "minecraft_backup":
        subtipo = accion[1]
        if subtipo == 'listar':
            return _mc.listar_backups()
        elif subtipo == 'abrir_servidor':
            log_fn("Abriendo servidor de Minecraft...", "accion")
            return _mc.abrir_servidor()
        elif subtipo == 'cerrar_servidor':
            log_fn("Cerrando servidor de Minecraft...", "accion")
            return _mc.cerrar_servidor()
        else:
            log_fn("Haciendo backup del mundo...", "accion")
            return _mc.hacer_backup(log_fn)

    elif tipo == "listar_eventos":
        if not CAL_OK:
            return "Módulo de calendario no disponible."
        log_fn("Consultando agenda...", "accion")
        return _cal.listar_eventos(accion[1])

    elif tipo == "calendario":
        if not CAL_OK:
            return "Módulo de calendario no disponible."
        titulo, fecha_str = accion[1], accion[2]
        try:
            fecha_hora = _cal.parsear_fecha_hora(fecha_str)
            return _cal.crear_evento(titulo, fecha_hora)
        except Exception as e:
            return f"No entendí la fecha: {e}"

    elif tipo == "archivo":
        if not ARCHIVOS_OK:
            return "Módulo de archivos no disponible."
        # accion = ("archivo", tipo_arch, modo, nombre, accion_arch)
        tipo_arch = accion[1]   # 'codigo' o 'archivo'
        modo = accion[2]        # 'nombre' o 'reciente'
        nombre = accion[3]
        accion_arch = accion[4]

        if modo == 'nombre' and nombre:
            ruta = _archivos._buscar_archivo(nombre)
            if not ruta:
                return f"No encontré ningún archivo llamado {nombre}."
        else:
            # Más reciente del tipo correspondiente
            exts = _archivos.EXT_CODIGO if tipo_arch == 'codigo' else (_archivos.EXT_TEXTO + ('.pdf', '.docx'))
            ruta = _archivos._archivo_mas_reciente(exts)
            if not ruta:
                return "No encontré ningún archivo reciente para analizar."

        log_fn(f"Analizando {os.path.basename(ruta)}...", "accion")
        return _archivos.analizar_archivo(ruta, accion_arch)

    elif tipo == "generar_imagen":
        if not IMAGENES_OK:
            return "Módulo de generación de imágenes no disponible."
        descripcion = accion[1]
        return _imagenes.generar_imagen(descripcion, log_fn)

    elif tipo == "vision":
        if not VISION_OK:
            return "Módulo de visión no disponible. Ejecuta: ollama pull llava"
        modo, pregunta = accion[1], accion[2]
        log_fn(f"Analizando imagen ({modo})...", "accion")
        return _vision.analizar(modo, pregunta)

    elif tipo == "juego":
        if not JUEGOS_OK:
            return "Módulo de juegos no disponible."
        subtipo = accion[1]
        if subtipo == 'que_juego':
            juego = _juegos.juego_activo()
            if juego:
                return f"Estás jugando a {juego}."
            return "No detecto ningún juego abierto ahora mismo."
        elif subtipo == 'buscar_juego':
            resultado = _juegos.buscar_info_juego(accion[2], log_fn)
            if isinstance(resultado, tuple) and resultado[0] == '_buscar_web':
                # Hacer búsqueda web con la query construida
                return ejecutar_accion(("buscar_web", resultado[1]), log_fn)
            return resultado

    elif tipo == "correo":
        if not CORREO_OK:
            return "Módulo de correo no disponible."
        # accion = ("correo", "leer_n", cantidad, solo_no_leidos)
        cantidad = accion[2]
        solo_no_leidos = accion[3]
        log_fn("Leyendo correos...", "accion")
        return _correo.leer_correos(cantidad=cantidad, solo_no_leidos=solo_no_leidos)

    elif tipo == "notificaciones":
        if not NOTI_OK:
            return "Módulo de notificaciones no disponible."
        return _noti.leer_notificaciones()

    elif tipo == "whatsapp":
        if not WHATSAPP_OK:
            return "WhatsApp no disponible. Instala selenium."
        contacto, mensaje = accion[1], accion[2]
        log_fn(f"Enviando WhatsApp a {contacto}...", "accion")
        return _wa.enviar_whatsapp_subprocess(contacto, mensaje)

    elif tipo == "phone_llamada":
        if not PHONE_LINK_OK:
            return "Phone Link no está disponible. Instala pywinauto: pip install pywinauto"
        subtipo = accion[1]
        if subtipo == "colgar":
            return phone_link.colgar_llamada()
        elif subtipo == "llamar":
            nombre = accion[2]
            log_fn(f"Llamando a {nombre}...", "accion")
            return phone_link.llamar_contacto(nombre)

    return "No entendí esa acción."


# ─── PROCESAMIENTO REMOTO (Telegram) ────
def procesar_orden_remota(texto):
    """Procesa una orden de texto (desde Telegram) y devuelve la respuesta.
    Usa el mismo pipeline que la voz pero sin hablar ni grabar audio.
    Si genera una imagen, la envía como foto a Telegram."""
    global _ultima_pregunta

    def _log_silencioso(t, tag):
        pass

    accion = detectar_accion(texto)

    if not (accion and accion[0] == 'verificar'):
        _ultima_pregunta = texto

    if accion:
        respuesta = ejecutar_accion(accion, _log_silencioso)

        # Si generó una imagen, enviarla por Telegram
        if accion[0] == 'generar_imagen' and TELEGRAM_OK and isinstance(respuesta, str):
            import re as _re_img
            m = _re_img.search(r'([A-Za-z]:\\[^\n]+\.png)', respuesta)
            if m:
                ruta_img = m.group(1)
                if os.path.exists(ruta_img):
                    _telegram.enviar_foto(ruta_img, "Imagen generada")
                    return "Imagen generada y enviada."
    else:
        respuesta = preguntar_ollama(texto)

    respuesta = respuesta or "Hecho."

    # Si la respuesta es muy larga, trocearla en varios mensajes de Telegram
    if TELEGRAM_OK and isinstance(respuesta, str) and len(respuesta) > 3800:
        _enviar_troceado(respuesta)
        return None  # ya enviado en trozos, no mandar de nuevo

    return respuesta


def _enviar_troceado(texto, tam=3600):
    """Envía un texto largo en varios mensajes de Telegram, respetando líneas.
    Si el texto es salida en bloque ``` y/o lleva un aviso interactivo
    al final (⌨️), reconstruye el bloque en cada trozo y deja el aviso al final."""

    # Separar un posible aviso interactivo del final (⌨️ ...)
    aviso = ""
    if "⌨️" in texto:
        idx = texto.find("⌨️")
        aviso = texto[idx:].strip()
        texto = texto[:idx].rstrip()

    # ¿Es un bloque de código? (empieza y/o acaba con ```)
    es_bloque = texto.lstrip().startswith("```")
    if es_bloque:
        # Quitar los ``` de los extremos para reinsertarlos en cada trozo
        cuerpo = texto.strip()
        if cuerpo.startswith("```"):
            cuerpo = cuerpo[3:]
        if cuerpo.endswith("```"):
            cuerpo = cuerpo[:-3]
        cuerpo = cuerpo.strip("\n")
    else:
        cuerpo = texto

    # Dividir el cuerpo en trozos por líneas
    margen = 12  # espacio para los ``` y encabezado
    lineas = cuerpo.split('\n')
    trozo = ""
    partes = []
    for linea in lineas:
        # Si una sola línea es enorme, partirla a lo bruto
        while len(linea) > tam - margen:
            partes_linea = linea[:tam - margen]
            if trozo:
                partes.append(trozo)
                trozo = ""
            partes.append(partes_linea)
            linea = linea[tam - margen:]
        if len(trozo) + len(linea) + 1 > tam - margen:
            partes.append(trozo)
            trozo = linea
        else:
            trozo = trozo + "\n" + linea if trozo else linea
    if trozo:
        partes.append(trozo)

    import time as _t
    total = len(partes)
    for i, parte in enumerate(partes):
        encabezado = f"📄 (parte {i+1}/{total})\n" if total > 1 else ""
        # Reenvolver en bloque de código si hace falta
        if es_bloque:
            cuerpo_msg = f"```\n{parte}\n```"
        else:
            cuerpo_msg = parte
        # El aviso interactivo va SOLO en el último trozo
        if i == total - 1 and aviso:
            cuerpo_msg = cuerpo_msg + "\n\n" + aviso
        _telegram.enviar_mensaje(encabezado + cuerpo_msg)
        _t.sleep(0.3)


# ─── INTERFAZ CYBERPUNK HUD ─────────────
class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS // SYSTEM ONLINE")
        self.root.geometry("720x510")
        self.root.configure(bg="#050814")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)  # sin borde de Windows

        # Colores
        self.bg      = "#050814"
        self.cyan    = "#00f6ff"
        self.magenta = "#ff00aa"
        self.green   = "#00ff88"
        self.yellow  = "#ffe100"
        self.white   = "#d9faff"
        self.orange  = "#ff6600"

        self.listening  = False
        self.processing = False
        self._anim_on   = True

        # Para arrastrar la ventana
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()

        gpu_name = torch.cuda.get_device_name(0) if DEVICE == "cuda" else "CPU"
        self._log(f"GPU: {gpu_name}", "system")
        self._log("Cargando Whisper en GPU...", "system")
        self._set_status("CARGANDO...", self.yellow)
        self.btn.config(state="disabled", text="◈  CARGANDO...  ◈")
        self.root.after(100, self._init_whisper)

        # Animación del título
        threading.Thread(target=self._animacion, daemon=True).start()

    def _build_ui(self):
        # Frame principal con borde neón
        self.main = tk.Frame(self.root, bg=self.bg,
                             highlightthickness=2, highlightbackground=self.cyan)
        self.main.pack(fill="both", expand=True)

        # ── Barra inferior (se reserva primero para que no la tapen) ──
        bottom = tk.Frame(self.main, bg=self.bg)
        bottom.pack(fill="x", side="bottom")
        tk.Label(bottom, text="  \u2630 arrastra", font=("Consolas", 8),
                fg="#335577", bg=self.bg).pack(side="left", pady=3)
        close_btn = tk.Label(bottom, text="\u2715 CERRAR  ", font=("Consolas", 9, "bold"),
                            fg=self.magenta, bg=self.bg, cursor="hand2")
        close_btn.pack(side="right", pady=3)
        close_btn.bind("<Button-1>", lambda e: self.on_close())
        min_btn = tk.Label(bottom, text="\u2013 MINIMIZAR   ", font=("Consolas", 9, "bold"),
                          fg=self.cyan, bg=self.bg, cursor="hand2")
        min_btn.pack(side="right", pady=3)
        min_btn.bind("<Button-1>", lambda e: self._minimizar())

        # ── Cabecera ──
        self.title = tk.Label(self.main, text="◆ J A R V I S  //  CORE SYSTEM",
                             font=("Consolas", 18, "bold"), fg=self.cyan, bg=self.bg)
        self.title.pack(pady=(14, 4))

        tk.Label(self.main, text="━" * 34, fg=self.magenta, bg=self.bg).pack()

        # ── Estado ──
        self.status_var = tk.StringVar(value="SISTEMA EN ESPERA")
        self.status_lbl = tk.Label(self.main, textvariable=self.status_var,
                                   font=("Consolas", 14), fg=self.green, bg=self.bg)
        self.status_lbl.pack(pady=(14, 10))

        # ── Terminal / consola ──
        self.log = tk.Text(self.main, height=9, width=72, bg="#02040b", fg=self.white,
                          insertbackground=self.cyan, font=("Consolas", 10), bd=0,
                          padx=10, pady=8)
        self.log.pack(padx=22, pady=4)

        # Colores por tipo de mensaje
        self.log.tag_config("system", foreground="#5fd7ff")
        self.log.tag_config("user",   foreground=self.white)
        self.log.tag_config("jarvis", foreground=self.green)
        self.log.tag_config("accion", foreground=self.yellow)
        self.log.tag_config("error",  foreground="#ff5577")

        self.log.insert("end", "> JARVIS iniciado...\n> Sistemas cargados\n> Esperando órdenes\n")
        self.log.config(state="disabled")

        # ── Indicadores ──
        self.info = tk.Label(self.main,
            text="MIC  ● READY        AI  ● MISTRAL        GPU  ● CUDA",
            font=("Consolas", 10), fg=self.cyan, bg=self.bg)
        self.info.pack(pady=(10, 8))

        # ── Botón principal ──
        self.btn = tk.Button(self.main,
            text=f"◈  ACTIVAR / INTERRUMPIR  [{TECLA_ACTIVAR.upper()}]  ◈",
            font=("Consolas", 11, "bold"), fg=self.bg, bg=self.magenta,
            activebackground=self.cyan, bd=0, relief="flat", cursor="hand2",
            command=self._toggle)
        self.btn.pack(pady=(0, 6), ipadx=10, ipady=6)

        # Arrastrar la ventana desde el título y la cabecera
        for widget in (self.title, self.main):
            widget.bind("<Button-1>", self._click_pos)
            widget.bind("<B1-Motion>", self._mover)

    def _minimizar(self):
        # Con overrideredirect, iconify no funciona directamente.
        # Truco: quitar override, minimizar, y al restaurar volver a quitarlo.
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("<Map>", self._al_restaurar)

    def _al_restaurar(self, event=None):
        # Cuando la ventana vuelve de la barra de tareas
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.unbind("<Map>")

    def _click_pos(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _mover(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _log(self, text, tag="system"):
        self.log.config(state="normal")
        prefix = {"system":"SYS","user":"TÚ","jarvis":"JARVIS","accion":"ACCIÓN","error":"ERROR"}
        self.log.insert("end", f"\n> [{prefix.get(tag,'   ')}] {text}", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_status(self, text_or_state, color=None):
        """Acepta tanto ('idle'/'listening'/...) como ('TEXTO', '#color')."""
        if text_or_state in ("idle", "listening", "processing", "speaking"):
            cfg = {
                "idle":       ("SISTEMA EN ESPERA", self.green,   self.magenta, f"◈  ACTIVAR / INTERRUMPIR  [{TECLA_ACTIVAR.upper()}]  ◈", "normal"),
                "listening":  ("◉ ESCUCHANDO",  self.cyan,    self.cyan,    f"◈  DETENER  [{TECLA_ACTIVAR.upper()}]  ◈",              "normal"),
                "processing": ("◈ PROCESANDO",  self.yellow,  self.yellow,  "◈  PROCESANDO...  ◈",                                   "disabled"),
                "speaking":   ("◈ HABLANDO",    self.magenta, self.magenta, f"◈  HABLANDO — {TECLA_ACTIVAR.upper()} INTERRUMPE  ◈", "normal"),
            }
            label, sc, bc, bt, bs = cfg.get(text_or_state, cfg["idle"])
            self.status_var.set(label)
            self.status_lbl.config(fg=sc)
            self.btn.config(text=bt, fg=self.bg, bg=bc, state=bs)
        else:
            # Modo texto + color manual
            self.status_var.set(text_or_state)
            if color:
                self.status_lbl.config(fg=color)
            if color == self.cyan:
                self.btn.config(text=f"◈  DETENER  [{TECLA_ACTIVAR.upper()}]  ◈", fg=self.bg, bg=self.cyan, state="normal")
            elif color == self.yellow:
                self.btn.config(text="◈  PROCESANDO...  ◈", fg=self.bg, bg=self.yellow, state="disabled")
            elif color == self.orange:
                self.btn.config(fg=self.bg, bg=self.orange, state="normal")
            else:
                self.btn.config(text=f"◈  ACTIVAR / INTERRUMPIR  [{TECLA_ACTIVAR.upper()}]  ◈",
                                fg=self.bg, bg=self.magenta, state="normal")

    def _init_whisper(self):
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        cargar_whisper()
        self.root.after(0, self._whisper_ready)

    def _whisper_ready(self):
        self._log(f"Whisper en {DEVICE.upper()}. Sistema listo.", "system")
        self._log("Volumen, apps, webs, notas, clima, fútbol, código, imágenes, documentos...", "system")
        self._set_status("idle")
        keyboard.add_hotkey(TECLA_ACTIVAR, lambda: self.root.after(0, self._toggle), suppress=False)

        # Arrancar bot de Telegram (control remoto desde el móvil)
        if TELEGRAM_OK:
            try:
                _telegram.iniciar(
                    procesar_orden_remota,
                    lambda t, tag: self.root.after(0, lambda: self._log(t, tag))
                )
                self._log("Bot de Telegram activo. Control remoto disponible.", "system")
            except Exception as e:
                self._log(f"No se pudo iniciar Telegram: {e}", "error")

    def _toggle(self):
        global _speaking, _speaking_process, _historial, _ultimo_resultado
        if _speaking:
            detener_habla()
            self._set_status("● INTERRUMPIDO", self.orange)
            self.root.after(1000, lambda: self._set_status("idle"))
            return
        if self.processing:
            return
        if not self.listening:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        global listening
        self.listening = True
        listening = True
        self._set_status("listening")
        threading.Thread(target=self._pipeline, daemon=True).start()

    def _stop_listening(self):
        global listening
        self.listening = False
        listening = False

    def _pipeline(self):
        audio = grabar_audio()
        self.processing = True
        self.root.after(0, lambda: self._set_status("processing"))
        if audio is None or len(audio) < SAMPLE_RATE * 0.4:
            self.root.after(0, lambda: self._log("No detecté audio.", "error"))
            self.processing = False
            self.root.after(0, lambda: self._set_status("idle"))
            return
        texto = audio_a_texto(audio)
        if not texto:
            self.root.after(0, lambda: self._log("No entendí nada.", "error"))
            self.processing = False
            self.root.after(0, lambda: self._set_status("idle"))
            return
        self.root.after(0, lambda t=texto: self._log(t, "user"))
        accion = detectar_accion(texto)
        if not (accion and accion[0] == 'verificar'):
            import sys as _sys
            _sys.modules[__name__]._ultima_pregunta = texto
        if accion:
            self.root.after(0, lambda a=accion: self._log(f"Acción: {a[0]}", "accion"))
            respuesta = ejecutar_accion(accion, lambda t, tag: self.root.after(0, lambda tt=t, tg=tag: self._log(tt, tg)))
        else:
            respuesta = preguntar_ollama(texto)
        if not respuesta:
            respuesta = "Hecho."
        self.root.after(0, lambda r=respuesta: self._log(r, "jarvis"))
        self.root.after(0, lambda: self._set_status("speaking"))
        hablar(respuesta)
        self.processing = False
        self.root.after(0, lambda: self._set_status("idle"))

    def _animacion(self):
        """Parpadeo suave del título entre cian y magenta."""
        while self._anim_on:
            try:
                self.root.after(0, lambda: self.title.config(fg=self.cyan))
                time.sleep(0.9)
                self.root.after(0, lambda: self.title.config(fg=self.magenta))
                time.sleep(0.9)
            except:
                break

    def on_close(self):
        self._anim_on = False
        try:
            keyboard.unhook_all()
        except:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = JarvisApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
