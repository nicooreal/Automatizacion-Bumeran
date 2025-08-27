# bumeran_brave.py — Brave + Selenium • Selenium Manager + fallback • cookies + scroll + filtros + validaciones + debug
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import os, time, random, urllib.parse, re
from urllib.parse import urlparse, urlunparse

# ==================== CONFIG ====================
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

SCRIPT_DIR = os.path.dirname(__file__)
PROFILE_DIR = os.path.join(SCRIPT_DIR, "brave_profile")   # perfil dedicado (no toca tu Brave personal)
os.makedirs(PROFILE_DIR, exist_ok=True)

PALABRAS = ["Soporte Técnico", "programador","oficina","desarrollador", "Administrativo", "IT"]
CIUDAD = "Buenos Aires"
PAGINAS_MAX = 3
MAX_POR_PALABRA = 3
MAX_TOTAL = 20
REVIEW_MODE = False
KEEP_OPEN_AFTER_RUN = True

# ==================== UTILS ====================
def human_sleep(a=1.2, b=3.0):
    time.sleep(random.uniform(a, b))

def normalize_url(u: str) -> str:
    p = urlparse(u or "")
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))

def candidate_result_urls(keyword: str, city: str):
    # Varias rutas según sesión/geo
    q = urllib.parse.quote(keyword)
    l = urllib.parse.quote(city)
    return [
        f"https://www.bumeran.com.ar/empleos/?q={q}&l={l}",
        f"https://www.bumeran.com.ar/empleos/?q={q}",
        f"https://www.bumeran.com.ar/empleos/buenos-aires/?q={q}",
        "https://www.bumeran.com.ar/empleos/buenos-aires/",
        "https://www.bumeran.com.ar/empleos/",
    ]

def click_cookies_si_aparece(timeout=5):
    """Cierra banners de cookies para no bloquear inputs/botones."""
    fin = time.time() + timeout
    posibles = [
        "//button[contains(., 'Aceptar')]", "//button[contains(., 'Acepto')]",
        "//button[contains(., 'Aceptar y cerrar')]", "//button[contains(., 'Aceptar todas')]",
        "//button[contains(., 'Entendido')]", "//a[contains(., 'Aceptar')]",
    ]
    while time.time() < fin:
        for xp in posibles:
            try:
                btn = driver.find_element(By.XPATH, xp)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    return True
            except:
                pass
        time.sleep(0.3)
    return False

# ==================== BROWSER ====================
def make_chrome_options():
    opts = webdriver.ChromeOptions()
    opts.binary_location = BRAVE_PATH
    opts.add_argument("--start-maximized")
    opts.add_argument(fr"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--profile-directory=Default")
    # estabilidad
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--test-type")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--remote-debugging-port=0")
    return opts

def start_browser():
    options = make_chrome_options()
    try:
        drv = webdriver.Chrome(options=options)  # Selenium Manager
        wait = WebDriverWait(drv, 15)
        return drv, wait
    except Exception as e:
        print(f"⚠️ Selenium Manager falló:\n{e}\n↪️ Intento fallback con chromedriver.exe local…")
        local_driver = os.path.join(SCRIPT_DIR, "chromedriver.exe")
        if not os.path.exists(local_driver):
            raise RuntimeError("No se encontró chromedriver.exe para el fallback.") from e
        service = Service(local_driver)
        drv = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(drv, 15)
        return drv, wait

driver, wait = start_browser()

# ==================== FLOWS ====================
def login_si_falta():
    driver.get("https://www.bumeran.com.ar/")
    human_sleep()
    try: wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except: pass
    click_cookies_si_aparece()
    page = driver.page_source
    if ("Ingresar" in page) or ("Iniciar sesión" in page):
        print("👉 Iniciá sesión en Bumeran en la ventana de Brave. Cuando termines, presioná Enter acá.")
        try: input()
        except KeyboardInterrupt: pass

