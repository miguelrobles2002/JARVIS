"""
Módulo de detección de videojuegos para JARVIS
Detecta qué juego se está ejecutando y busca información
"""
import re, subprocess

# Mapa de procesos a nombres de juegos
JUEGOS_PROCESOS = {
    'valorant.exe':        'Valorant',
    'valorant-win64-shipping.exe': 'Valorant',
    'javaw.exe':           'Minecraft',
    'minecraft.exe':       'Minecraft',
    'gta5.exe':            'Grand Theft Auto V',
    'gta5_enhanced.exe':   'Grand Theft Auto V',
    'rdr2.exe':           'Red Dead Redemption 2',
    'rocketleague.exe':    'Rocket League',
    'fc26.exe':           'EA Sports FC 26',
    'fc25.exe':           'EA Sports FC 25',
    'hogwartslegacy.exe':  'Hogwarts Legacy',
    'farcry.exe':         'Far Cry Primal',
    'farcryprimal.exe':    'Far Cry Primal',
    'starwarsbattlefront.exe': 'Star Wars Battlefront',
    'starwarsbattlefrontii.exe': 'Star Wars Battlefront II',
    'pokemonz.exe':       'Pokémon Z',
    'pokemon.exe':        'Pokémon',
    # Comunes adicionales
    'csgo.exe':           'Counter-Strike',
    'cs2.exe':            'Counter-Strike 2',
    'leagueoflegends.exe': 'League of Legends',
    'fortniteclient-win64-shipping.exe': 'Fortnite',
}

# Webs oficiales/fiables por juego para buscar info
WEBS_JUEGOS = {
    'Valorant':              'playvalorant.com',
    'Minecraft':             'minecraft.wiki',
    'Grand Theft Auto V':    'gta.fandom.com',
    'Red Dead Redemption 2': 'reddead.fandom.com',
    'Rocket League':         'rocketleague.com',
    'EA Sports FC 26':       'ea.com',
    'Hogwarts Legacy':       'hogwartslegacy.com',
    'Far Cry Primal':        'farcry.fandom.com',
    'Star Wars Battlefront': 'starwars.fandom.com',
    'Pokémon Z':             'bulbapedia.bulbagarden.net',
    'Pokémon':               'bulbapedia.bulbagarden.net',
}


def juego_activo():
    """Detecta qué juego se está ejecutando ahora mismo."""
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        procesos = result.stdout.lower()

        for proc, nombre in JUEGOS_PROCESOS.items():
            if proc in procesos:
                return nombre
        return None
    except:
        return None


def detectar_consulta_juego(texto):
    """
    Detecta consultas sobre juegos.
    Devuelve ('que_juego',) o ('buscar_juego', pregunta) o None.
    """
    t = texto.lower().strip()

    # "¿A qué juego estoy jugando?"
    if any(p in t for p in ['qué juego', 'que juego', 'a qué estoy jugando',
                             'a que estoy jugando', 'qué estoy jugando',
                             'que estoy jugando', 'cuál es mi juego',
                             'cual es mi juego']):
        return ('que_juego',)

    # Consulta sobre el juego activo: "busca cómo conseguir X en este juego"
    PALABRAS_JUEGO = ['en este juego', 'del juego', 'de este juego',
                      'sobre el juego', 'en el juego que estoy']
    if any(p in t for p in PALABRAS_JUEGO):
        return ('buscar_juego', t)

    return None


def buscar_info_juego(pregunta, log_fn=None):
    """Busca información del juego activo en webs fiables."""
    juego = juego_activo()
    if not juego:
        return "No detecto ningún juego abierto ahora mismo."

    if log_fn:
        log_fn(f"Buscando info de {juego}...", "accion")

    # Construir query con la web oficial si la tenemos
    web = WEBS_JUEGOS.get(juego, '')

    # Limpiar la pregunta quitando referencias genéricas
    consulta = re.sub(r'\b(en este juego|del juego|de este juego|sobre el juego|en el juego que estoy|busca|buscar)\b',
                      '', pregunta).strip()

    if web:
        query = f"{juego} {consulta} site:{web}"
    else:
        query = f"{juego} {consulta}"

    return ('_buscar_web', query, juego)
