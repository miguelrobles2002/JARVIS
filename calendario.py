"""
Módulo de calendario para JARVIS - Google Calendar API
"""
import re, os, sys
from datetime import datetime, timedelta

CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
TOKEN       = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')
SCOPES      = ['https://www.googleapis.com/auth/calendar']


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN, 'w') as f:
                f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def crear_evento(titulo, fecha_hora, duracion_min=30, recordatorio_min=15, descripcion=""):
    """Crea un evento en Google Calendar."""
    try:
        service = _get_service()

        fin = fecha_hora + timedelta(minutes=duracion_min)
        fmt = "%Y-%m-%dT%H:%M:%S"

        evento = {
            'summary': titulo,
            'description': descripcion,
            'start': {'dateTime': fecha_hora.strftime(fmt), 'timeZone': 'Europe/Madrid'},
            'end':   {'dateTime': fin.strftime(fmt),        'timeZone': 'Europe/Madrid'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup',  'minutes': recordatorio_min},
                    {'method': 'email',  'minutes': recordatorio_min},
                ]
            }
        }

        result = service.events().insert(calendarId='primary', body=evento).execute()
        hora_fmt = fecha_hora.strftime("%d/%m/%Y a las %H:%M")
        return f"Evento '{titulo}' creado en Google Calendar para el {hora_fmt} con recordatorio {recordatorio_min} minutos antes."

    except Exception as e:
        return f"Error al crear evento: {e}"


def listar_eventos(dia="hoy"):
    """Lista los eventos del día (hoy o mañana)."""
    from datetime import datetime, timedelta
    try:
        service = _get_service()
    except Exception as e:
        return f"No pude conectar con el calendario: {e}"

    ahora = datetime.now()
    if dia == "mañana":
        inicio = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        etiqueta = "mañana"
    else:
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        etiqueta = "hoy"
    fin = inicio + timedelta(days=1)

    # Formato RFC3339 con zona horaria de Madrid
    time_min = inicio.isoformat() + "+02:00"
    time_max = fin.isoformat() + "+02:00"

    try:
        eventos = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
    except Exception as e:
        return f"Error al leer eventos: {e}"

    if not eventos:
        return f"No tienes eventos para {etiqueta}."

    lineas = [f"Eventos de {etiqueta}:"]
    for ev in eventos:
        inicio_ev = ev['start'].get('dateTime', ev['start'].get('date'))
        titulo = ev.get('summary', 'Sin título')
        # Extraer la hora
        if 'T' in inicio_ev:
            hora = inicio_ev.split('T')[1][:5]
            lineas.append(f"  {hora} — {titulo}")
        else:
            lineas.append(f"  Todo el día — {titulo}")
    return "\n".join(lineas)


