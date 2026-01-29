import os
import sys
import time
import base64
import zipfile
import io
import shutil
import glob
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Importar configuración y cliente de Odoo
from core.config import ODOO_DB, ODOO_PASSWORD, ODOO_URL, get_base_path, MAPEO_CARPETAS, PROJECT_ROOT
from core.odoo_client import conectar_odoo

# Importaciones para ejecución simultánea segura
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

# ============================================================================
# LÓGICA DE XML-RPC (XML / CDR)
# ============================================================================

def buscar_adjuntos_guia(uid, models, picking_id):
    try:
        return models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[('res_model', '=', 'stock.picking'), ('res_id', '=', picking_id)]],
            {'fields': ['id', 'name', 'datas', 'mimetype', 'description']}
        )
    except:
        return []

def clasificar_archivo_guia(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if nombre_lower.endswith('.pdf'): return 'pdf'
    elif nombre_lower.endswith('.zip'): return 'zip'
    elif nombre_lower.endswith('.xml'):
        if 'cdr' in nombre_lower or 'constancia' in nombre_lower: return 'cdr'
        return 'xml'
    elif 'cdr' in nombre_lower: return 'cdr'
    return None

def descargar_xml_cdr_guia(uid, models, guia, base_path_guia):
    guia_id = guia['id']
    numero_doc = guia.get('l10n_latam_document_number', f"GUIA_{guia_id}")
    nombre_base = numero_doc.replace('/', '-').replace('\\', '-')
    
    adjuntos = buscar_adjuntos_guia(uid, models, guia_id)
    stats = {'xml': 0, 'cdr': 0}
    
    for adj in adjuntos:
        nombre_archivo = adj.get('name', '')
        datas = adj.get('datas')
        if not datas: continue
        
        try:
            tipo = clasificar_archivo_guia(nombre_archivo)
            if not tipo or tipo == 'pdf': continue
            
            if tipo == 'zip':
                contenido = base64.b64decode(datas)
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for filename in z.namelist():
                        tipo_int = clasificar_archivo_guia(filename)
                        if tipo_int and tipo_int in ['xml', 'cdr']:
                            ruta = base_path_guia / tipo_int / f"{nombre_base}.xml"
                            if ruta.exists():
                                stats[tipo_int] += 1
                                continue
                                
                            ruta.parent.mkdir(parents=True, exist_ok=True)
                            with open(ruta, 'wb') as f:
                                f.write(z.read(filename))
                            stats[tipo_int] += 1
            else:
                ruta = base_path_guia / tipo / f"{nombre_base}.xml"
                if ruta.exists():
                    stats[tipo] += 1
                    continue
                    
                contenido = base64.b64decode(datas)
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with open(ruta, 'wb') as f:
                    f.write(contenido)
                stats[tipo] += 1
        except:
            pass
    return stats

# ============================================================================
# LÓGICA DE SELENIUM (PDF)
# ============================================================================

def setup_browser(download_dir):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Opcional
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Desactivar verificación SSL para la descarga del driver (solución para redes corporativas)
    os.environ['WDM_SSL_VERIFY'] = '0'
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_odoo_web(driver, url, db, user, password):
    driver.get(f"{url}/web/login")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login")))
        driver.find_element(By.ID, "login").send_keys(user)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "o_main_navbar")))
        return True
    except:
        return False

def descargar_pdf_guia_selenium(driver, guia_id, numero_doc, final_path, temp_download_dir):
    # Limpiar carpeta temporal antes
    for f in glob.glob(str(temp_download_dir / "*")): os.remove(f)
    
    url_guia = f"{ODOO_URL}/web#id={guia_id}&model=stock.picking&view_type=form"
    driver.get(url_guia)
    
    try:
        # Esperar a que cargue el botón de imprimir
        wait = WebDriverWait(driver, 15)
        btn_imprimir = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Imprimir')]")))
        btn_imprimir.click()
        
        # Click en e-Guía AGR (ajustar según el texto exacto del botón)
        btn_eguia = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'e-Guía AGR')]")))
        btn_eguia.click()
        
        # Esperar a la descarga
        timeout = 20
        start_time = time.time()
        while time.time() - start_time < timeout:
            files = list(temp_download_dir.glob("*.pdf"))
            if files:
                # Mover al destino final
                nombre_final = numero_doc.replace('/', '-').replace('\\', '-') + ".pdf"
                shutil.move(str(files[0]), str(final_path / nombre_final))
                return True
            time.sleep(1)
    except Exception as e:
        print(f"❌ Error descargando PDF para {numero_doc}: {e}")
    
    return False
