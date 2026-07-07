"""
Módulo de lectura de correo Gmail para JARVIS
"""
import re, base64
import os
from email.header import decode_header

TOKEN  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/gmail.readonly']


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, 'w') as f:
            f.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def _decodificar(texto):
    """Decodifica encabezados MIME."""
    if not texto:
        return ""
    partes = decode_header(texto)
    resultado = ""
    for contenido, encoding in partes:
        if isinstance(contenido, bytes):
            try:
                resultado += contenido.decode(encoding or 'utf-8', errors='ignore')
            except:
                resultado += contenido.decode('utf-8', errors='ignore')
        else:
            resultado += contenido
    return resultado


def leer_correos(cantidad=5, solo_no_leidos=True):
    """Lee los correos más recientes."""
    try:
        service = _get_service()

        query = 'is:unread' if solo_no_leidos else ''
        results = service.users().messages().list(
            userId='me', q=query, maxResults=cantidad
        ).execute()

        mensajes = results.get('messages', [])
        if not mensajes:
            if solo_no_leidos:
                return "No tienes correos sin leer."
            return "No hay correos."

        lista = []
        for msg in mensajes:
            detalle = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['From', 'Subject']
            ).execute()

            headers = detalle.get('payload', {}).get('headers', [])
            remitente = ""
            asunto = ""
            for h in headers:
                if h['name'] == 'From':
                    remitente = _decodificar(h['value'])
                    # Limpiar email, dejar solo nombre
                    m = re.match(r'^"?([^"<]+)"?\s*<', remitente)
                    if m:
                        remitente = m.group(1).strip()
                    else:
                        remitente = remitente.split('@')[0]
                elif h['name'] == 'Subject':
                    asunto = _decodificar(h['value'])

            lista.append((remitente, asunto))

        n = len(lista)
        estado = "sin leer" if solo_no_leidos else ""
        resultado = f"Tienes {n} correo{'s' if n != 1 else ''} {estado}. "
        for i, (rem, asu) in enumerate(lista, 1):
            resultado += f"De {rem}: {asu}. "

        return resultado.strip()

    except Exception as e:
        return f"Error al leer correos: {e}"


def detectar_correo(texto):
    """Detecta si el usuario quiere leer correos."""
    t = texto.lower().strip()

    PALABRAS_CORREO = ['correo', 'correos', 'email', 'emails', 'gmail',
                       'mensaje de correo', 'bandeja de entrada', 'mail']

    if not any(p in t for p in PALABRAS_CORREO):
        return None

    # Acciones de lectura
    VERBOS_LECTURA = ['lee', 'leer', 'dime', 'cuántos', 'cuantos', 'cuál', 'cual',
                      'tengo', 'hay', 'revisa', 'comprueba', 'mira', 'muéstrame',
                      'muestrame', 'enséñame', 'ensename', 'último', 'ultimo',
                      'últimos', 'ultimos', 'nuevo', 'nuevos']
    if any(p in t for p in VERBOS_LECTURA):
        # "el último correo" (singular) → solo 1
        if any(p in t for p in ['último correo', 'ultimo correo', 'último email',
                                 'ultimo email', 'último e-mail', 'ultimo e-mail',
                                 'el último', 'el ultimo']):
            return ('leer_n', 1, False)  # 1 correo, incluye leídos
        # "los últimos" / "recientes" → varios incluyendo leídos
        if any(p in t for p in ['todos', 'últimos', 'ultimos', 'recientes']):
            return ('leer_n', 5, False)
        # Solo no leídos
        return ('leer_n', 5, True)

    return None
