"""
Módulo para explorar carpetas de cualquier disco desde JARVIS / Telegram
"""
import os
import re

# Carpetas conocidas por nombre hablado
CARPETAS_CONOCIDAS = {
    'escritorio': os.path.expandvars(r"%USERPROFILE%\Desktop"),
    'descargas': os.path.expandvars(r"%USERPROFILE%\Downloads"),
    'documentos': os.path.expandvars(r"%USERPROFILE%\Documents"),
    'imágenes': os.path.expandvars(r"%USERPROFILE%\Pictures"),
    'imagenes': os.path.expandvars(r"%USERPROFILE%\Pictures"),
    'música': os.path.expandvars(r"%USERPROFILE%\Music"),
    'musica': os.path.expandvars(r"%USERPROFILE%\Music"),
    'vídeos': os.path.expandvars(r"%USERPROFILE%\Videos"),
    'videos': os.path.expandvars(r"%USERPROFILE%\Videos"),
}

# Discos donde buscar carpetas por nombre
DISCOS = ['C:\\', 'D:\\', 'E:\\', 'F:\\', 'G:\\']

# Carpetas del sistema que se saltan en la búsqueda profunda (lentas e irrelevantes)
SALTAR = {'windows', 'program files', 'program files (x86)', 'programdata',
          '$recycle.bin', 'system volume information', 'windowsapps', 'appdata',
          'node_modules', '.git', 'recovery', 'perflogs', 'msocache', 'intel',
          'nvidia', 'amd', '$windows.~bt', '$windows.~ws', 'config.msi',
          'documents and settings', 'onedrivetemp', '.cache'}

# Máxima profundidad de búsqueda recursiva
MAX_PROFUNDIDAD = 5

# Última carpeta explorada (para "dime el contenido del archivo X")
_ultima_carpeta = None
_ultimos_archivos = []


def _buscar_recursivo(nombre, exacto=True):
    """Busca una carpeta en profundidad por todos los discos.
    exacto=True: coincidencia exacta del nombre. exacto=False: parcial."""
    nombre = nombre.lower()

    for disco in DISCOS:
        if not os.path.isdir(disco):
            continue
        # Recorrido por niveles con límite de profundidad
        pila = [(disco, 0)]
        while pila:
            actual, prof = pila.pop()
            if prof > MAX_PROFUNDIDAD:
                continue
            try:
                with os.scandir(actual) as it:
                    for entry in it:
                        try:
                            if not entry.is_dir():
                                continue
                            nombre_dir = entry.name.lower()
                            # Saltar carpetas del sistema
                            if nombre_dir in SALTAR or nombre_dir.startswith('$'):
                                continue
                            # ¿Coincide?
                            if exacto and nombre_dir == nombre:
                                return entry.path
                            if not exacto and nombre in nombre_dir:
                                return entry.path
                            # Seguir bajando
                            pila.append((entry.path, prof + 1))
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                continue
    return None


def _buscar_carpeta(nombre):
    """Busca una carpeta por nombre. Devuelve la ruta o None."""
    nombre = nombre.strip().lower()

    # ¿Es una carpeta conocida? (rápido)
    if nombre in CARPETAS_CONOCIDAS:
        ruta = CARPETAS_CONOCIDAS[nombre]
        if os.path.isdir(ruta):
            return ruta

    # ¿Es una ruta directa? (ej "d:\mis-proyectos")
    if os.path.isdir(nombre):
        return nombre

    # Búsqueda profunda: primero exacta, luego parcial
    ruta = _buscar_recursivo(nombre, exacto=True)
    if ruta:
        return ruta
    return _buscar_recursivo(nombre, exacto=False)


def buscar_archivo_global(nombre_archivo):
    """Busca un archivo por nombre en todo el PC (en profundidad)."""
    global _ultima_carpeta, _ultimos_archivos

    nombre = nombre_archivo.strip().lower()
    nombre_sin_ext = os.path.splitext(nombre)[0]
    encontrados = []

    for disco in DISCOS:
        if not os.path.isdir(disco):
            continue
        pila = [(disco, 0)]
        while pila and len(encontrados) < 10:
            actual, prof = pila.pop()
            if prof > MAX_PROFUNDIDAD:
                continue
            try:
                with os.scandir(actual) as it:
                    for entry in it:
                        try:
                            ename = entry.name.lower()
                            if entry.is_dir():
                                if ename in SALTAR or ename.startswith('$'):
                                    continue
                                pila.append((entry.path, prof + 1))
                            elif entry.is_file():
                                base = os.path.splitext(ename)[0]
                                if nombre == ename or nombre_sin_ext == base or nombre_sin_ext in base:
                                    encontrados.append(entry.path)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                continue

    if not encontrados:
        return f"No encontré ningún archivo llamado '{nombre_archivo}' en el PC."

    # Guardar la carpeta del primer resultado para poder leerlo después
    primero = encontrados[0]
    _ultima_carpeta = os.path.dirname(primero)
    try:
        _ultimos_archivos = os.listdir(_ultima_carpeta)
    except:
        _ultimos_archivos = [os.path.basename(primero)]

    if len(encontrados) == 1:
        return f"Encontrado: {primero}"

    lineas = [f"Encontré {len(encontrados)} archivos:"]
    for f in encontrados[:10]:
        lineas.append(f"  {f}")
    return "\n".join(lineas)


