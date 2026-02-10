import os
import sys
from pathlib import Path
from datetime import datetime

# Añadir la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import get_periodo_info, get_base_path, ODOO_DB, ODOO_PASSWORD, ODOO_URL, ODOO_USER, MAPEO_CARPETAS
from core.odoo_client import conectar_odoo
from modules.guias_module import setup_browser, login_odoo_web, descargar_pdf_guia_url_directa
from modules.documentos_module import descargar_comprobante_integral

def buscar_archivo_recursivo(base_path, nombre_archivo):
    """Busca un archivo dentro de una carpeta y todas sus subcarpetas (Diarios)"""
    for path in base_path.rglob(nombre_archivo):
        return path
    return None

def main():
    print(f"\n{'='*70}")
    print("🛠️  HERRAMIENTA DE REPARACIÓN DE FALTANTES (MODO RECURSIVO)")
    print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # CONFIGURACIÓN DE PERIODO (Ajustar según necesidad)
    año = 2026
    mes = 1
    info = get_periodo_info(año, mes)
    base_path_mes = get_base_path(año, info['nombre_carpeta_mes'])

    uid, models = conectar_odoo()
    if not uid: 
        print("❌ No se pudo conectar a Odoo.")
        return

    # ============================================================================
    # 1. REPARAR COMPROBANTES (Facturas, Boletas, Notas)
    # ============================================================================
    print(f"\n🔍 Verificando Comprobantes faltantes en {base_path_mes}...")
    
    # Obtener todos los comprobantes del periodo desde Odoo
    domain_docs = [
        ('state', '=', 'posted'),
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('invoice_date', '>=', info['fecha_inicio']),
        ('invoice_date', '<=', info['fecha_fin']),
    ]
    docs_odoo = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD, 
        'account.move', 'search_read', 
        [domain_docs], 
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'l10n_latam_document_type_id', 'journal_id']}
    )

    docs_faltantes = []
    for doc in docs_odoo:
        num_doc = doc.get('l10n_latam_document_number') or doc['name']
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')
        
        # Búsqueda recursiva: no importa en qué diario esté, si el PDF existe, saltamos
        if not buscar_archivo_recursivo(base_path_mes, f"{nombre_base}.pdf"):
            docs_faltantes.append(doc)

    if docs_faltantes:
        print(f"⚠️  Se encontraron {len(docs_faltantes)} comprobantes faltantes.")
        for idx, doc in enumerate(docs_faltantes, 1):
            num_doc = doc.get('l10n_latam_document_number') or doc['name']
            diario_raw = doc.get('journal_id', [0, ''])
            nombre_diario = diario_raw[1] if diario_raw else 'Sin_Diario'
            
            print(f"   [{idx}/{len(docs_faltantes)}] Reparando: {num_doc} ({nombre_diario})")
            descargar_comprobante_integral(uid, models, doc, base_path_mes, nombre_diario=nombre_diario)
    else:
        print("✅ Todos los comprobantes (Facturas/Boletas) están completos.")

    # ============================================================================
    # 2. REPARAR GUÍAS (PDFs faltantes)
    # ============================================================================
    print(f"\n🔍 Verificando Guías sin PDF...")
    base_path_guia = base_path_mes / "09_Guias_Remision"
    
    domain_guias = [
        ('state', '=', 'done'),
        ('picking_type_id', '=', 2),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias_odoo = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD, 
        'stock.picking', 'search_read', 
        [domain_guias], 
        {'fields': ['id', 'l10n_latam_document_number']}
    )
    
    guias_faltantes = []
    for g in guias_odoo:
        num_doc = g['l10n_latam_document_number']
        if num_doc:
            nombre_pdf = num_doc.replace('/', '-').replace('\\', '-') + ".pdf"
            # Búsqueda recursiva para guías también (por si se organizan por diario en el futuro)
            if not buscar_archivo_recursivo(base_path_guia, nombre_pdf):
                guias_faltantes.append(g)

    if guias_faltantes:
        print(f"⚠️  Se encontraron {len(guias_faltantes)} guías sin PDF. Iniciando Selenium...")
        temp_dir = PROJECT_ROOT / f"temp_repair_{os.getpid()}"
        temp_dir.mkdir(exist_ok=True)
        driver = setup_browser(temp_dir)
        try:
            if login_odoo_web(driver, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD):
                for g in guias_faltantes:
                    num_doc = g['l10n_latam_document_number']
                    print(f"   Reparando PDF Guía: {num_doc}")
                    # Usar el método de URL directa para mayor robustez
                    descargar_pdf_guia_url_directa(driver, g['id'], num_doc, base_path_guia / "pdf", temp_dir)
        finally:
            driver.quit()
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
    else:
        print("✅ Todas las guías tienen su PDF.")

    print(f"\n✅ PROCESO DE REPARACIÓN FINALIZADO.")
    print(f"   Ubicación: {base_path_mes}")

if __name__ == "__main__":
    main()
