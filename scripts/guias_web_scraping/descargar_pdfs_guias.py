# -*- coding: utf-8 -*-
"""
Script para descargar PDFs de Guías de Remisión usando Web Scraping (Navegación Visual)
ESTRATEGIA VISUAL AUTOMATIZADA:
1. Usa XML-RPC para obtener la lista de IDs (para saber qué descargar)
2. Usa Selenium para loguearse
3. Navega DIRECTAMENTE a la ficha de cada guía (visual)
4. Hace CLIC en el botón "Imprimir" y luego en "e-Guía de Remisión AGR"
5. Gestiona la descarga y renombra el archivo

Autor: GitHub Proyectos AGV
"""

import os
import sys
import time
import shutil
import xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv
from calendar import monthrange

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configurar encoding para Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================================================
# CONFIGURACIÓN DE AMBIENTE
# ============================================================================
AMBIENTE = "desarrollo"

# Buscar .env en la raíz del proyecto
project_root = Path(__file__).parent.parent.parent
env_file = f'.env.{AMBIENTE}'
env_path = project_root / env_file

if not env_path.exists():
    # Intentar buscar en directorios padres
    parent_dirs = [Path(__file__).parent.parent, project_root]
    for parent_dir in parent_dirs:
        test_env = parent_dir / env_file
        if test_env.exists():
            env_path = test_env
            break

if not env_path.exists():
    print(f"❌ Error: No se encontró el archivo '{env_file}'")
    exit(1)

print(f"📁 Cargando configuración desde: {env_path} (Ambiente: {AMBIENTE})")
load_dotenv(env_path, override=True)

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# Configuración de Fechas
AÑO = 2025
MES = 10

ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"

# Ruta de descarga final
BASE_PATH = project_root / "Prueba_Octubre" / "09_Guias_Remision_V2" / "pdf"
# Carpeta temporal para descargas de Chrome
DOWNLOAD_DIR = project_root / "temp_downloads"

# Crear carpetas
BASE_PATH.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FUNCIONES
# ============================================================================

def conectar_xmlrpc():
    """Conectar por XML-RPC solo para obtener la lista de guías a procesar"""
    print(f"📡 Conectando por XML-RPC para listar guías del {FECHA_INICIO} al {FECHA_FIN}...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    domain = [
        ('picking_type_id', '=', 2),  # Guías de salida
        ('state', '=', 'done'),
        ('date_done', '>=', f'{FECHA_INICIO} 00:00:00'),
        ('date_done', '<=', f'{FECHA_FIN} 23:59:59'),
        ('l10n_latam_document_number', '!=', False)
    ]
    
    ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.picking', 'search', [domain])
    print(f"✅ Encontradas {len(ids)} guías para procesar.")
    
    guias = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.picking', 'read', [ids], 
                            {'fields': ['id', 'name', 'l10n_latam_document_number']})
    return guias