def parsear_fecha_hora(texto):
    """Convierte texto hablado a datetime."""
    t = texto.lower().strip()
    ahora = datetime.now()

    m = re.search(r'en\s+(\d+)\s+(minuto|hora)', t)
    if m:
        n = int(m.group(1))
        return ahora + timedelta(hours=n if 'hora' in m.group(2) else 0,
                                  minutes=n if 'minuto' in m.group(2) else 0)

    dia_base = ahora
    # Quitar expresiones de hora ("de la mañana/tarde/noche") antes de buscar el día
    t_dia = re.sub(r'de\s+la\s+(ma[ñn]ana|tarde|noche|madrugada)', '', t)

    if 'hoy' in t:
        dia_base = ahora
    elif 'pasado mañana' in t_dia or 'pasado manana' in t_dia:
        dia_base = ahora + timedelta(days=2)
    elif 'mañana' in t_dia or 'manana' in t_dia:
        dia_base = ahora + timedelta(days=1)
    else:
        dias_semana = {'lunes':0,'martes':1,'miércoles':2,'miercoles':2,
                       'jueves':3,'viernes':4,'sábado':5,'sabado':5,'domingo':6}
        encontrado = False
        for nombre, num in dias_semana.items():
            if nombre in t:
                diff = (num - ahora.weekday()) % 7 or 7
                dia_base = ahora + timedelta(days=diff)
                encontrado = True
                break

        if not encontrado:
            meses = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
                     'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
            # Excluir "de la tarde/mañana/noche" - esos son horas, no fechas
            m_fecha = re.search(r'(?:el\s+)?(?:d[ií]a\s+)?(\d{1,2})\s+de\s+(?!la\s|las\s)(\w+)', t)
            if m_fecha:
                dia_num = int(m_fecha.group(1))
                mes_num = meses.get(m_fecha.group(2), ahora.month)
                try:
                    ft = ahora.replace(day=dia_num, month=mes_num)
                    if ft.date() < ahora.date():
                        ft = ft.replace(year=ft.year + 1)
                    dia_base = ft
                except: pass
            else:
                m_dia = re.search(r'(?:el\s+)?(?:d[ií]a\s+)(\d{1,2})(?!\s*de)', t)
                if not m_dia:
                    m_dia = re.search(r'(?:el\s+)(\d{1,2})(?:\s|$)', t)
                if m_dia:
                    dia_num = int(m_dia.group(1))
                    try:
                        ft = ahora.replace(day=dia_num)
                        if ft.date() < ahora.date():
                            ft = ft.replace(month=ft.month % 12 + 1)
                        dia_base = ft
                    except: pass

    hora, minuto = 9, 0
    m = re.search(r'a\s+las?\s+(\d{1,2})(?:\s+y\s+(media|cuarto|(\d{2})))?', t)
    if m:
        hora = int(m.group(1))
        if m.group(2) == 'media': minuto = 30
        elif m.group(2) == 'cuarto': minuto = 15
        elif m.group(3): minuto = int(m.group(3))

    if any(p in t for p in ['tarde','pm']) and hora < 12: hora += 12
    elif any(p in t for p in ['noche','madrugada']) and hora != 12 and hora < 12: hora += 12
    elif hora == 12 and 'noche' in t: hora = 0

    return dia_base.replace(hour=hora % 24, minute=minuto, second=0, microsecond=0)


def buscar_evento_por_nombre(nombre, dias=14):
    """Busca un evento por nombre en los próximos N días.
    Devuelve (evento_id, titulo, fecha_texto) o None."""
    from datetime import datetime, timedelta
    try:
        service = _get_service()
    except Exception:
        return None

    ahora = datetime.now()
    time_min = ahora.isoformat() + "+02:00"
    time_max = (ahora + timedelta(days=dias)).isoformat() + "+02:00"

    try:
        eventos = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
    except Exception:
        return None

    nombre = nombre.lower().strip()
    for ev in eventos:
        titulo = ev.get('summary', '').lower()
        if nombre in titulo or titulo in nombre:
            inicio_ev = ev['start'].get('dateTime', ev['start'].get('date'))
            # Formatear fecha legible
            try:
                if 'T' in inicio_ev:
                    dt = datetime.fromisoformat(inicio_ev.replace('Z', '+00:00'))
                    fecha_txt = dt.strftime("%d/%m a las %H:%M")
                else:
                    dt = datetime.fromisoformat(inicio_ev)
                    fecha_txt = dt.strftime("%d/%m")
            except Exception:
                fecha_txt = inicio_ev
            return (ev['id'], ev.get('summary', 'Sin título'), fecha_txt)

    return None


def borrar_evento(evento_id):
    """Borra un evento del calendario por su ID."""
    try:
        service = _get_service()
        service.events().delete(calendarId='primary', eventId=evento_id).execute()
        return True
    except Exception:
        return False


