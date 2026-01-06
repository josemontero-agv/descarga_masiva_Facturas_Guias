# -*- coding: utf-8 -*-
"""
Script para descargar PDFs faltantes usando web scraping
Lee el archivo de análisis FACTURAS_ANALISIS_sin_pdf.txt y descarga los PDFs
que no se pudieron obtener mediante XML-RPC.

ESTRATEGIA:
1. Leer archivo de análisis para obtener IDs de Odoo y nombres de comprobantes
2. XML-RPC: Obtener información del comprobante (diario, tipo de documento)
3. Selenium: Navegar a cada factura y descargar PDF
4. Guardar en la estructura correcta: {Mes}/{Diario}/{TipoDocumento}/pdf/
"""

import os
import sys
import time
import shutil
import re
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Importaciones para ejecución simultánea segura
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

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
AMBIENTE = "produccion"  # ← CAMBIADO: de "produccion" a "desarrollo" para pruebas locales

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

# Configuración de rutas
AÑO = 2025
MES = 11  # ← CAMBIAR AQUÍ EL MES

# Obtener nombre del mes
nombre_mes = datetime(AÑO, MES, 1).strftime('%B')
nombre_carpeta_mes = f"{MES:02d}_{nombre_mes}"

# Ruta base de descarga
if AMBIENTE == "produccion":
    BASE_PATH_RAIZ = rf"V:\{AÑO}\{nombre_carpeta_mes}"
    if not Path(BASE_PATH_RAIZ).parent.parent.exists():
        print(f"⚠️  ADVERTENCIA: No se detecta la unidad Y:")
else:
    BASE_PATH_RAIZ = project_root / "Prueba_Octubre" / nombre_carpeta_mes
    print(f"🔧 MODO DESARROLLO: Guardando en ruta local: {BASE_PATH_RAIZ}")

# Carpeta temporal única por proceso
DOWNLOAD_DIR = project_root / f"temp_downloads_pdfs_{os.getpid()}"

# Crear carpetas si no existen
try:
    Path(BASE_PATH_RAIZ).mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🔧 Proceso PID: {os.getpid()} | Carpeta temporal: {DOWNLOAD_DIR.name}")
except Exception as e:
    print(f"❌ Error creando carpetas: {e}")

# Mapeo de tipos de documentos a carpetas
MAPEO_CARPETAS = {
    'Factura': '01_Facturas',
    'Boleta': '03_Boletas',
    'Nota de Crédito': '07_Notas_Credito',
    'Nota de Débito': '08_Notas_Debito'
}

# ============================================================================
# FUNCIONES DE BLOQUEO PARA EJECUCIÓN SIMULTÁNEA
# ============================================================================

def obtener_bloqueo_archivo(ruta_archivo, timeout=5):
    """Intenta obtener un bloqueo exclusivo sobre un archivo"""
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if sys.platform == 'win32':
                try:
                    lock_file = open(lock_file_path, 'xb')
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except (FileExistsError, IOError, OSError):
                    time.sleep(0.1)
                    continue
            else:
                try:
                    lock_file = open(lock_file_path, 'x')
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (FileExistsError, IOError, OSError):
                    time.sleep(0.1)
                    continue
            
            return lock_file
        except FileExistsError:
            time.sleep(0.1)
            continue
        except Exception:
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
    """Verificación atómica: verifica si el archivo existe y si no, reserva la descarga"""
    if ruta_final.exists():
        return False, None
    
    lock_file = obtener_bloqueo_archivo(ruta_final, timeout=2)
    
    if lock_file is None:
        return False, None
    
    if ruta_final.exists():
        liberar_bloqueo_archivo(lock_file, ruta_final)
        return False, None
    
    return True, lock_file

# ============================================================================
# FUNCIONES
# ============================================================================

