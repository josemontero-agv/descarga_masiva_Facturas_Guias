import sys
from pathlib import Path
from datetime import datetime

# Añadir la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import get_periodo_info, get_base_path, ODOO_DB, ODOO_PASSWORD, MAPEO_CARPETAS, AMBIENTE
from core.odoo_client import conectar_odoo
from modules.documentos_module import descargar_comprobante_integral

def guardar_resumen_errores(base_path_mes, año, mes, analisis, duracion=None):
    """Guardar resumen consolidado de problemas en un archivo .txt"""
    try:
        carpeta_logs = base_path_mes / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        info = get_periodo_info(año, mes)
        ruta_archivo = carpeta_logs / "FACTURAS_RESUMEN_COMPLETO_PROBLEMAS.txt"
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN CONSOLIDADO - ANÁLISIS DE DESCARGA\n")
            f.write(f"{'#'*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Período: {info['nombre_mes']} {año}\n")
            f.write(f"Ambiente: {AMBIENTE.upper()}\n")
            if duracion:
                f.write(f"Duración total: {duracion}\n")
            f.write(f"{'#'*70}\n\n")
            
            f.write(f"❌ Comprobantes con errores:    {len(analisis['errores'])}\n")
            f.write(f"✅ Comprobantes OK:             {len(analisis['comprobantes_ok'])}\n")
            f.write("\n")
            
            if analisis['errores']:
                f.write("IDs DE ODOO CON ERRORES (Para Reparación):\n")
                ids = [str(item['id']) for item in analisis['errores']]
                f.write(", ".join(ids))
                f.write("\n")

        print(f"   📊 Resumen de errores guardado en: {ruta_archivo}")
    except Exception as e:
        print(f"   ⚠️ No se pudo guardar el resumen de errores: {e}")

def main():
    t_inicio = datetime.now()
    print(f"\n{'#'*70}")
    print("# DESCARGA DE COMPROBANTES (FACTURAS, BOLETAS, NOTAS)")
    print(f"# Fecha Inicio: {t_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    año = 2026
    mes = 2
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
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'l10n_latam_document_type_id', 'invoice_date', 'journal_id']}
    )

    if not docs:
        print("⚠️ No se encontraron comprobantes.")
        return

    print(f"✅ Se encontraron {len(docs)} documentos.")

    analisis = {'errores': [], 'comprobantes_ok': []}

    for idx, doc in enumerate(docs, 1):
        # Priorizar el campo 'name' para mantener el prefijo "F " o "B " y el espacio
        num_doc = doc.get('name') or doc.get('l10n_latam_document_number', f"DOC_{doc['id']}")
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')
        
        # Obtener nombre del diario
        diario_raw = doc.get('journal_id', [0, ''])
        nombre_diario = diario_raw[1] if diario_raw else 'Sin_Diario'
        nombre_diario_limpio = "".join([c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in nombre_diario]).strip()
        
        # Obtener tipo de documento para saber la carpeta
        tipo_doc_raw = doc.get('l10n_latam_document_type_id', [0, ''])[1]
        tipo_carpeta = 'Otros'
        for k, v in MAPEO_CARPETAS.items():
            if k in tipo_doc_raw:
                tipo_carpeta = v
                break
        
        # Verificación rápida con los nuevos sufijos para total similitud con archive
        path_pdf = base_path_mes / nombre_diario_limpio / tipo_carpeta / 'pdf' / f"{nombre_base}_pdf.pdf"
        path_xml = base_path_mes / nombre_diario_limpio / tipo_carpeta / 'xml' / f"{nombre_base}_xml.xml"
        path_cdr = base_path_mes / nombre_diario_limpio / tipo_carpeta / 'cdr' / f"{nombre_base}_cdr.xml"
        
        if path_pdf.exists() and path_xml.exists():
            if idx % 100 == 0 or idx == len(docs):
                print(f"   [Verificado] {num_doc} ({nombre_diario}) ya existe. Saltando...")
            analisis['comprobantes_ok'].append({'id': doc['id'], 'nombre': num_doc})
            continue

        stats = descargar_comprobante_integral(uid, models, doc, base_path_mes, nombre_diario=nombre_diario)
        
        # Si no se descargó al menos un XML o PDF, lo marcamos como error para reintento
        if stats.get('xml', 0) == 0 or stats.get('pdf', 0) == 0:
            analisis['errores'].append({'id': doc['id'], 'nombre': num_doc, 'diario': nombre_diario})
        else:
            analisis['comprobantes_ok'].append({'id': doc['id'], 'nombre': num_doc})

        if idx % 50 == 0 or idx == len(docs):
            print(f"   Progreso: {idx}/{len(docs)}")

    # Calcular duración
    t_final = datetime.now()
    duracion = t_final - t_inicio

    # Guardar reporte de errores al final
    guardar_resumen_errores(base_path_mes, año, mes, analisis, duracion=duracion)
    
    print(f"\n✅ Proceso completado en: {duracion}")
    print(f"Archivos en: {base_path_mes}")

if __name__ == "__main__":
    main()