def detectar_borrado_evento(texto):
    """Detecta 'borra el evento X'. Devuelve el nombre o None."""
    t = texto.lower().strip()
    t = re.sub(r'[.,;:]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    if not any(p in t for p in ['borra', 'borrar', 'elimina', 'eliminar', 'quita', 'cancela']):
        return None
    if 'evento' not in t and 'cita' not in t and 'recordatorio' not in t:
        return None

    m = re.search(r'(?:borra|borrar|elimina|eliminar|quita|cancela)\s+(?:el\s+|la\s+)?(?:evento|cita|recordatorio)\s+(?:llamad[ao]\s+|de\s+)?(.+)', t)
    if m:
        nombre = m.group(1).strip()
        # Quitar referencias temporales del final
        nombre = re.sub(r'\s+(?:de\s+)?(?:hoy|mañana|manana).*$', '', nombre).strip()
        if nombre and len(nombre) > 1:
            return nombre
    return None


def detectar_evento(texto):
    """Detecta si el usuario quiere crear un evento."""
    t = texto.lower().strip()
    # Limpiar puntuación que Whisper añade
    t = re.sub(r'[.,;:]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    PALABRAS_EVENTO = ['evento','cita','recordatorio','recuérdame','recuerdame',
                       'agenda','apunta','calendario','reunión','reunion','crea un','pon un','añade']
    if not any(p in t for p in PALABRAS_EVENTO):
        return None

    # Patrón prioritario: "crea/pon el evento TITULO hoy/mañana/el día X a las HORA"
    m_pri = re.search(
        r'(?:cre[oa]r?|pon(?:er)?|a[ñn]ad(?:e|ir)|agenda(?:r)?|apunta(?:r)?)\s+'
        r'(?:el\s+|un\s+|la\s+)?(?:evento|cita|recordatorio|reuni[oó]n)\s+'
        r'(.+?)\s+(hoy|ma[ñn]ana|pasado\s+ma[ñn]ana|el\s+d[ií]a\s+\d+|el\s+\d+|'
        r'el\s+lunes|el\s+martes|el\s+mi[eé]rcoles|el\s+jueves|el\s+viernes|'
        r'el\s+s[aá]bado|el\s+domingo|a\s+las?)\s*(.*)', t)
    if m_pri:
        titulo = m_pri.group(1).strip()
        fecha_str = (m_pri.group(2) + ' ' + m_pri.group(3)).strip()
        # Si el "título" es en realidad parte de la fecha (lunes, día, número...), no hay título real
        _es_fecha = re.match(r'^(el\s+)?(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|'
                             r'domingo|d[ií]a\s+\d+|\d+)$', titulo)
        if titulo and len(titulo) > 1 and not _es_fecha:
            return (titulo, fecha_str)
        elif _es_fecha:
            # Evento sin título, la fecha incluye este texto
            return ("Evento", titulo + ' ' + fecha_str)

    m = re.search(r'(?:recuérdame|recuerdame)\s+(?:que\s+)?(.+)', t)
    if m:
        resto = m.group(1).strip()
        titulo_m = re.sub(
            r'\s+(?:mañana|manana|pasado|el\s+lunes|el\s+martes|el\s+miércoles|el\s+miercoles|'
            r'el\s+jueves|el\s+viernes|el\s+sábado|el\s+sabado|el\s+domingo|'
            r'a\s+las?|en\s+\d+|el\s+d[ií]a|el\s+\d).*', '', resto).strip()
        return (titulo_m or resto, resto)

    m2 = re.search(
        r'(?:cre[oa]r?|pon(?:er)?|agenda(?:r)?|apunta(?:r)?|añade?|añadir)\s+(?:un\s+)?(?:evento|cita|recordatorio|reunión|reunion)'
        r'\s+(?:llamad[ao]\s+|de\s+|sobre\s+)?(.+?)\s+(?:para\s+|el\s+|mañana|en\s+)(.*)', t)
    if m2:
        return (m2.group(1).strip(), m2.group(2).strip() or t)

    # Patrón simple: "evento TITULO el DIA a las HORA"
    m3 = re.search(r'(?:evento|cita|recordatorio)\s+([\w\s]+?)\s+(?:el\s+|mañana|para\s+)(.*)', t)
    if m3:
        titulo = m3.group(1).strip()
        fecha_str = m3.group(2).strip() or t
        # Si el "título" parece una fecha, no es título
        if not re.search(r'\d', titulo) and len(titulo) > 2:
            return (titulo, fecha_str)

    # "crea un evento el DIA a las HORA" sin título explícito
    m4 = re.search(r'(?:cre[oa]r?|pon(?:er)?)\s+(?:un\s+)?(?:evento|cita|recordatorio)\s+(el\s+.+|mañana.+|pasado.+|en\s+\d+.*)', t)
    if m4:
        fecha_str = m4.group(1).strip()
        return ("Evento", fecha_str)

    return None