def listar_carpeta(nombre_carpeta):
    """Lista los archivos de una carpeta."""
    global _ultima_carpeta, _ultimos_archivos

    ruta = _buscar_carpeta(nombre_carpeta)
    if not ruta:
        return f"No encontré la carpeta '{nombre_carpeta}' en ningún disco."

    try:
        items = os.listdir(ruta)
    except Exception as e:
        return f"No pude abrir la carpeta: {e}"

    if not items:
        return f"La carpeta {os.path.basename(ruta)} está vacía."

    _ultima_carpeta = ruta
    _ultimos_archivos = items

    # Separar carpetas y archivos
    carpetas = []
    archivos = []
    for item in sorted(items):
        full = os.path.join(ruta, item)
        if os.path.isdir(full):
            carpetas.append(item)
        else:
            archivos.append(item)

    lineas = [f"Contenido de {ruta}:\n"]
    if carpetas:
        lineas.append("Carpetas:")
        for c in carpetas[:30]:
            lineas.append(f"  📁 {c}")
    if archivos:
        lineas.append("\nArchivos:")
        for a in archivos[:50]:
            lineas.append(f"  📄 {a}")

    total = len(carpetas) + len(archivos)
    if total > 80:
        lineas.append(f"\n...y más ({total} en total)")

    return "\n".join(lineas)


def _resolver_archivo(nombre_archivo):
    """Encuentra un archivo en la última carpeta explorada."""
    if not _ultima_carpeta:
        return None

    nombre = nombre_archivo.strip().lower()
    nombre_sin_ext = os.path.splitext(nombre)[0]

    # Buscar coincidencia exacta o parcial
    for archivo in _ultimos_archivos:
        al = archivo.lower()
        if nombre == al or nombre_sin_ext == os.path.splitext(al)[0]:
            return os.path.join(_ultima_carpeta, archivo)
    # Parcial
    for archivo in _ultimos_archivos:
        if nombre_sin_ext in archivo.lower():
            return os.path.join(_ultima_carpeta, archivo)
    return None


def leer_archivo_de_carpeta(nombre_archivo, accion='mostrar'):
    """
    Lee/muestra/resume un archivo de la última carpeta explorada.
    accion: 'mostrar' (contenido tal cual), 'leer' (igual), 'resumir' (con IA)
    """
    ruta = _resolver_archivo(nombre_archivo)
    if not ruta:
        # Quizás no exploró carpeta antes; intentar como ruta directa
        return (f"No encontré '{nombre_archivo}'. Primero dime la carpeta "
                f"(ej: 'abre la carpeta escritorio') y luego el archivo.")

    if not os.path.isfile(ruta):
        return f"'{nombre_archivo}' no es un archivo."

    ext = os.path.splitext(ruta)[1].lower()
    nombre = os.path.basename(ruta)

    # Si quiere resumen, usar el módulo archivos (IA)
    if accion == 'resumir':
        try:
            import archivos as _arch
            return _arch.analizar_archivo(ruta, 'resumir')
        except ImportError:
            accion = 'mostrar'  # fallback

    # Mostrar/leer contenido directo
    EXT_LEGIBLE = ('.txt', '.md', '.log', '.csv', '.json', '.xml', '.ini', '.cfg',
                   '.py', '.php', '.js', '.html', '.css', '.java', '.cpp', '.c',
                   '.bat', '.ps1', '.yml', '.yaml', '.properties', '.toml')

    if ext == '.pdf':
        try:
            import archivos as _arch
            contenido = _arch._leer_pdf(ruta)
        except:
            return "Para PDF necesito el módulo de archivos."
    elif ext == '.docx':
        try:
            import archivos as _arch
            contenido = _arch._leer_docx(ruta)
        except:
            return "Para Word necesito el módulo de archivos."
    elif ext in EXT_LEGIBLE:
        try:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()
        except Exception as e:
            return f"No pude leer el archivo: {e}"
    else:
        tam = os.path.getsize(ruta)
        return f"{nombre} es un archivo {ext} ({tam} bytes). No puedo mostrar su contenido como texto."

    if not contenido.strip():
        return f"{nombre} está vacío."

    # Devolver el contenido completo (el troceo para Telegram lo hace jarvis.py)
    return f"📄 {nombre}:\n\n{contenido}"


