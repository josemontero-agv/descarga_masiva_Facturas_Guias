# -*- coding: utf-8 -*-
"""
Script para descargar PDFs de Guías de Remisión - VERSIÓN VISUAL OPTIMIZADA
ESTRATEGIA:
1. XML-RPC: Obtener lista de guías (rápido)
2. Selenium: Navegar a cada ficha y hacer clic en Imprimir > e-Guía AGR
3. Optimizaciones: Esperas mínimas, sin recargas innecesarias, gestión rápida de archivos

Tiempo estimado: ~3 segundos por guía = 1000 guías en 50 minutos
Autor: GitHub Proyectos AGV

EJECUCIÓN SIMULTÁNEA:
✅ Este script soporta ejecución simultánea en múltiples terminales
- Cada proceso usa su propia carpeta temporal (temp_downloads_{PID})
- Sistema de bloqueo de archivos evita descargas duplicadas
- Verificación atómica previene race conditions
"""

import os
import sys
import time
import shutil
import glob
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from calendar import monthrange

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
AMBIENTE = "produccion"  # ← CAMBIAR AQUÍ: "desarrollo" o "produccion"

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
AÑO = 2026
MES = 1

ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"

# Obtener nombre del mes en español
MESES_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
nombre_mes = MESES_ESPANOL.get(MES, datetime(AÑO, MES, 1).strftime('%B'))
nombre_carpeta_mes = f"{MES:02d}_{nombre_mes}"

# Ruta base de descarga
if AMBIENTE == "produccion":
    BASE_PATH_RAIZ = rf"V:\{AÑO}\{nombre_carpeta_mes}"
    if not Path(BASE_PATH_RAIZ).parent.parent.exists():
        print(f"⚠️  ADVERTENCIA: No se detecta la unidad V:")
        # Se podría añadir input de confirmación aquí
else:
    BASE_PATH_RAIZ = project_root / "Prueba_Octubre" / nombre_carpeta_mes
    print(f"🔧 MODO DESARROLLO: Guardando en ruta local: {BASE_PATH_RAIZ}")

# Rutas específicas
BASE_PATH = Path(BASE_PATH_RAIZ) / "09_Guias_Remision" / "pdf"
# Carpeta temporal única por proceso para ejecución simultánea segura
DOWNLOAD_DIR = project_root / f"temp_downloads_{os.getpid()}"

# Crear carpetas si no existen
try:
    Path(BASE_PATH_RAIZ).mkdir(parents=True, exist_ok=True)
    BASE_PATH.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🔧 Proceso PID: {os.getpid()} | Carpeta temporal: {DOWNLOAD_DIR.name}")
except Exception as e:
    print(f"❌ Error creando carpetas: {e}")

# Reporte técnico (route) para e-Guía AGR en Odoo
REPORTE_NAME = "agr_shiping_guide.report_edi_gre"

# ============================================================================
# FUNCIONES DE BLOQUEO PARA EJECUCIÓN SIMULTÁNEA
# ============================================================================

