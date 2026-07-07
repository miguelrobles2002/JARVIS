"""
Módulo de fútbol para JARVIS usando API-Football (api-sports.io)
Datos reales del Mundial 2026 y todas las ligas
"""
import re, requests
from datetime import datetime, timedelta

# La API key se lee de la configuración del usuario (config.json).
# Cada usuario puede conseguir una gratis en https://www.api-football.com
from configuracion import cargar_config
_CONFIG = cargar_config()
API_KEY = _CONFIG.get("futbol_api_key", "")
API_HOST = "v3.football.api-sports.io"
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY,
}

# Selecciones y equipos conocidos (para búsqueda por nombre)
EQUIPOS_CONOCIDOS = [
    'holanda', 'países bajos', 'paises bajos', 'japón', 'japon', 'alemania',
    'curazao', 'españa', 'cabo verde', 'bélgica', 'belgica', 'egipto', 'irán', 'iran',
    'arabia', 'arabia saudí', 'uruguay', 'argentina', 'francia', 'brasil', 'portugal',
    'inglaterra', 'italia', 'méxico', 'mexico', 'estados unidos', 'canadá', 'canada',
    'marruecos', 'croacia', 'suiza', 'senegal', 'corea', 'ecuador', 'costa de marfil',
    'suecia', 'túnez', 'tunez', 'australia', 'catar', 'qatar', 'noruega', 'austria',
    'dinamarca', 'real madrid', 'barcelona', 'atletico', 'atlético', 'sevilla', 'al hilal',
]


def _get(endpoint, params):
    """Hace una petición a la API."""
    if not API_KEY:
        return None  # sin API key configurada
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=10)
        if r.status_code != 200:
            return None
        return r.json().get("response", [])
    except Exception:
        return None


def _formatear_partido(fixture):
    """Formatea un partido de la API a texto legible."""
    teams = fixture.get("teams", {})
    goals = fixture.get("goals", {})
    status = fixture.get("fixture", {}).get("status", {}).get("short", "")

    local = teams.get("home", {}).get("name", "")
    visit = teams.get("away", {}).get("name", "")
    gl = goals.get("home")
    gv = goals.get("away")

    # Traducir algunos nombres al español
    TRAD = {
        'Netherlands': 'Países Bajos', 'Japan': 'Japón', 'Germany': 'Alemania',
        'Spain': 'España', 'Belgium': 'Bélgica', 'Egypt': 'Egipto', 'Iran': 'Irán',
        'Saudi Arabia': 'Arabia Saudí', 'Sweden': 'Suecia', 'Tunisia': 'Túnez',
        'United States': 'Estados Unidos', 'Mexico': 'México', 'Brazil': 'Brasil',
        'France': 'Francia', 'England': 'Inglaterra', 'Croatia': 'Croacia',
        'Morocco': 'Marruecos', 'Switzerland': 'Suiza', 'Denmark': 'Dinamarca',
        'Norway': 'Noruega', 'Austria': 'Austria', 'Australia': 'Australia',
        'Canada': 'Canadá', 'Ecuador': 'Ecuador', 'Uruguay': 'Uruguay',
        'Argentina': 'Argentina', 'Portugal': 'Portugal', 'Italy': 'Italia',
        'Cape Verde': 'Cabo Verde', 'Curacao': 'Curazao', 'Qatar': 'Catar',
        'South Korea': 'Corea del Sur', 'Ivory Coast': 'Costa de Marfil',
    }
    local = TRAD.get(local, local)
    visit = TRAD.get(visit, visit)

    # Estado del partido
    if status in ('FT', 'AET', 'PEN'):  # terminado
        return f"{local} {gl}-{gv} {visit}"
    elif status in ('1H', '2H', 'HT', 'ET', 'LIVE'):  # en juego
        return f"{local} {gl or 0}-{gv or 0} {visit} (en juego)"
    elif status == 'NS':  # no empezado
        hora = fixture.get("fixture", {}).get("date", "")[11:16]
        return f"{local} contra {visit} a las {hora}"
    else:
        if gl is not None and gv is not None:
            return f"{local} {gl}-{gv} {visit}"
        return f"{local} contra {visit}"