def borrar_archivo(nombre_archivo, carpeta=None):
    """Mueve un archivo a la papelera de Windows.
    Si se da carpeta, busca ahí; si no, usa la última carpeta explorada."""
    global _ultima_carpeta, _ultimos_archivos

    ruta = None

    # Si especifica carpeta, buscarla primero
    if carpeta:
        carpeta_ruta = _buscar_carpeta(carpeta)
        if not carpeta_ruta:
            return f"No encontré la carpeta '{carpeta}'."
        # Buscar el archivo dentro
        nombre = nombre_archivo.strip().lower()
        nombre_sin_ext = os.path.splitext(nombre)[0]
        try:
            for archivo in os.listdir(carpeta_ruta):
                al = archivo.lower()
                if nombre == al or nombre_sin_ext == os.path.splitext(al)[0] or nombre_sin_ext in al:
                    ruta = os.path.join(carpeta_ruta, archivo)
                    break
        except Exception as e:
            return f"No pude acceder a la carpeta: {e}"
    else:
        # Usar la última carpeta explorada
        ruta = _resolver_archivo(nombre_archivo)

    if not ruta:
        return (f"No encontré '{nombre_archivo}'. Dime la carpeta "
                f"(ej: 'borra notas.txt de la carpeta escritorio').")

    if not os.path.isfile(ruta):
        return f"'{nombre_archivo}' no es un archivo (o es una carpeta)."

    nombre_real = os.path.basename(ruta)

    # Mover a la papelera
    try:
        from send2trash import send2trash
        send2trash(ruta)
        # Actualizar la lista en memoria
        if _ultimos_archivos and nombre_real in _ultimos_archivos:
            _ultimos_archivos.remove(nombre_real)
        return f"He movido {nombre_real} a la papelera."
    except ImportError:
        return "Necesito send2trash. Instala: pip install send2trash"
    except Exception as e:
        return f"No pude borrar {nombre_real}: {e}"


def detectar_explorador(texto):
    """
    Detecta órdenes de exploración de carpetas/archivos.
    Devuelve ('listar', carpeta) o ('leer', archivo, accion) o None.
    """
    t = texto.lower().strip()

    # Buscar archivo en todo el PC: "busca el archivo X en el pc / en todo el ordenador"
    m = re.search(r'busca(?:r)?\s+(?:el\s+)?(?:archivo|fichero)\s+(.+?)(?:\s+en\s+(?:el\s+)?(?:pc|ordenador|equipo|todo|todas?\s+partes?))', t)
    if m:
        return ('buscar_archivo', m.group(1).strip().rstrip('.,;:'))

    # Listar carpeta: "abre/busca/lista la carpeta X", "qué hay en la carpeta X"
    m = re.search(r'(?:abre|busca|lista|listar|muestra|mu[eé]strame|ver|entra en|qu[eé] hay en|contenido de)\s+(?:la\s+)?(?:carpeta|directorio)\s+(?:llamada?\s+)?(.+)', t)
    if m:
        carpeta = m.group(1).strip().rstrip('.,;:')
        # Limpiar "en el disco X", "del disco X"
        carpeta = re.sub(r'\s+(?:en|del|de)\s+(?:el\s+)?disco.*$', '', carpeta).strip()
        return ('listar', carpeta)

    # Borrar archivo: "borra/elimina el archivo X (de la carpeta Y)"
    # NO capturar si habla de eventos/citas/recordatorios (eso es del calendario)
    _es_calendario = any(p in t for p in ['evento', 'cita', 'recordatorio', 'reunión', 'reunion'])
    m = re.search(r'(?:borra|borrar|elimina|eliminar|qu[ií]ta|quitar)\s+(?:el\s+)?(?:archivo|fichero|documento)?\s*(.+)', t)
    if m and not _es_calendario and any(p in t for p in ['borra', 'borrar', 'elimina', 'eliminar', 'quita', 'quitar']):
        resto = m.group(1).strip().rstrip('.,;:')
        # ¿Menciona carpeta? "X de la carpeta Y"
        carpeta = None
        mc = re.search(r'(.+?)\s+(?:de|en)\s+(?:la\s+)?carpeta\s+(.+)', resto)
        if mc:
            archivo = mc.group(1).strip()
            carpeta = mc.group(2).strip().rstrip('.,;:')
        else:
            archivo = resto
        return ('borrar', archivo, carpeta)

    # Leer/mostrar/resumir archivo: "lee/muestra/resume el archivo X"
    m = re.search(r'(?:lee|leer|muestra|mu[eé]strame|resume|resumir|abre)\s+(?:el\s+)?(?:archivo|fichero|documento)\s+(.+)', t)
    if m:
        archivo = m.group(1).strip().rstrip('.,;:')
        if 'resume' in t or 'resumir' in t:
            accion = 'resumir'
        else:
            accion = 'mostrar'
        return ('leer', archivo, accion)

    return None