def ir_home_y_buscar(keyword: str, city: str) -> bool:
    """Intento por la home (no indispensable). Si falla, devolvemos False para plan B."""
    try:
        driver.get("https://www.bumeran.com.ar/")
        human_sleep()
        click_cookies_si_aparece()

        sb = None; lb = None
        for sel in [
            "input[placeholder*='Puesto']","input[aria-label*='Puesto']",
            "input[placeholder*='palabra clave']","input[aria-label*='palabra']",
            "input[type='search']",
        ]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems: sb = elems[0]; break
        for sel in [
            "input[placeholder*='Lugar']","input[aria-label*='Lugar']",
            "input[placeholder*='trabajo']","input[aria-label*='trabajo']",
        ]:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems: lb = elems[0]; break

        if not sb or not lb:
            header = driver.find_element(By.CSS_SELECTOR, "header, div[class*='header']")
            inputs = [e for e in header.find_elements(By.CSS_SELECTOR, "input") if e.is_displayed()]
            if len(inputs) >= 2:
                sb = sb or inputs[0]; lb = lb or inputs[1]
        if not sb or not lb:
            return False

        sb.click(); sb.clear(); sb.send_keys(keyword); human_sleep(0.2, 0.6)
        lb.click(); lb.clear(); lb.send_keys(city)

        for sel in ["//button[contains(., 'Buscar trabajo')]","//button[contains(., 'Buscar')]", "button[type='submit']"]:
            try:
                btn = driver.find_element(By.XPATH, sel) if sel.startswith("//") else driver.find_element(By.CSS_SELECTOR, sel)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                human_sleep(0.2, 0.6); btn.click(); break
            except: continue
        human_sleep()
        return True
    except:
        return False

def abrir_resultados(keyword: str, city: str):
    # Plan B primero: probar múltiples URLs de resultados
    urls = candidate_result_urls(keyword, city)
    for u in urls:
        driver.get(u)
        click_cookies_si_aparece()
        # scroll suave para disparar carga
        for _ in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.6)
        found = driver.find_elements(By.CSS_SELECTOR, "a[href*='/empleos/'], a[href*='/trabajo/'], a[href*='/oferta/']")
        print(f"   • Intento en {u} → {len(found)} anchors potenciales")
        if len(found) >= 10:
            return
    # Si ninguna cargó, probamos home
    if ir_home_y_buscar(keyword, city):
        click_cookies_si_aparece()
        time.sleep(1.0)

# -------- Recolección y validaciones --------
AVISO_PATTERNS = [
    re.compile(r"/empleos/[^/]+/\d+"),    # /empleos/slug/12345
    re.compile(r"/empleos/[^/]+"),        # /empleos/slug
    re.compile(r"/oferta/[^/]+/\d+"),     # /oferta/slug/12345
    re.compile(r"/trabajo/[^/]+/\d+"),    # /trabajo/slug/12345
]
BAD_SUBSTR = (
    "/empresa/", "/perfil-empresa", "/postulantes/", "/salarios",
    "/jovenes-profesionales", "/puestos-ejecutivos", "/login", "/registro",
    "/terminos", "/privacidad", "/faq", "/ayuda", "/blog", "/articulo",
    "/curriculum", "/orientacion-laboral"
)

def es_url_aviso(href: str) -> bool:
    if not href or "bumeran.com.ar" not in href:
        return False
    if any(b in href for b in BAD_SUBSTR):
        return False
    path = urlparse(href).path
    return any(p.search(path) for p in AVISO_PATTERNS)

def recolectar_urls(paginas_max=3):
    urls = set()
    for _ in range(paginas_max):
        # scroll para cargar más resultados
        for _s in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.7)

        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        for a in anchors:
            href = (a.get_attribute("href") or "").strip()
            if es_url_aviso(href):
                urls.add(normalize_url(href))

        # ir a siguiente página si existe
        avanzo = False
        for xp in ["//a[@rel='next']", "//a[contains(., 'Siguiente')]", "//a[contains(., 'Next')]"]:
            try:
                nxt = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
                time.sleep(0.4); nxt.click()
                avanzo = True
                time.sleep(1.0)
                break
            except:
                continue
        if not avanzo:
            break
    return list(urls)

def es_404_o_no_disponible(html: str) -> bool:
    """Marca 404 solo ante mensajes reales de error, no por '404' suelto en assets/scripts."""
    if not html:
        return True
    txt = " ".join(html.lower().split())  # normaliza espacios
    needles = [
        "no encontramos lo que buscás",
        "este aviso ya no se encuentra activo",
        "aviso no disponible",
        "página no encontrada",
        "page not found",
        "error 404",            # forma explícita
        ">404<",                # 404 en contenido visible, no en urls
    ]
    return any(n in txt for n in needles)


def tiene_boton_postulacion_visible() -> bool:
    try:
        for by, sel in [
            (By.XPATH, "//button[contains(., 'Postularme') or contains(., 'Postulación rápida')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//a[contains(., 'Postularme')]"),
        ]:
            elems = driver.find_elements(by, sel)
            if any(e.is_displayed() for e in elems):
                return True
    except:
        pass
    return False

