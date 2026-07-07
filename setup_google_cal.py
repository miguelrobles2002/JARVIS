"""
Script de autorización de Google Calendar - ejecutar UNA VEZ
Genera token.json que JARVIS usa para crear eventos
"""
from google_auth_oauthlib.flow import InstalledAppFlow
import json, os

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
TOKEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')

print("Iniciando autorización de Google Calendar...")
print("Se abrirá una ventana del navegador.")
print("Inicia sesión con tu cuenta de Google y acepta los permisos.")
print()

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN, 'w') as f:
    f.write(creds.to_json())

print(f"Autorización completada. Token guardado en {TOKEN}")
print("JARVIS ya puede crear eventos en tu Google Calendar.")
