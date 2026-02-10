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
# SISTEMA DE BLOQUEO ATÓMICO (Para ejecución en paralelo)
# ============================================================================

def obtener_bloqueo_archivo(ruta_archivo, timeout=2):
    """
    Intenta obtener un bloqueo exclusivo sobre un archivo .lock para evitar 
    que múltiples procesos descarguen el mismo documento simultáneamente.
    """
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if sys.platform == 'win32':
                # En Windows, usar msvcrt para bloqueo atómico
                lock_file = open(lock_file_path, 'xb')
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                # En Linux/Mac, usar fcntl
                lock_file = open(lock_file_path, 'x')
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except (FileExistsError, IOError, OSError):
            # El archivo ya existe o está bloqueado por otro proceso
            time.sleep(0.1)
            continue
    return None

def liberar_bloqueo_archivo(lock_file, ruta_archivo):
    """Libera el bloqueo de archivo y elimina el archivo .lock"""
    if lock_file:
        try:
            lock_file.close()
        except:
            pass
    
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    try:
        if lock_file_path.exists():
            os.remove(lock_file_path)
    except:
        pass

def verificar_y_reservar_descarga(ruta_final):
    """
    Verificación atómica: si el archivo no existe, intenta reservarlo con un .lock
    Retorna (puede_descargar, lock_file)
    """
    if ruta_final.exists():
        return False, None
    
    lock_file = obtener_bloqueo_archivo(ruta_final)
    if lock_file is None:
        return False, None
    
    # Verificar de nuevo tras obtener el bloqueo por si acaso terminó justo antes
    if ruta_final.exists():
        liberar_bloqueo_archivo(lock_file, ruta_final)
        return False, None
        
    return True, lock_file

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
# LÓGICA DE SELENIUM (PDF - MÉTODO URL DIRECTA)
# ============================================================================

def setup_browser(download_dir):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    prefs = {
        "download.default_directory": str(download_dir.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    os.environ['WDM_SSL_VERIFY'] = '0'
    
    try:
        service = Service(ChromeDriverManager().install())
    except:
        service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_odoo_web(driver, url, db, user, password):
    driver.get(f"{url}/web/login")
    try:
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "login"))).send_keys(user)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "o_main_navbar")))
        return True
    except:
        return False

def descargar_pdf_guia_url_directa(driver, guia_id, numero_doc, final_path, temp_download_dir):
    """
    Descarga el PDF navegando directamente a la URL del reporte de Odoo.
    Esto es mucho más rápido y estable que interactuar con los botones de la interfaz.
    """
    # Limpiar carpeta temporal antes de cada descarga
    for f in glob.glob(str(temp_download_dir / "*")):
        try:
            os.remove(f)
        except:
            pass
    
    # Nombre técnico del reporte de guías en Odoo
    report_name = "agr_shiping_guide.report_edi_gre"
    url_reporte = f"{ODOO_URL}/report/pdf/{report_name}/{guia_id}"
    
    driver.get(url_reporte)
    
    # Esperar a que el archivo aparezca en la carpeta temporal
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = list(temp_download_dir.glob("*.pdf"))
        if files:
            # Verificar que el archivo no esté vacío y que no sea un archivo temporal de Chrome
            if os.path.getsize(files[0]) > 1000:
                nombre_final = numero_doc.replace('/', '-').replace('\\', '-') + ".pdf"
                shutil.move(str(files[0]), str(final_path / nombre_final))
                return True
        time.sleep(0.5)
    
    return False
