# -*- coding: utf-8 -*-
"""
Script para descargar PDFs de Guías de Remisión - VERSIÓN VISUAL OPTIMIZADA
ESTRATEGIA:
1. XML-RPC: Obtener lista de guías (rápido)
2. Selenium: Navegar a cada ficha y hacer clic en Imprimir > e-Guía AGR
3. Optimizaciones: Esperas mínimas, sin recargas innecesarias, gestión rápida de archivos

Tiempo estimado: ~3 segundos por guía = 1000 guías en 50 minutos
Autor: GitHub Proyectos AGV
"""

import os
import sys
import time
import shutil
import glob
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
DOWNLOAD_DIR = project_root / "temp_downloads"

BASE_PATH.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Reporte técnico (route) para e-Guía AGR en Odoo
REPORTE_NAME = "agr_shiping_guide.report_edi_gre"

# ============================================================================
# FUNCIONES
# ============================================================================

def conectar_xmlrpc():
    """Conectar por XML-RPC para listar guías"""
    print(f"📡 Conectando por XML-RPC para listar guías del {FECHA_INICIO} al {FECHA_FIN}...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    domain = [
        ('picking_type_id', '=', 2),
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
    """Inicia Chrome optimizado"""
    print("\n🚀 Iniciando navegador Chrome...")
    
    os.environ['WDM_SSL_VERIFY'] = '0'
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Evitar detección
    
    # Configurar descargas automáticas
    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
    except:
        service = Service()
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_odoo(driver):
    """Login en Odoo"""
    print("🔐 Iniciando sesión en Odoo...")
    driver.get(f"{ODOO_URL}/web/login")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "login")))
        driver.find_element(By.NAME, "login").send_keys(ODOO_USER)
        driver.find_element(By.NAME, "password").send_keys(ODOO_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        WebDriverWait(driver, 15).until(EC.url_contains("/web"))
        print("✅ Login exitoso.")
        time.sleep(1)  # Espera mínima
        return True
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

def esperar_descarga_rapida(timeout=8):
    """Espera a que aparezca un archivo PDF en la carpeta de descargas"""
    start_time = time.time()
    archivos_iniciales = set(os.listdir(DOWNLOAD_DIR))
    
    while time.time() - start_time < timeout:
        archivos_actuales = set(os.listdir(DOWNLOAD_DIR))
        nuevos_archivos = archivos_actuales - archivos_iniciales
        
        for archivo in nuevos_archivos:
            # Esperar a que termine de descargarse
            if not archivo.endswith('.crdownload') and not archivo.endswith('.tmp'):
                ruta_completa = DOWNLOAD_DIR / archivo
                # Verificar que el archivo tenga contenido
                if ruta_completa.exists() and os.path.getsize(ruta_completa) > 1000:
                    return archivo
        time.sleep(0.3)
    return None

def procesar_guias_optimizado(driver, guias):
    """Procesa guías con clics pero optimizado al máximo"""
    print(f"\n🖱️  Iniciando descarga VISUAL OPTIMIZADA de {len(guias)} guías...")
    
    total = len(guias)
    descargados = 0
    errores = 0
    start_time = time.time()
    
    for idx, guia in enumerate(guias, 1):
        doc_number = guia['l10n_latam_document_number']
        nombre_final = f"{doc_number}.pdf"
        ruta_final = BASE_PATH / nombre_final
        
        if ruta_final.exists():
            print(f"[{idx}/{total}] ⏭️  {doc_number}")
            continue
        
        try:
            # Navegar a la ficha de la guía
            url_ficha = f"{ODOO_URL}/web#id={guia['id']}&model=stock.picking&view_type=form"
            driver.get(url_ficha)
            
            # Espera reducida - Solo esperar el botón crítico
            wait = WebDriverWait(driver, 5)
            
            # Clic en botón Imprimir
            try:
                boton_imprimir = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(@class, 'o_dropdown_title') and contains(text(), 'Imprimir')]")
                ))
                boton_imprimir.click()
            except:
                boton_imprimir = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//span[contains(text(), 'Imprimir')]]")
                ))
                boton_imprimir.click()
            
            # Clic en e-Guía de Remisión AGR
            opcion_agr = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(), 'e-Guía de Remisión AGR')]")
            ))
            opcion_agr.click()
            
            # Esperar descarga
            archivo_descargado = esperar_descarga_rapida()
            
            if archivo_descargado:
                origen = DOWNLOAD_DIR / archivo_descargado
                shutil.move(str(origen), str(ruta_final))
                descargados += 1
                
                # Calcular velocidad
                tiempo_transcurrido = time.time() - start_time
                velocidad = descargados / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
                tiempo_restante = (total - idx) / velocidad if velocidad > 0 else 0
                
                print(f"[{idx}/{total}] ✅ {doc_number} | Vel: {velocidad:.1f} docs/s | ETA: {tiempo_restante/60:.1f} min")
            else:
                print(f"[{idx}/{total}] ❌ {doc_number} (Timeout descarga)")
                errores += 1
                
        except TimeoutException:
            print(f"[{idx}/{total}] ❌ {doc_number} (Botón no encontrado)")
            errores += 1
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {doc_number} ({str(e)[:30]})")
            errores += 1
    
    tiempo_total = time.time() - start_time
    print(f"\n✨ Proceso completado en {tiempo_total/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")

