<div align="center">

```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

### Asistente de IA local · Voz + Telegram

`+80 funciones · Python · IA 100% local`

[![Ver demo en YouTube](https://img.shields.io/badge/▶_VER_DEMO-e5534b?style=for-the-badge)](https://youtu.be/T3hwXxf3abs)

</div>

---

## `▸` Qué es

**JARVIS** es un asistente personal de inteligencia artificial que corre **en local**
en tu propio PC, controlable por **voz** y por **Telegram** desde cualquier lugar.
No es un chatbot: ejecuta acciones reales sobre el sistema y tiene más de 80 funciones.

Toda la IA funciona en tu ordenador, sin enviar datos a la nube.

> Este es un proyecto personal que he abierto para que cualquiera pueda montárselo.
> Al arrancar por primera vez, un menú te guía para configurar tus datos.

---

## `▸` Requisitos

- **Windows 10/11**
- **Python 3.10 o superior** → https://www.python.org/downloads/
  (marca "Add Python to PATH" al instalar)
- **Ollama** → https://ollama.com (para la IA)
- **GPU recomendada** con 8GB+ de VRAM si quieres generar imágenes
  (funciona sin GPU, pero sin generación de imágenes)

---

## `▸` Instalación paso a paso

### 1. Descarga el proyecto
```bash
git clone https://github.com/miguelrobles2002/jarvis
cd jarvis
```
(o descarga el ZIP y descomprímelo)

### 2. Instala las dependencias de Python
```bash
pip install -r requirements.txt
```

### 3. Instala Ollama y descarga los modelos
Instala Ollama desde https://ollama.com y luego, en una terminal:
```bash
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
```
Opcional (solo si quieres análisis de imágenes por IA):
```bash
ollama pull llava
```

### 4. Arranca JARVIS
```bash
python jarvis.py
```

**La primera vez**, aparecerá un menú de configuración que te preguntará:
- Tu nombre y ciudad
- Si quieres control por Telegram (te explica cómo conseguir el token)
- Qué modelos de IA usar
- Qué módulos activar (voz, imágenes, correo, etc.)

Todo se guarda en `config.json`. Las siguientes veces, JARVIS arranca directo.

---

## `▸` Configurar Telegram (opcional pero recomendado)

Para controlar JARVIS desde el móvil:

1. En Telegram, busca **@BotFather** y escríbele `/newbot`. Te dará un **token**.
2. Busca **@userinfobot** y escríbele `/start`. Te dará tu **Chat ID**.
3. Mete esos dos datos cuando el menú de JARVIS te los pida.

---

## `▸` Módulos opcionales

Algunos módulos necesitan configuración extra:

| Módulo | Qué necesitas |
|--------|---------------|
| **Voz (F9)** | Piper TTS en una carpeta `piper/` (opcional; funciona sin voz) |
| **Imágenes IA** | GPU con VRAM suficiente + `ollama pull llava` |
| **Gmail / Calendar** | Credenciales de Google Cloud (`credentials.json`) → ejecuta `setup_gmail.py` |
| **WhatsApp** | Chrome + chromedriver en el proyecto |
| **Fútbol** | API key gratuita de https://www.api-football.com |
| **Temperaturas** | LibreHardwareMonitor abierto |

Si no configuras un módulo, JARVIS simplemente no usará esa función. Todo lo demás
funciona igual.

---

## `▸` Reconfigurar

Si quieres cambiar tus datos más adelante:
```bash
python configuracion.py
```

---

## `▸` Qué sabe hacer

```
🎙️  Control por voz (Whisper) y síntesis de voz (Piper)
📱  Control remoto completo por Telegram
🧠  Conversación con IA local (Ollama)
🎨  Generar imágenes (SDXL) y analizar pantalla (LLaVA)
⚙️   Control del sistema: volumen, procesos, hardware, apps
📁  Explorar, buscar, leer y resumir documentos con IA
📬  Gmail, Google Calendar, WhatsApp, notificaciones del móvil
💾  Copias de seguridad de tus carpetas
🧮  Resolver ecuaciones, derivadas, integrales
🎮  Detección de juegos, backups de servidores
🛠️   Alarmas, notas, clima, y mucho más
```

---

## `▸` Seguridad y privacidad

- Tus datos (token, contraseñas, contactos) se guardan **solo en tu PC**, en
  `config.json`, que **nunca** se sube a GitHub (está en `.gitignore`).
- Toda la IA funciona en local: tus conversaciones no salen de tu ordenador.
- Añade tus contactos de teléfono/WhatsApp editando los archivos correspondientes.

---

<div align="center">

Proyecto creado por **Miguel Robles** · Técnico Superior ASIR

[Portfolio ↗](https://robles-it.netlify.app) · [YouTube ↗](https://www.youtube.com/@robles0797) · [LinkedIn ↗](https://www.linkedin.com/in/miguel-robles-medina-8a0315389)

</div>