def partidos_por_fecha(fecha=None):
    """Lista los partidos de una fecha (formato YYYY-MM-DD)."""
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    fixtures = _get("fixtures", {"date": fecha})
    if fixtures is None:
        return "No pude conectar con el servicio de fútbol."
    if not fixtures:
        return "No hay partidos para esa fecha."

    # Ligas importantes con país exacto para evitar confusiones
    LIGAS_TOP = [
        ('world cup', 'world'),
        ('champions league', 'world'),
        ('europa league', 'world'),
        ('la liga', 'spain'),
        ('primera division', 'spain'),
        ('premier league', 'england'),
        ('serie a', 'italy'),
        ('bundesliga', 'germany'),
        ('ligue 1', 'france'),
        ('euro championship', 'world'),
        ('copa del rey', 'spain'),
        ('copa libertadores', 'world'),
    ]

    def es_top(fx):
        liga = fx.get("league", {}).get("name", "").lower()
        pais = fx.get("league", {}).get("country", "").lower()
        return any(liga == ln and pais == lp for ln, lp in LIGAS_TOP)

    top = [f for f in fixtures if es_top(f)]

    # Si hay Mundial, mostrar SOLO Mundial (es lo más relevante)
    mundial = [f for f in fixtures
               if f.get("league", {}).get("name", "").lower() == 'world cup']
    if mundial:
        usar = mundial
        etiqueta = "del Mundial"
    elif top:
        usar = top
        etiqueta = ""
    else:
        # No hay nada top, no abrumar con ligas menores
        return "No hay partidos de las grandes competiciones para esa fecha."

    partidos = [_formatear_partido(f) for f in usar[:15]]
    n = len(partidos)
    pref = f"Hay {n} partido{'s' if n != 1 else ''} {etiqueta}: ".replace("  ", " ")
    return pref + ". ".join(partidos)


def buscar_partido_equipo(nombre_equipo, fecha=None):
    """Busca el partido de un equipo concreto."""
    # Buscar el ID del equipo
    equipo_data = _get("teams", {"search": nombre_equipo})
    if not equipo_data:
        # Probar con búsqueda en inglés para selecciones
        TRAD_INV = {
            'holanda': 'Netherlands', 'países bajos': 'Netherlands', 'japón': 'Japan',
            'alemania': 'Germany', 'españa': 'Spain', 'bélgica': 'Belgium',
            'egipto': 'Egypt', 'irán': 'Iran', 'suecia': 'Sweden', 'túnez': 'Tunisia',
        }
        nombre_en = TRAD_INV.get(nombre_equipo.lower())
        if nombre_en:
            equipo_data = _get("teams", {"search": nombre_en})

    if not equipo_data:
        return f"No encontré al equipo {nombre_equipo}."

    team_id = equipo_data[0].get("team", {}).get("id")
    if not team_id:
        return f"No encontré al equipo {nombre_equipo}."

    # Buscar partidos del equipo
    params = {"team": team_id, "season": datetime.now().year}
    if fecha:
        params["date"] = fecha
        fixtures = _get("fixtures", params)
    else:
        # Último partido jugado
        fixtures = _get("fixtures", {"team": team_id, "last": 1})

    if not fixtures:
        return f"No encontré partidos de {nombre_equipo} para esa fecha."

    return _formatear_partido(fixtures[0]) + "."


def detectar_futbol(texto):
    """
    Detecta consultas de fútbol.
    Devuelve ('lista', fecha) o ('equipo', equipo, fecha) o None.
    """
    t = texto.lower().strip()

    GATILLOS = ["partidos de hoy", "partidos hoy", "qué partidos", "que partidos",
                "resultados de hoy", "resultados de ayer", "partidos de ayer",
                "resultados de", "cómo quedó", "como quedo", "cómo quedaron",
                "como quedaron", "resultado del", "resultado de", "marcador del",
                "marcador de", "todos los partidos", "qué se juega", "que se juega",
                "partido de", "partido del"]

    if not any(p in t for p in GATILLOS):
        return None

    # Determinar fecha
    fecha = None
    if 'ayer' in t:
        fecha = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif 'anteayer' in t:
        fecha = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    elif 'hoy' in t:
        fecha = datetime.now().strftime("%Y-%m-%d")
    else:
        dias = {'lunes':0,'martes':1,'miércoles':2,'miercoles':2,'jueves':3,
                'viernes':4,'sábado':5,'sabado':5,'domingo':6}
        for nombre, num in dias.items():
            if nombre in t:
                diff = (datetime.now().weekday() - num) % 7 or 7
                fecha = (datetime.now() - timedelta(days=diff)).strftime("%Y-%m-%d")
                break
        if not fecha:
            meses = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
                     'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
            m = re.search(r'(\d{1,2})\s+de\s+(\w+)', t)
            if m:
                try:
                    fecha = datetime(datetime.now().year, meses.get(m.group(2), 1),
                                     int(m.group(1))).strftime("%Y-%m-%d")
                except:
                    pass

    # ¿Menciona equipo concreto?
    equipos = [e for e in EQUIPOS_CONOCIDOS if e in t]
    if equipos:
        return ('equipo', equipos[0], fecha)

    return ('lista', fecha)
