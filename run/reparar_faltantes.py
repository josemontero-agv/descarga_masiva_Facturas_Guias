import os
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import get_periodo_info, get_base_path, ODOO_DB, ODOO_PASSWORD, ODOO_URL, ODOO_USER
from core.odoo_client import conectar_odoo
from modules.guias_module import setup_browser, login_odoo_web, descargar_pdf_guia_selenium
from modules.documentos_module import descargar_comprobante_integral

def main():
    print(f"\n{'='*70}")
    print("🛠️  HERRAMIENTA DE REPARACIÓN DE FALTANTES")
    print(f"{'='*70}")

    año = 2026
    mes = 1
    info = get_periodo_info(año, mes)
    base_path_mes = get_base_path(año, info['nombre_carpeta_mes'])

    uid, models = conectar_odoo()
    if not uid: return

    # 1. Reparar Guías (PDFs faltantes)
    print("\n🔍 Verificando Guías sin PDF...")
    path_guias_pdf = base_path_mes / "09_Guias_Remision" / "pdf"
    
    # Obtener todas las guías del periodo para comparar
    domain_guias = [
        ('state', '=', 'done'),
        ('picking_type_id', '=', 2),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.picking', 'search_read', [domain_guias], {'fields': ['id', 'l10n_latam_document_number']})
    
    guias_faltantes = []
    for g in guias:
        num_doc = g['l10n_latam_document_number']
        if num_doc:
            nombre_pdf = num_doc.replace('/', '-').replace('\\', '-') + ".pdf"
            if not (path_guias_pdf / nombre_pdf).exists():
                guias_faltantes.append(g)

    if guias_faltantes:
        print(f"⚠️ Se encontraron {len(guias_faltantes)} guías sin PDF. Iniciando Selenium...")
        temp_dir = PROJECT_ROOT / f"temp_repair_{os.getpid()}"
        temp_dir.mkdir(exist_ok=True)
        driver = setup_browser(temp_dir)
        try:
            if login_odoo_web(driver, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD):
                for g in guias_faltantes:
                    num_doc = g['l10n_latam_document_number']
                    print(f"   Reparando PDF Guía: {num_doc}")
                    descargar_pdf_guia_selenium(driver, g['id'], num_doc, path_guias_pdf, temp_dir)
        finally:
            driver.quit()
            import shutil
            shutil.rmtree(temp_dir)
    else:
        print("✅ Todas las guías tienen su PDF.")

    # 2. Reparar Otros Documentos (XML/PDF/CDR)
    # Aquí se podría implementar una lógica similar para Facturas si se detecta que faltan archivos.
    
    print("\n✅ Proceso de reparación finalizado.")

if __name__ == "__main__":
    main()
