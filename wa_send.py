"""
Script auxiliar para enviar WhatsApp - proceso independiente
Uso: python wa_send.py "contacto" "mensaje"
"""
import sys, os, time, subprocess, random

CHROME_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome-win64", "chrome.exe")
CHROMEDRIVER   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver-win64", "chromedriver.exe")
CHROME_PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_profile")

# Añade aquí tus contactos: "nombre": "+34XXXXXXXXX"
CONTACTOS_WA = {
}


def _limpiar_locks():
    """Elimina archivos de bloqueo del perfil."""
    for nombre in ['SingletonLock', 'SingletonSocket', 'SingletonCookie',
                   os.path.join('Default', 'lockfile')]:
        try:
            p = os.path.join(CHROME_PROFILE, nombre)
            if os.path.exists(p):
                os.remove(p)
        except:
            pass


def enviar(contacto, mensaje):
    contacto = contacto.lower().strip()
    numero = CONTACTOS_WA.get(contacto)

    _limpiar_locks()
    time.sleep(0.5)

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    import re

    debug_port = random.randint(9300, 9400)
    opts = Options()
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    opts.add_argument(f"--remote-debugging-port={debug_port}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--window-position=-32000,-32000")
    opts.add_argument("--no-first-run")
    opts.add_argument("--disable-sync")
    opts.add_argument("--disable-extensions")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.binary_location = CHROME_PATH

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=opts)

    try:
        if numero:
            num = re.sub(r'[^\d+]', '', numero)
            driver.get(f"https://web.whatsapp.com/send?phone={num}&text=")
        else:
            driver.get("https://web.whatsapp.com")

        wait = WebDriverWait(driver, 40)
        wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            '[data-testid="conversation-compose-box-input"], [data-testid="qrcode"]'
        )))

        if driver.find_elements(By.CSS_SELECTOR, '[data-testid="qrcode"]'):
            return "Sesión caducada, escanea el QR con test_wa2.py"

        if not numero:
            search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="search"]')))
            search.click()
            time.sleep(0.5)
            inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="search-input"]')))
            inp.send_keys(contacto)
            time.sleep(2)
            res = driver.find_elements(By.CSS_SELECTOR, '[data-testid="cell-frame-container"]')
            if not res:
                return f"No encontré a {contacto}"
            res[0].click()
            time.sleep(1)

        box = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]')))
        box.click()
        time.sleep(0.5)
        box.send_keys(mensaje)
        time.sleep(0.8)
        box.send_keys(Keys.ENTER)

        # Esperar a que el mensaje se ENVÍE de verdad (no solo se escriba)
        # WhatsApp muestra un reloj mientras envía, luego el tic de enviado.
        enviado = False
        for _ in range(20):  # hasta 10 segundos
            time.sleep(0.5)
            # Buscar el icono de "enviado" (tic) en el último mensaje saliente
            ticks = driver.find_elements(By.CSS_SELECTOR,
                '[data-testid="msg-check"], [data-testid="msg-dblcheck"], span[aria-label*="Enviado"], span[aria-label*="Entregado"]')
            if ticks:
                enviado = True
                break
            # Si ya no hay reloj de "pendiente", también vale
            relojes = driver.find_elements(By.CSS_SELECTOR, '[data-testid="msg-time"], [data-icon="msg-time"]')
            if not relojes and _ > 4:
                enviado = True
                break

        # Margen extra de seguridad para que sincronice con el móvil
        time.sleep(3)

        if enviado:
            return f"Mensaje enviado a {contacto}."
        return f"Mensaje enviado a {contacto} (sin confirmación de entrega)."
    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("RESULTADO: Uso incorrecto")
        sys.exit()
    try:
        resultado = enviar(sys.argv[1], sys.argv[2])
        print(f"RESULTADO: {resultado}")
    except Exception as e:
        # Solo la primera línea del error, sin stacktrace
        msg = str(e).split('\n')[0][:100]
        print(f"RESULTADO: Error - {msg}")
