"""
Módulo WhatsApp Web para JARVIS
Envía mensajes usando Selenium con Chrome (sesión guardada en wa_profile)
"""
import re, time, os

# Añade aquí tus contactos: "nombre": "+34XXXXXXXXX"
# Ejemplo:
#   "mama": "+34600000000",
#   "juan": "+34611111111",
CONTACTOS_WA = {
}

CHROME_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome-win64", "chrome.exe")
CHROMEDRIVER   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver-win64", "chromedriver.exe")
CHROME_PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_profile")


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--window-position=-32000,-32000")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-sync")
    opts.add_argument("--disable-extensions")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.binary_location = CHROME_PATH

    return webdriver.Chrome(service=Service(CHROMEDRIVER), options=opts)


def enviar_whatsapp_subprocess(contacto, mensaje):
    """Ejecuta wa_send.py como proceso independiente."""
    import subprocess, sys
    wa_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_send.py")
    result = subprocess.run(
        [sys.executable, wa_script, contacto, mensaje],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True, timeout=90,
        creationflags=0x08000000
    )
    out = result.stdout.strip()
    lineas = [l for l in out.split("\n")
              if l and not l.startswith("[") and "DevTools" not in l
              and "CONSOLE" not in l and "ERROR" not in l]
    return lineas[-1] if lineas else f"Mensaje enviado a {contacto}."


def enviar_whatsapp(contacto, mensaje):
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
    except ImportError:
        return "Instala selenium: pip install selenium"

    contacto_lower = contacto.lower().strip()
    numero = CONTACTOS_WA.get(contacto_lower)

    driver = None
    try:
        driver = _make_driver()
        

        if numero:
            numero_limpio = re.sub(r'[^\d+]', '', numero)
            url = f"https://web.whatsapp.com/send?phone={numero_limpio}&text="
        else:
            url = "https://web.whatsapp.com"

        driver.get(url)
        wait = WebDriverWait(driver, 40)

        try:
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                '[data-testid="conversation-compose-box-input"], [data-testid="qrcode"]'
            )))
        except:
            return "WhatsApp Web tardó demasiado. Comprueba la conexión o ejecuta test_wa2.py de nuevo."

        qr = driver.find_elements(By.CSS_SELECTOR, '[data-testid="qrcode"]')
        if qr:
            return "Sesión caducada. Ejecuta test_wa2.py para escanear el QR de nuevo."

        if not numero:
            search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="search"]')))
            search.click()
            time.sleep(0.5)
            inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="search-input"]')))
            inp.send_keys(contacto)
            time.sleep(2)
            resultados = driver.find_elements(By.CSS_SELECTOR, '[data-testid="cell-frame-container"]')
            if not resultados:
                return f"No encontré a {contacto} en WhatsApp."
            resultados[0].click()
            time.sleep(1)

        msg_box = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]'
        )))
        msg_box.click()
        time.sleep(0.3)
        msg_box.send_keys(mensaje)
        time.sleep(0.5)
        msg_box.send_keys(Keys.ENTER)
        time.sleep(1)

        return f"Mensaje enviado a {contacto}."

    except Exception as e:
        return f"Error al enviar WhatsApp: {e}"
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def detectar_whatsapp(texto):
    # Limpiar puntuación y normalizar
    t = texto.lower().strip()
    # Quitar puntos y comas sueltos que Whisper añade
    t = re.sub(r'[.,]\s+', ' ', t).strip()

    # Palabras clave de WhatsApp
    WA_WORDS = ['wasap', 'whatsapp', 'wasa', 'guasap', 'wassap']
    if not any(w in t for w in WA_WORDS):
        return None

    # Extraer contacto y mensaje con múltiples estrategias
    patrones = [
        # "manda un wasap a CONTACTO diciendo/que MENSAJE"
        r'(?:manda?|envía?|envia?|escribe?|di(?:le)?)\s+(?:un\s+)?(?:wasap|whatsapp|wasa|guasap|wassap)\s+a\s+(.+?)\s+(?:diciendo?|que|con el mensaje|con mensaje|:)\s+(.+)',
        # "manda un wasap a CONTACTO MENSAJE" (sin "que")
        r'(?:manda?|envía?|envia?)\s+(?:un\s+)?(?:wasap|whatsapp|wasa|guasap|wassap)\s+a\s+(\w+)[,\s]+(?!que)(.+)',
        # "dile por wasap a CONTACTO que MENSAJE"
        r'(?:dile?)\s+(?:por\s+(?:wasap|whatsapp|wasa|guasap|wassap)\s+)?a\s+(.+?)\s+(?:que|:)\s+(.+)',
        # "wasap/whatsapp a CONTACTO: MENSAJE"
        r'(?:wasap|whatsapp|wasa|guasap|wassap)\s+a\s+(.+?)[,:\s]+(.+)',
        # "manda wasap CONTACTO MENSAJE" (sin "a")
        r'(?:manda?|envía?|envia?)\s+(?:un\s+)?(?:wasap|whatsapp|wasa|guasap|wassap)\s+(\w+)[,\s]+(?!que)(.+)',
    ]

    CONTACTOS_CONOCIDOS = list(CONTACTOS_WA.keys())

    for patron in patrones:
        m = re.search(patron, t)
        if m:
            contacto = m.group(1).strip().rstrip('.,;:')
            mensaje  = m.group(2).strip().rstrip('.,;:')
            if contacto and mensaje and len(mensaje) > 1:
                return (contacto, mensaje)

    # Último recurso: si hay palabra WA + contacto conocido en el texto
    for w in WA_WORDS:
        if w in t:
            for c in CONTACTOS_CONOCIDOS:
                if c in t:
                    # Extraer el mensaje como todo lo que va después del contacto
                    idx = t.find(c) + len(c)
                    resto = t[idx:].strip().lstrip('.,;: ')
                    # Quitar "que" inicial
                    resto = re.sub(r'^que\s+', '', resto)
                    if resto and len(resto) > 2:
                        return (c, resto)
    return None