def iniciar_selenium():
    """Inicia Chrome configurado para descargar automáticamente"""
    print("\n🚀 Iniciando navegador Chrome...")
    
    os.environ['WDM_SSL_VERIFY'] = '0'
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--ignore-certificate-errors")
    
    # Configurar preferencias de descarga
    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # Para que no abra el PDF en el visor, sino que lo descargue
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
    except:
        service = Service()
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_odoo(driver):
    """Login visual en Odoo"""
    print("🔐 Iniciando sesión en Odoo...")
    driver.get(f"{ODOO_URL}/web/login")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "login")))
        driver.find_element(By.NAME, "login").send_keys(ODOO_USER)
        driver.find_element(By.NAME, "password").send_keys(ODOO_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Esperar a que cargue el dashboard
        WebDriverWait(driver, 20).until(EC.url_contains("/web"))
        print("✅ Login exitoso.")
        time.sleep(2) # Espera prudencial
        return True
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

def esperar_nueva_descarga(carpeta_descargas, tiempo_espera=15):
    """Espera a que aparezca un nuevo archivo en la carpeta de descargas"""
    tiempo_inicio = time.time()
    archivos_iniciales = set(os.listdir(carpeta_descargas))
    
    while time.time() - tiempo_inicio < tiempo_espera:
        archivos_actuales = set(os.listdir(carpeta_descargas))
        nuevos_archivos = archivos_actuales - archivos_iniciales
        
        for archivo in nuevos_archivos:
            if not archivo.endswith('.crdownload') and not archivo.endswith('.tmp'):
                return archivo
        time.sleep(0.5)
    return None

def procesar_guias_visual(driver, guias):
    """Navega a cada guía y hace clic en Imprimir"""
    print("\n🖱️  Iniciando descarga VISUAL (haciendo clics)...")
    
    total = len(guias)
    descargados = 0
    errores = 0
    
    for idx, guia in enumerate(guias, 1):
        doc_number = guia['l10n_latam_document_number']
        nombre_final = f"{doc_number}.pdf"
        ruta_final = BASE_PATH / nombre_final
        
        if ruta_final.exists():
            print(f"[{idx}/{total}] ⏭️  Ya existe: {nombre_final}")
            continue
            
        print(f"[{idx}/{total}] 📄 Procesando: {doc_number} ...", end="")
        
        try:
            # 1. Navegar DIRECTAMENTE a la ficha de la guía
            url_ficha = f"{ODOO_URL}/web#id={guia['id']}&model=stock.picking&view_type=form"
            driver.get(url_ficha)
            driver.refresh() # Forzar recarga para asegurar limpieza de DOM
            
            wait = WebDriverWait(driver, 15)

            # 2. Esperar a que el título de la página o breadcrumb contenga el número de guía
            # Esto confirma que cargó la guía correcta y no se quedó en la anterior
            try:
                wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), doc_number))
            except:
                pass # Si no lo encuentra en el body, seguimos intentando (a veces está en input)

            # 3. Esperar que cargue el botón "Imprimir"
            # Selector ESPECÍFICO basado en el HTML proporcionado por el usuario
            
            # Intentar encontrar el botón desplegable que contiene el span "Imprimir"
            try:
                # Opción A: Clic en el span directo
                boton_imprimir = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'o_dropdown_title') and contains(text(), 'Imprimir')]")))
                time.sleep(1) # Pequeña pausa para estabilidad
                boton_imprimir.click()
            except:
                # Opción B: Clic en el botón padre del span
                boton_imprimir = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Imprimir')]]")))
                time.sleep(1)
                boton_imprimir.click()
            
            # 4. Esperar y hacer clic en "e-Guía de Remisión AGR"
            opcion_agr = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'e-Guía de Remisión AGR')]")))
            opcion_agr.click()
            
            # 5. Esperar descarga
            archivo_descargado = esperar_nueva_descarga(DOWNLOAD_DIR)
            
            if archivo_descargado:
                # Mover y renombrar
                origen = DOWNLOAD_DIR / archivo_descargado
                shutil.move(str(origen), str(ruta_final))
                print(" ✅ Descargado")
                descargados += 1
            else:
                print(" ❌ No se detectó descarga")
                errores += 1
                
        except Exception as e:
            print(f" ❌ Error: {str(e)[:100]}")
            errores += 1
            # Intentar recuperar navegador si se colgó
            try:
                driver.get("about:blank")
            except:
                pass
        
        # Pausa para no saturar
        time.sleep(1)
        
    print(f"\n📊 Resumen: {descargados} descargados, {errores} errores.")
    
    # Limpiar carpeta temporal
    try:
        os.rmdir(DOWNLOAD_DIR)
    except:
        pass

def main():
    # 1. Obtener lista de guías
    guias = conectar_xmlrpc()
    if not guias:
        print("No hay guías para descargar.")
        return

    # 2. Iniciar Selenium
    driver = iniciar_selenium()
    
    try:
        # 3. Login
        if login_odoo(driver):
            # 4. Procesar visualmente
            procesar_guias_visual(driver, guias)
    finally:
        print("👋 Cerrando navegador...")
        driver.quit()

if __name__ == "__main__":
    main()
