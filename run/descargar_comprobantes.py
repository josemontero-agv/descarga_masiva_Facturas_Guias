import sys
from pathlib import Path
from datetime import datetime

# Añadir la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import get_periodo_info, get_base_path, ODOO_DB, ODOO_PASSWORD, MAPEO_CARPETAS
from core.odoo_client import conectar_odoo
from modules.documentos_module import descargar_comprobante_integral

def main():
    print(f"\n{'#'*70}")
    print("# DESCARGA DE COMPROBANTES (FACTURAS, BOLETAS, NOTAS)")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    año = 2026
    mes = 1
    info = get_periodo_info(año, mes)
    base_path_mes = get_base_path(año, info['nombre_carpeta_mes'])

    uid, models = conectar_odoo()
    if not uid:
        print("❌ No se pudo conectar a Odoo.")
        return

    print(f"🔍 Buscando comprobantes del {info['fecha_inicio']} al {info['fecha_fin']}...")
    domain = [
        ('state', '=', 'posted'),
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('invoice_date', '>=', info['fecha_inicio']),
        ('invoice_date', '<=', info['fecha_fin']),
    ]
    
    docs = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'l10n_latam_document_type_id', 'invoice_date']}
    )

    if not docs:
        print("⚠️ No se encontraron comprobantes.")
        return

    print(f"✅ Se encontraron {len(docs)} documentos.")

    for idx, doc in enumerate(docs, 1):
        num_doc = doc.get('l10n_latam_document_number') or doc['name']
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')
        
        # Obtener tipo de documento para saber la carpeta
        tipo_doc_raw = doc.get('l10n_latam_document_type_id', [0, ''])[1]
        tipo_carpeta = 'Otros'
        for k, v in MAPEO_CARPETAS.items():
            if k in tipo_doc_raw:
                tipo_carpeta = v
                break
        
        # Verificación rápida: si ya existen PDF y XML, asumimos que está completo
        # Esto ahorra una llamada a la API por cada documento ya descargado
        path_pdf = base_path_mes / tipo_carpeta / 'pdf' / f"{nombre_base}.pdf"
        path_xml = base_path_mes / tipo_carpeta / 'xml' / f"{nombre_base}.xml"
        
        if path_pdf.exists() and path_xml.exists():
            if idx % 100 == 0 or idx == len(docs):
                print(f"   [Verificado] {num_doc} ya existe. Saltando...")
            continue

        stats = descargar_comprobante_integral(uid, models, doc, base_path_mes)
        if idx % 50 == 0 or idx == len(docs):
            print(f"   Progreso: {idx}/{len(docs)}")

    print(f"\n✅ Proceso completado. Archivos en: {base_path_mes}")

if __name__ == "__main__":
    main()
