import os
import sys
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
    descargar_pdf_guia_selenium
)

def main():
    print(f"\n{'#'*70}")
    print("# PROCESO INTEGRAL DE DESCARGA DE GUÍAS (XML + PDF)")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    # 1. Configuración de periodo
    # Estos valores podrían venir de argumentos de línea de comandos en el futuro
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
        ('picking_type_id', '=', 2), # Ajustar ID según corresponda
        ('l10n_latam_document_number', '!=', False),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'stock.picking', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'date_done']}
    )

    if not guias:
        print("⚠️ No se encontraron guías en este periodo.")
        return

    print(f"✅ Se encontraron {len(guias)} guías.")

    # 4. Descarga de XML/CDR (XML-RPC)
    print("\n📥 Descargando archivos XML y CDR...")
    for idx, guia in enumerate(guias, 1):
        num_doc = guia['l10n_latam_document_number']
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')
        
        # Verificar si ya existen XML y CDR
        path_xml = base_path_guia / "xml" / f"{nombre_base}.xml"
        # El CDR es opcional en algunos casos, pero verificamos el XML
        if path_xml.exists():
            if idx % 100 == 0 or idx == len(guias):
                print(f"   [Verificado XML] {num_doc} ya existe.")
        else:
            stats = descargar_xml_cdr_guia(uid, models, guia, base_path_guia)
            
        if idx % 50 == 0:
            print(f"   Progreso XML: {idx}/{len(guias)}")

    # 5. Descarga de PDF (Selenium)
    print("\n🌐 Iniciando Selenium para descarga de PDFs...")
    temp_dir = PROJECT_ROOT / f"temp_downloads_{os.getpid()}"
    temp_dir.mkdir(exist_ok=True)
    
    driver = setup_browser(temp_dir)
    try:
        if login_odoo_web(driver, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD):
            print("✅ Login web exitoso.")
            for idx, guia in enumerate(guias, 1):
                num_doc = guia['l10n_latam_document_number']
                nombre_pdf = num_doc.replace('/', '-').replace('\\', '-') + ".pdf"
                ruta_final_pdf = base_path_guia / "pdf" / nombre_pdf
                
                if ruta_final_pdf.exists():
                    print(f"   [{idx}/{len(guias)}] Skipped: {num_doc} (Ya existe)")
                    continue
                
                print(f"   [{idx}/{len(guias)}] Descargando PDF: {num_doc}")
                descargar_pdf_guia_selenium(driver, guia['id'], num_doc, base_path_guia / "pdf", temp_dir)
        else:
            print("❌ Error en login web.")
    finally:
        driver.quit()
        # Limpiar carpeta temporal
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)

    print(f"\n✅ Proceso completado. Archivos guardados en: {base_path_guia}")

if __name__ == "__main__":
    main()