def tiene_titulo_visible() -> bool:
    """True si hay un título visible en el detalle (no dependemos de <h1>)."""
    posibles = ["h1", "h2", "h3", "div[class*='title']", "div[class*='job']"]
    for sel in posibles:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed() and el.text.strip():
                return True
        except:
            continue
    # fallback: usar <title> del head
    try:
        return bool(driver.title.strip())
    except:
        return False

def extraer_titulo_empresa():
    titulo=empresa=""
    try: titulo = driver.title.strip()
    except: pass
    try:
        empresa_el = driver.find_element(By.XPATH, "//a[contains(@href, '/perfil-empresa') or contains(@href, '/empresa/')]")
        empresa = empresa_el.text.strip()
    except: pass
    return titulo, empresa

def intentar_postulacion(url: str) -> bool:
    driver.get(url)
    human_sleep()
    html = driver.page_source
    current = driver.current_url
    title = ""
    try: title = driver.title
    except: pass
    print(f"    → Abierto: {current} | title: {title}")

    # 404 / caído
    if es_404_o_no_disponible(html):
        print("  ↪️ Salteada (404/no disponible).")
        return False

    # si no vemos título visible, seguimos igual si tiene botón
    if not tiene_titulo_visible():
        print("  ⚠️ Aviso sin título reconocible, intento igual.")

    # filtro geográfico laxo
    if ("Buenos Aires" not in html) and ("CABA" not in html) and ("Capital Federal" not in html):
        print("  ↪️ Salteada (fuera de Buenos Aires).")
        return False

    # sin botón de postulación visible → salteamos
    if not tiene_boton_postulacion_visible():
        print("  ↪️ Salteada (sin botón de postulación visible).")
        return False

    if REVIEW_MODE:
        titulo, empresa = extraer_titulo_empresa()
        print(f"📝 Revisar: {titulo or 'Aviso'} @ {empresa or ''}\n    {url}")
        if input("¿Enviar esta postulación? [S/n] ").strip().lower() == "n":
            return False

    # Click en botón de postulación
    selectores = [
        (By.XPATH, "//button[contains(., 'Postularme') or contains(., 'Postulación rápida')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//a[contains(., 'Postularme')]"),
    ]
    clicked = False
    for by, sel in selectores:
        try:
            btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            human_sleep(0.5, 1.0)
            btn.click()
            clicked = True
            break
        except:
            continue

    titulo, empresa = extraer_titulo_empresa()
    if not clicked:
        print(f"  ⚠️ Sin botón claro de postulación. ({titulo or url})")
        return False

    # Confirmaciones/modales simples
    for by, sel in [
        (By.XPATH, "//button[contains(., 'Confirmar') or contains(., 'Enviar')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ]:
        try:
            btn2 = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
            human_sleep(0.6, 1.3)
            btn2.click()
            break
        except:
            pass

    print(f"  ✅ Postulación enviada — {titulo} @ {empresa}")
    return True

# ==================== MAIN ====================
def main():
    print("🔎 Iniciando…")
    login_si_falta()
    total = 0

    for kw in PALABRAS:
        if total >= MAX_TOTAL: break
        print(f"\n🔹 Buscando: {kw} en {CIUDAD}")
        abrir_resultados(kw, CIUDAD)
        urls = recolectar_urls(PAGINAS_MAX)
        print(f"   ↳ {len(urls)} avisos detectados")
        random.shuffle(urls)

        enviados_kw = 0
        vistos = set()
        empties = 0
        for u in urls:
            if enviados_kw >= MAX_POR_PALABRA or total >= MAX_TOTAL: break
            if u in vistos: continue
            vistos.add(u)
            print(f"📌 {kw} → {u}")
            ok = intentar_postulacion(u)
            if ok:
                enviados_kw += 1; total += 1; empties = 0
            else:
                empties += 1
                if empties >= 5:
                    print("⛔ Demasiados avisos inválidos seguidos. Paso a la siguiente keyword.")
                    break
            human_sleep()

    print(f"\n🎉 Listo. Postulaciones realizadas: {total}")

if __name__ == "__main__":
    try:
        main()
        if KEEP_OPEN_AFTER_RUN:
            print("\n🔒 Dejo Brave abierto para revisar. Presioná Enter acá para cerrar…")
            try: input()
            except KeyboardInterrupt: pass
    finally:
        try: driver.quit()
        except: pass
