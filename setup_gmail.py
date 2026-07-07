"""
Re-autoriza Google añadiendo permiso de lectura de Gmail.
Ejecutar UNA VEZ. Borra el token viejo y crea uno nuevo con Gmail + Calendar.
"""
from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Scopes: Calendar (ya lo tenías) + Gmail lectura
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
]
CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
TOKEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')

# Borrar token viejo para forzar re-autorización con nuevos permisos
if os.path.exists(TOKEN):
    os.remove(TOKEN)
    print("Token viejo eliminado.")

print("Se abrirá el navegador. Acepta los permisos de Calendar Y Gmail.")
print()

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN, 'w') as f:
    f.write(creds.to_json())

print(f"Listo. Token con Gmail + Calendar guardado en {TOKEN}")
