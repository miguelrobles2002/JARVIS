"""
Módulo de memoria persistente para JARVIS
Guarda y recupera información entre sesiones
"""
import re, json, os
from datetime import datetime

MEMORIA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memoria.json")


def _cargar():
    """Carga la memoria del archivo."""
    if not os.path.exists(MEMORIA_PATH):
        return {}
    try:
        with open(MEMORIA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def _guardar(memoria):
    """Guarda la memoria en el archivo."""
    with open(MEMORIA_PATH, 'w', encoding='utf-8') as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)


def recordar(clave, valor):
    """Guarda un dato en la memoria."""
    memoria = _cargar()
    memoria[clave] = {
        'valor': valor,
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    _guardar(memoria)
    return f"Lo recordaré: {clave} → {valor}."


def olvidar(clave):
    """Elimina un dato de la memoria."""
    memoria = _cargar()
    # Buscar clave exacta o aproximada
    for k in list(memoria.keys()):
        if clave.lower() in k.lower() or k.lower() in clave.lower():
            del memoria[k]
            _guardar(memoria)
            return f"Olvidado: {k}."
    return f"No tenía nada guardado sobre '{clave}'."


def obtener_contexto():
    """Devuelve la memoria como texto para incluir en el prompt de Ollama."""
    memoria = _cargar()
    if not memoria:
        return ""
    lineas = ["Información que recuerdas sobre el usuario:"]
    for clave, dato in memoria.items():
        lineas.append(f"- {clave}: {dato['valor']}")
    return "\n".join(lineas)


def listar_memoria():
    """Lista todo lo que JARVIS recuerda."""
    memoria = _cargar()
    if not memoria:
        return "No recuerdo nada guardado todavía."
    lineas = [f"Recuerdo {len(memoria)} cosa{'s' if len(memoria) != 1 else ''}:"]
    for clave, dato in memoria.items():
        lineas.append(f"• {clave}: {dato['valor']}")
    return ". ".join(lineas)


def detectar_memoria(texto):
    """
    Detecta si el usuario quiere guardar/borrar/listar memoria.
    Devuelve ('recordar', clave, valor), ('olvidar', clave), ('listar',) o None.
    """
    t = texto.lower().strip()

    # Listar
    if any(p in t for p in ['qué recuerdas', 'que recuerdas', 'qué sabes de mí',
                              'que sabes de mi', 'qué tienes guardado', 'que tienes guardado']):
        return ('listar',)

    # Olvidar
    m_olv = re.search(r'(?:olvida|borra|elimina)\s+(?:que\s+)?(.+)', t)
    if m_olv:
        return ('olvidar', m_olv.group(1).strip().rstrip('.,;:'))

    # Recordar: "recuerda que X" o "recuerda mi nombre es X"
    m_rec = re.search(r'(?:recuerda|guarda|anota)\s+(?:que\s+)?(.+)', t)
    if m_rec:
        contenido = m_rec.group(1).strip().rstrip('.,;:')

        # Intentar separar clave y valor: "mi nombre es X", "trabajo de X", etc.
        patrones_kv = [
            (r'mi\s+(\w+(?:\s+\w+)?)\s+es\s+(.+)', lambda m: (f"nombre de {m.group(1)}", m.group(2))),
            (r'me\s+llamo\s+(.+)', lambda m: ("nombre", m.group(1))),
            (r'mi\s+equipo\s+(?:es\s+|favorito\s+es\s+)?(.+)', lambda m: ("equipo favorito", m.group(1))),
            (r'vivo\s+en\s+(.+)', lambda m: ("ciudad", m.group(1))),
            (r'trabajo\s+(?:de\s+|como\s+)?(.+)', lambda m: ("trabajo", m.group(1))),
            (r'tengo\s+(\d+)\s+años', lambda m: ("edad", m.group(1) + " años")),
        ]

        for patron, extractor in patrones_kv:
            m = re.search(patron, contenido)
            if m:
                try:
                    clave, valor = extractor(m)
                    return ('recordar', clave.strip(), valor.strip())
                except:
                    pass

        # Sin patrón específico: guardar el contenido completo
        return ('recordar', contenido[:50], contenido)

    return None