def limpiar_descargas_temporales():
    """Elimina archivos previos en la carpeta temporal de descargas."""
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            try:
                os.remove(DOWNLOAD_DIR / f)
            except:
                pass
    except:
        pass

def descargar_por_url_directa(driver, guias):
    """
    Descarga cada guía navegando directamente a la URL del reporte PDF.
    Usa la sesión real del navegador (más robusto) y evita los clics.
    """
    print(f"\n⚡ Iniciando descarga DIRECTA por URL de {len(guias)} guías...")
    total = len(guias)
    descargados = 0
    errores = 0
    start_time = time.time()

    for idx, guia in enumerate(guias, 1):
        doc_number = guia['l10n_latam_document_number']
        nombre_final = f"{doc_number}.pdf"
        ruta_final = BASE_PATH / nombre_final

        if ruta_final.exists():
            print(f"[{idx}/{total}] ⏭️  {doc_number}")
            continue

        try:
            # Limpiar temporales antes de cada descarga
            limpiar_descargas_temporales()

            # Ruta estándar de Odoo: /report/pdf/<report_name>/<doc_id>
            report_url = f"{ODOO_URL}/report/pdf/{REPORTE_NAME}/{guia['id']}"
            driver.get(report_url)

            archivo_descargado = esperar_descarga_rapida(timeout=12)
            if archivo_descargado:
                origen = DOWNLOAD_DIR / archivo_descargado
                shutil.move(str(origen), str(ruta_final))
                descargados += 1
                # Métricas
                elapsed = time.time() - start_time
                speed = descargados / elapsed if elapsed > 0 else 0
                eta = (total - idx) / speed if speed > 0 else 0
                print(f"[{idx}/{total}] ✅ {doc_number} | Vel: {speed:.2f} docs/s | ETA: {eta/60:.1f} min")
            else:
                print(f"[{idx}/{total}] ❌ {doc_number} (Timeout descarga)")
                errores += 1
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {doc_number} (Error: {str(e)[:60]})")
            errores += 1

    total_time = time.time() - start_time
    print(f"\n✨ Proceso directo completado en {total_time/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")

def main():
    guias = conectar_xmlrpc()
    if not guias:
        return

    driver = iniciar_selenium()
    
    try:
        if login_odoo(driver):
            # Modo directo por URL (mucho más rápido y robusto)
            descargar_por_url_directa(driver, guias)
            # Si prefieres los clics visuales, comenta la línea de arriba
            # y descomenta la siguiente:
            # procesar_guias_optimizado(driver, guias)
    finally:
        print("👋 Cerrando navegador...")
        driver.quit()
        # Limpiar carpeta temporal
        try:
            shutil.rmtree(DOWNLOAD_DIR)
        except:
            pass

if __name__ == "__main__":
    main()