def obtener_bloqueo_archivo(ruta_archivo, timeout=5):
    """
    Intenta obtener un bloqueo exclusivo sobre un archivo para evitar 
    descargas duplicadas en ejecución simultánea.
    Retorna un objeto de archivo bloqueado o None si no se pudo obtener.
    """
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # En Windows, usar modo binario exclusivo para bloqueo
            if sys.platform == 'win32':
                try:
                    lock_file = open(lock_file_path, 'xb')
                    # Bloquear el archivo en Windows
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except (FileExistsError, IOError, OSError):
                    # Otro proceso ya tiene el bloqueo o error al bloquear
                    time.sleep(0.1)
                    continue
            else:
                # En Linux/Mac, usar fcntl
                try:
                    lock_file = open(lock_file_path, 'x')
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (FileExistsError, IOError, OSError):
                    time.sleep(0.1)
                    continue
            
            return lock_file
        except FileExistsError:
            # Otro proceso ya tiene el bloqueo
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
    """
    Verificación atómica: verifica si el archivo existe y si no, 
    reserva la descarga con un bloqueo.
    Retorna (puede_descargar, lock_file)
    """
    # Verificar si ya existe
    if ruta_final.exists():
        return False, None
    
    # Intentar obtener bloqueo para esta descarga específica
    lock_file = obtener_bloqueo_archivo(ruta_final, timeout=2)
    
    if lock_file is None:
        # No se pudo obtener el bloqueo, otro proceso está descargando
        return False, None
    
    # Verificar nuevamente después de obtener el bloqueo
    if ruta_final.exists():
        liberar_bloqueo_archivo(lock_file, ruta_final)
        return False, None
    
    return True, lock_file

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
    
    # Estructura de análisis de problemas
    analisis_problemas = {
        'errores_descarga': [],
        'comprobantes_ok': [],
        'sin_pdf': []
    }
    
    for idx, guia in enumerate(guias, 1):
        doc_number = guia['l10n_latam_document_number']
        guia_id = guia['id']
        nombre_final = f"{doc_number}.pdf"
        ruta_final = BASE_PATH / nombre_final
        
        # Verificación atómica con bloqueo para ejecución simultánea
        puede_descargar, lock_file = verificar_y_reservar_descarga(ruta_final)
        
        if not puede_descargar:
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)
            print(f"[{idx}/{total}] ⏭️  {doc_number} (ya existe o en proceso)")
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
                # Mover con manejo de errores por concurrencia
                try:
                    shutil.move(str(origen), str(ruta_final))
                    descargados += 1
                except (FileExistsError, shutil.Error):
                    # Otro proceso ya descargó el archivo
                    try:
                        if origen.exists():
                            os.remove(origen)
                    except:
                        pass
                    print(f"[{idx}/{total}] ⏭️  {doc_number} (descargado por otro proceso)")
                    continue
                
                # Registrar éxito
                analisis_problemas['comprobantes_ok'].append({
                    'nombre': doc_number,
                    'id': guia_id
                })
                
                # Calcular velocidad
                tiempo_transcurrido = time.time() - start_time
                velocidad = descargados / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
                tiempo_restante = (total - idx) / velocidad if velocidad > 0 else 0
                
                print(f"[{idx}/{total}] ✅ {doc_number} | Vel: {velocidad:.1f} docs/s | ETA: {tiempo_restante/60:.1f} min")
            else:
                print(f"[{idx}/{total}] ❌ {doc_number} (Timeout descarga)")
                errores += 1
                analisis_problemas['errores_descarga'].append({
                    'nombre': doc_number,
                    'id': guia_id,
                    'error': "Timeout esperando descarga"
                })
                
        except TimeoutException:
            print(f"[{idx}/{total}] ❌ {doc_number} (Botón no encontrado)")
            errores += 1
            analisis_problemas['errores_descarga'].append({
                'nombre': doc_number,
                'id': guia_id,
                'error': "Timeout: Botón Imprimir o AGR no encontrado"
            })
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {doc_number} ({str(e)[:30]})")
            errores += 1
            analisis_problemas['errores_descarga'].append({
                'nombre': doc_number,
                'id': guia_id,
                'error': str(e)[:100]
            })
        finally:
            # Liberar bloqueo siempre, incluso si hubo error
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)
    
    tiempo_total = time.time() - start_time
    print(f"\n✨ Proceso completado en {tiempo_total/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")
    
    # Mostrar análisis detallado
    mostrar_analisis_problemas(analisis_problemas)

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
    
    # Estructura de análisis de problemas
    analisis_problemas = {
        'errores_descarga': [],
        'comprobantes_ok': [],
        'sin_pdf': []
    }

    for idx, guia in enumerate(guias, 1):
        doc_number = guia['l10n_latam_document_number']
        guia_id = guia['id']
        nombre_final = f"{doc_number}.pdf"
        ruta_final = BASE_PATH / nombre_final

        # Verificación atómica con bloqueo para ejecución simultánea
        puede_descargar, lock_file = verificar_y_reservar_descarga(ruta_final)
        
        if not puede_descargar:
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)
            print(f"[{idx}/{total}] ⏭️  {doc_number} (ya existe o en proceso)")
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
                # Mover con manejo de errores por concurrencia
                try:
                    shutil.move(str(origen), str(ruta_final))
                    descargados += 1
                except (FileExistsError, shutil.Error):
                    # Otro proceso ya descargó el archivo
                    try:
                        if origen.exists():
                            os.remove(origen)
                    except:
                        pass
                    print(f"[{idx}/{total}] ⏭️  {doc_number} (descargado por otro proceso)")
                    continue
                
                # Registrar éxito
                analisis_problemas['comprobantes_ok'].append({
                    'nombre': doc_number,
                    'id': guia_id
                })
                
                # Métricas
                elapsed = time.time() - start_time
                speed = descargados / elapsed if elapsed > 0 else 0
                eta = (total - idx) / speed if speed > 0 else 0
                print(f"[{idx}/{total}] ✅ {doc_number} | Vel: {speed:.2f} docs/s | ETA: {eta/60:.1f} min")
            else:
                print(f"[{idx}/{total}] ❌ {doc_number} (Timeout descarga)")
                errores += 1
                analisis_problemas['errores_descarga'].append({
                    'nombre': doc_number,
                    'id': guia_id,
                    'error': "Timeout esperando descarga (PDF no generado o lentitud)"
                })
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {doc_number} (Error: {str(e)[:60]})")
            errores += 1
            analisis_problemas['errores_descarga'].append({
                'nombre': doc_number,
                'id': guia_id,
                'error': str(e)[:100]
            })
        finally:
            # Liberar bloqueo siempre, incluso si hubo error
            if lock_file:
                liberar_bloqueo_archivo(lock_file, ruta_final)

    total_time = time.time() - start_time
    print(f"\n✨ Proceso directo completado en {total_time/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")
    
    # Mostrar análisis detallado
    mostrar_analisis_problemas(analisis_problemas)

