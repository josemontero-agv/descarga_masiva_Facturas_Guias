import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Añadir la raíz del proyecto al path para importar core y modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import get_periodo_info, get_base_path, AMBIENTE, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD
from core.odoo_client import conectar_odoo
from modules.guias_module import (
    descargar_xml_cdr_guia, 
    setup_browser, 
    login_odoo_web, 
    descargar_pdf_guia_url_directa,
    verificar_y_reservar_descarga,
    liberar_bloqueo_archivo
)

def guardar_resumen_guias(base_path_raiz, analisis):
    """Guardar resumen de guías faltantes para reparación"""
    try:
        carpeta_logs = base_path_raiz / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        ruta_archivo = carpeta_logs / "GUIAS_RESUMEN_COMPLETO_PROBLEMAS.txt"
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN DE DESCARGA DE GUIAS\n")
            f.write(f"{'#'*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"❌ Fallidos/Faltantes: {len(analisis['errores'])}\n")
            f.write(f"✅ Exitosos:           {len(analisis['comprobantes_ok'])}\n")
            f.write(f"{'#'*70}\n\n")
            
            if analisis['errores']:
                f.write("IDs DE ODOO CON ERRORES (Para Reparación):\n")
                ids = [str(item['id']) for item in analisis['errores']]
                f.write(", ".join(ids))
                f.write("\n")
        print(f"   📊 Resumen de guías guardado en: {ruta_archivo}")
    except Exception as e:
        print(f"   ⚠️ No se pudo guardar el resumen de guías: {e}")

def main():
    print(f"\n{'#'*70}")
    print("# PROCESO INTEGRAL DE DESCARGA DE GUÍAS (XML + PDF)")
    print(f"# Ejecución Segura para Terminales Múltiples (PID: {os.getpid()})")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    # 1. Configuración de periodo
    año = 2026
    mes = 1
    info = get_periodo_info(año, mes)
    base_path_raiz = get_base_path(año, info['nombre_carpeta_mes'])
    base_path_guia = base_path_raiz / "09_Guias_Remision"
    
    # Crear carpetas base
    (base_path_guia / "xml").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "cdr").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "pdf").mkdir(parents=True, exist_ok=True)

    # 2. Conexión Odoo (XML-RPC)
    uid, models = conectar_odoo()
    if not uid:
        print("❌ No se pudo conectar a Odoo. Verifica tu .env")
        return

    # 3. Buscar Guías
    print(f"🔍 Buscando guías del {info['fecha_inicio']} al {info['fecha_fin']}...")
    domain = [
        ('state', '=', 'done'),
        ('picking_type_id', '=', 2), # Ajustar ID según corresponda (Producción: 2)
        ('l10n_latam_document_number', '!=', False),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'stock.picking', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'date_done'], 'order': 'date_done asc'}
    )

    if not guias:
        print("⚠️ No se encontraron guías en este periodo.")
        return

    print(f"✅ Se encontraron {len(guias)} guías.")

    # 4. Descarga Combinada (XML/CDR + PDF con Selenium)
    print("\n🌐 Iniciando Navegador para descarga de PDFs...")
    temp_dir = PROJECT_ROOT / f"temp_downloads_{os.getpid()}"
    temp_dir.mkdir(exist_ok=True)
    
    driver = setup_browser(temp_dir)
    stats = {'descargados': 0, 'errores': 0, 'saltados': 0}
    analisis = {'errores': [], 'comprobantes_ok': []}
    
    try:
        if login_odoo_web(driver, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD):
            print("✅ Login web exitoso.")
            
            for idx, guia in enumerate(guias, 1):
                num_doc = guia['l10n_latam_document_number']
                nombre_base = num_doc.replace('/', '-').replace('\\', '-')
                ruta_pdf = base_path_guia / "pdf" / f"{nombre_base}.pdf"
                
                # VERIFICACIÓN ATÓMICA Y RESERVA (Bloqueo .lock)
                # Esto permite que si abres otra terminal, esta no descargue lo mismo
                puede_procesar, lock_file = verificar_y_reservar_descarga(ruta_pdf)
                
                if not puede_procesar:
                    stats['saltados'] += 1
                    analisis['comprobantes_ok'].append({'id': guia['id'], 'nombre': num_doc})
                    if idx % 100 == 0 or idx == len(guias):
                        print(f"   [{idx}/{len(guias)}] Skipped: {num_doc} (Ya existe o en proceso)")
                    continue

                try:
                    # A. Descargar XML y CDR (vía API)
                    descargar_xml_cdr_guia(uid, models, guia, base_path_guia)
                    
                    # B. Descargar PDF (vía URL Directa en Selenium)
                    print(f"   [{idx}/{len(guias)}] Procesando: {num_doc}")
                    if descargar_pdf_guia_url_directa(driver, guia['id'], num_doc, base_path_guia / "pdf", temp_dir):
                        stats['descargados'] += 1
                        analisis['comprobantes_ok'].append({'id': guia['id'], 'nombre': num_doc})
                    else:
                        print(f"      ❌ Error al obtener PDF para {num_doc}")
                        stats['errores'] += 1
                        analisis['errores'].append({'id': guia['id'], 'nombre': num_doc})
                except Exception as e:
                    print(f"      ❌ Error crítico en {num_doc}: {e}")
                    stats['errores'] += 1
                    analisis['errores'].append({'id': guia['id'], 'nombre': num_doc})
                finally:
                    # Siempre liberar el bloqueo al terminar con esta guía
                    liberar_bloqueo_archivo(lock_file, ruta_pdf)

                if idx % 50 == 0:
                    print(f"   >>> Progreso: {idx}/{len(guias)} (Descargados: {stats['descargados']})")
        else:
            print("❌ Error en login web. Revisa tus credenciales en el navegador.")
    finally:
        driver.quit()
        # Limpiar carpeta temporal
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)

    # Guardar resumen de guías para reparación
    guardar_resumen_guias(base_path_raiz, analisis)

    print(f"\n{'='*70}")
    print(f"✅ PROCESO FINALIZADO")
    print(f"   - Procesados:  {stats['descargados']}")
    print(f"   - Con errores: {stats['errores']}")
    print(f"   - Saltados:    {stats['saltados']}")
    print(f"   - Ubicación:   {base_path_guia}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