def conectar_xmlrpc():
    """Conectar por XML-RPC para obtener información de comprobantes"""
    print(f"📡 Conectando por XML-RPC...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def leer_archivo_analisis():
    """Lee el archivo de análisis y extrae IDs de Odoo y nombres de comprobantes"""
    ruta_analisis = Path(BASE_PATH_RAIZ) / "Resumen de errores" / "FACTURAS_ANALISIS_sin_pdf.txt"
    
    if not ruta_analisis.exists():
        print(f"❌ No se encontró el archivo de análisis: {ruta_analisis}")
        return []
    
    print(f"📖 Leyendo archivo de análisis: {ruta_analisis}")
    
    comprobantes = []
    with open(ruta_analisis, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Buscar patrones: [número] Comprobante: ... ID Odoo: ...
    patron = r'\[(\d+)\]\s+Comprobante:\s+([^\n]+)\s+ID Odoo:\s+(\d+)'
    matches = re.findall(patron, contenido)
    
    for match in matches:
        num, comprobante, odoo_id = match
        comprobantes.append({
            'id': int(odoo_id.strip()),
            'nombre': comprobante.strip(),
            'numero': int(num)
        })
    
    print(f"✅ Se encontraron {len(comprobantes)} comprobantes sin PDF")
    return comprobantes

def obtener_info_comprobante(uid, models, move_id):
    """Obtener información del comprobante (diario, tipo de documento)"""
    try:
        comprobante = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.move', 'read',
            [[move_id]],
            {'fields': ['id', 'name', 'journal_id', 'l10n_latam_document_type_id', 'invoice_date']}
        )
        
        if not comprobante:
            return None
        
        comp = comprobante[0]
        
        # Obtener nombre del diario
        diario_data = comp.get('journal_id')
        nombre_diario = diario_data[1] if diario_data else 'Sin_Diario'
        nombre_diario_limpio = "".join([c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in nombre_diario]).strip()
        
        # Obtener tipo de documento
        tipo_doc_data = comp.get('l10n_latam_document_type_id')
        tipo_doc_nombre = tipo_doc_data[1] if tipo_doc_data and len(tipo_doc_data) > 1 else 'Factura'
        
        # Mapear tipo de documento a carpeta
        tipo_doc_carpeta = '01_Facturas'  # Default
        for tipo_key, carpeta in MAPEO_CARPETAS.items():
            if tipo_key.lower() in tipo_doc_nombre.lower():
                tipo_doc_carpeta = carpeta
                break
        
        return {
            'id': comp['id'],
            'name': comp['name'],
            'diario': nombre_diario_limpio,
            'tipo_doc': tipo_doc_carpeta,
            'fecha': comp.get('invoice_date', '')
        }
    except Exception as e:
        print(f"   ⚠️  Error obteniendo info del comprobante {move_id}: {e}")
        return None

def iniciar_selenium():
    """Inicia Chrome optimizado"""
    print("\n🚀 Iniciando navegador Chrome...")
    
    os.environ['WDM_SSL_VERIFY'] = '0'
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
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
        time.sleep(1)
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
            if not archivo.endswith('.crdownload') and not archivo.endswith('.tmp'):
                ruta_completa = DOWNLOAD_DIR / archivo
                if ruta_completa.exists() and os.path.getsize(ruta_completa) > 1000:
                    return archivo
        time.sleep(0.3)
    return None

def descargar_pdf_por_url_directa(driver, move_id, nombre_comprobante):
    """Descarga PDF navegando directamente a la URL del reporte"""
    try:
        # Limpiar temporales antes de cada descarga para evitar confusiones
        for f in os.listdir(DOWNLOAD_DIR):
            try:
                os.remove(DOWNLOAD_DIR / f)
            except:
                pass
        
        # URL estándar de Odoo para facturas/boletas
        # Odoo 16+ usa: /report/pdf/account.report_invoice/{id}
        report_url = f"{ODOO_URL}/report/pdf/account.report_invoice/{move_id}"
        driver.get(report_url)
        
        # Esperar un poco más para que Odoo genere el PDF (a veces toma tiempo)
        archivo_descargado = esperar_descarga_rapida(timeout=15)
        
        if not archivo_descargado:
            # Reintento con clic visual si la URL directa falla (opcional, pero ayuda)
            ficha_url = f"{ODOO_URL}/web#id={move_id}&model=account.move&view_type=form"
            driver.get(ficha_url)
            time.sleep(2)
        
        return archivo_descargado
    except Exception as e:
        print(f"      ❌ Error en navegación: {str(e)[:50]}")
        return None

def descargar_pdfs_faltantes(driver, comprobantes, uid, models):
    """Descarga PDFs faltantes usando web scraping"""
    print(f"\n🖱️  Iniciando descarga de {len(comprobantes)} PDFs faltantes...")
    
    total = len(comprobantes)
    descargados = 0
    errores = 0
    start_time = time.time()
    
    for idx, comp_info in enumerate(comprobantes, 1):
        move_id = comp_info['id']
        nombre_comprobante = comp_info['nombre']
        
        print(f"\n[{idx}/{total}] 📄 {nombre_comprobante} (ID: {move_id})")
        
        # Obtener información del comprobante (diario, tipo)
        info = obtener_info_comprobante(uid, models, move_id)
        if not info:
            print(f"   ⚠️  No se pudo obtener información del comprobante")
            errores += 1
            continue
        
        # Construir ruta destino: {Mes}/{Diario}/{TipoDocumento}/pdf/
        ruta_carpeta_pdf = Path(BASE_PATH_RAIZ) / info['diario'] / info['tipo_doc'] / 'pdf'
        ruta_carpeta_pdf.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo final
        nombre_limpio = nombre_comprobante.replace('/', '-').replace('\\', '-')
        nombre_final = f"{nombre_limpio}.pdf"
        ruta_final = ruta_carpeta_pdf / nombre_final
        
        # Verificación atómica con bloqueo
        puede_descargar, lock_file = verificar_y_reservar_descarga(ruta_final)
        
        if not puede_descargar:
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)
            print(f"   ⏭️  Ya existe o está en proceso")
            continue
        
        try:
            # Descargar PDF
            archivo_descargado = descargar_pdf_por_url_directa(driver, move_id, nombre_comprobante)
            
            if archivo_descargado:
                origen = DOWNLOAD_DIR / archivo_descargado
                try:
                    shutil.move(str(origen), str(ruta_final))
                    descargados += 1
                    
                    # Calcular velocidad
                    tiempo_transcurrido = time.time() - start_time
                    velocidad = descargados / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
                    tiempo_restante = (total - idx) / velocidad if velocidad > 0 else 0
                    
                    print(f"   ✅ Descargado | Vel: {velocidad:.1f} docs/s | ETA: {tiempo_restante/60:.1f} min")
                    print(f"   📂 Guardado en: {ruta_final.parent.name}/{ruta_final.parent.parent.name}/pdf/")
                except (FileExistsError, shutil.Error):
                    try:
                        if origen.exists():
                            os.remove(origen)
                    except:
                        pass
                    print(f"   ⏭️  Descargado por otro proceso")
            else:
                print(f"   ❌ Timeout descarga")
                errores += 1
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:60]}")
            errores += 1
        finally:
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)
    
    tiempo_total = time.time() - start_time
    print(f"\n✨ Proceso completado en {tiempo_total/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")

def main():
    # Leer archivo de análisis
    comprobantes = leer_archivo_analisis()
    if not comprobantes:
        print("❌ No se encontraron comprobantes para procesar")
        return
    
    # Conectar XML-RPC
    uid, models = conectar_xmlrpc()
    
    # Iniciar Selenium
    driver = iniciar_selenium()
    
    try:
        if login_odoo(driver):
            descargar_pdfs_faltantes(driver, comprobantes, uid, models)
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