def mostrar_analisis_problemas(analisis):
    """Mostrar análisis detallado de problemas encontrados"""
    print(f"\n{'='*70}")
    print("🔍 ANÁLISIS DETALLADO DE PROBLEMAS")
    print(f"{'='*70}")
    
    total_problemas = (
        len(analisis['errores_descarga']) + 
        len(analisis['sin_pdf'])
    )
    
    if total_problemas == 0:
        print("✅ No se encontraron problemas - Todas las guías OK")
        return
    
    print(f"\n⚠️  Se encontraron {total_problemas} problemas en total:\n")
    
    # 1. Errores de descarga / Sin PDF
    if analisis['errores_descarga']:
        print(f"❌ ERRORES DE DESCARGA ({len(analisis['errores_descarga'])} guías):")
        print(f"   Motivo: Timeout, error de conexión o PDF no generado")
        
        for err in analisis['errores_descarga'][:5]:
            print(f"      • {err['nombre']} - {err['error']}")
        
        if len(analisis['errores_descarga']) > 5:
            print(f"      ... y {len(analisis['errores_descarga']) - 5} más")
            
        guardar_lista_problemas('errores_descarga', analisis['errores_descarga'])
        print(f"   💾 Lista guardada en: {BASE_PATH.parent}/ANALISIS_errores_descarga.txt")
        print()

    # 2. Generar resumen consolidado
    guardar_resumen_consolidado(analisis, total_problemas)
    
    print(f"{'='*70}\n")


def guardar_resumen_consolidado(analisis, total_problemas):
    """Guardar resumen consolidado de todos los problemas"""
    try:
        # Crear carpeta de logs en la raíz del mes
        carpeta_logs = Path(BASE_PATH_RAIZ) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / "RESUMEN_COMPLETO_PROBLEMAS_GUIAS_PDF.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN CONSOLIDADO - DESCARGA PDFS GUÍAS (SCRAPING/DIRECTO)\n")
            f.write(f"{'#'*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Período: {FECHA_INICIO} al {FECHA_FIN}\n")
            f.write(f"Ambiente: {AMBIENTE.upper()}\n")
            f.write(f"{'#'*70}\n\n")
            
            # Resumen ejecutivo
            f.write("="*70 + "\n")
            f.write("RESUMEN EJECUTIVO\n")
            f.write("="*70 + "\n")
            f.write(f"Total de problemas encontrados: {total_problemas}\n\n")
            
            f.write(f"❌ Errores de descarga:          {len(analisis['errores_descarga'])}\n")
            f.write(f"✅ Guías OK:                     {len(analisis['comprobantes_ok'])}\n")
            f.write("\n")
            
            # Archivos de detalle generados
            f.write("="*70 + "\n")
            f.write("ARCHIVOS DE DETALLE GENERADOS\n")
            f.write("="*70 + "\n")
            if analisis['errores_descarga']:
                f.write(f"• ANALISIS_errores_descarga.txt  ({len(analisis['errores_descarga'])} registros)\n")
            f.write("\n")
            
            # IDs de Odoo para búsqueda directa
            if analisis['errores_descarga']:
                f.write("="*70 + "\n")
                f.write("IDs DE ODOO PARA BÚSQUEDA DIRECTA\n")
                f.write("="*70 + "\n\n")
                
                ids = [str(item.get('id', '')) for item in analisis['errores_descarga'][:50] if item.get('id')]
                if ids:
                    f.write("ERRORES (IDs para buscar en Odoo):\n")
                    f.write(", ".join(ids))
                    if len(analisis['errores_descarga']) > 50:
                        f.write(f"... y más")
                    f.write("\n\n")
        
        print(f"   📊 Resumen consolidado guardado en: {carpeta_logs}/RESUMEN_COMPLETO_PROBLEMAS_GUIAS_PDF.txt")
        
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar resumen consolidado: {e}")


def guardar_lista_problemas(tipo, lista):
    """Guardar lista de problemas en archivo de texto"""
    try:
        # Crear carpeta de logs
        carpeta_logs = Path(BASE_PATH_RAIZ) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / f"ANALISIS_{tipo}_guias_pdf.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"ANÁLISIS DE PROBLEMAS: {tipo.upper().replace('_', ' ')}\n")
            f.write(f"{'='*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total de problemas: {len(lista)}\n")
            f.write(f"{'='*70}\n\n")
            
            for idx, item in enumerate(lista, 1):
                f.write(f"[{idx}] Guía: {item['nombre']}\n")
                if 'id' in item: f.write(f"    ID Odoo: {item['id']}\n")
                if 'error' in item: f.write(f"    Error: {item['error']}\n")
                f.write("\n")
            
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar archivo de análisis: {e}")

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
