# -*- coding: utf-8 -*-
"""
Script AUTOMATIZADO para generar TODOS los PDFs de Guías de Remisión
Procesa todos los XMLs sin preguntar al usuario
"""

import xmlrpc.client
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configurar encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    parent_dirs = [Path(__file__).parent.parent, Path(__file__).parent.parent.parent]
    for parent_dir in parent_dirs:
        test_env = parent_dir / '.env'
        if test_env.exists():
            env_path = test_env
            break

load_dotenv(env_path)

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("❌ Error: Credenciales no encontradas")
    exit(1)

# Rutas
XML_PATH = r"C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias\Prueba_Octubre\09_Guias_Remision_V2\xml"
PDF_PATH = r"C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias\Prueba_Octubre\09_Guias_Remision_V2\pdf"

# ============================================================================
# FUNCIONES
# ============================================================================

def conectar_odoo():
    """Conectar a Odoo"""
    print(f"\n{'='*70}")
    print("🔄 CONECTANDO A ODOO")
    print(f"{'='*70}")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            print("❌ Error de autenticación")
            exit(1)
        
        print(f"✅ Conectado (UID: {uid})")
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        return uid, models
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)


def extraer_numero_de_xml(xml_path):
    """Extraer número de documento del XML o del nombre del archivo"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        namespaces = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }
        
        # Intentar extraer del XML
        ref_id = root.find('.//cbc:ReferenceID', namespaces)
        if ref_id is not None and ref_id.text:
            return ref_id.text.strip()
        
        doc_ref = root.find('.//cac:DocumentReference/cbc:ID', namespaces)
        if doc_ref is not None and doc_ref.text:
            return doc_ref.text.strip()
    except:
        pass
    
    # Usar nombre del archivo
    return Path(xml_path).stem


def buscar_guia_por_numero(uid, models, numero_doc):
    """Buscar guía en Odoo por número de documento"""
    try:
        guias = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'search_read',
            [[('l10n_latam_document_number', '=', numero_doc)]],
            {'fields': ['id'], 'limit': 1}
        )
        
        return guias[0]['id'] if guias else None
    except:
        return None


def extraer_datos_guia(uid, models, picking_id):
    """Extraer datos necesarios para el PDF"""
    try:
        picking = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'read',
            [[picking_id]],
            {
                'fields': [
                    'name', 'date_done', 'l10n_latam_document_number',
                    'type_operation_sunat', 'partner_id', 'company_id',
                    'note', 'move_ids_without_package'
                ]
            }
        )[0]
        
        datos = {'picking': picking}
        
        # Partner
        if picking.get('partner_id'):
            partner = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'read',
                [[picking['partner_id'][0]]],
                {'fields': ['name', 'vat', 'street', 'city']}
            )[0]
            datos['partner'] = partner
        
        # Company
        if picking.get('company_id'):
            company = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.company', 'read',
                [[picking['company_id'][0]]],
                {'fields': ['name', 'vat', 'street', 'city']}
            )[0]
            datos['company'] = company
        
        # Movimientos
        move_ids = picking.get('move_ids_without_package') or []
        if move_ids:
            moves = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'stock.move', 'read',
                [move_ids],
                {'fields': ['name', 'product_id', 'product_uom_qty', 'quantity_done', 'product_uom']}
            )
            datos['moves'] = moves
            
            # Productos
            product_ids = [m['product_id'][0] for m in moves if m.get('product_id')]
            if product_ids:
                products = models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'product.product', 'read',
                    [product_ids],
                    {'fields': ['id', 'name', 'default_code']}
                )
                datos['products'] = {p['id']: p for p in products}
        
        return datos
    except:
        return None


def generar_pdf_simple(datos, output_path):
    """Generar PDF usando reportlab"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    
    try:
        picking = datos.get('picking', {})
        partner = datos.get('partner', {})
        company = datos.get('company', {})
        moves = datos.get('moves', [])
        products = datos.get('products', {})
        
        numero_doc = picking.get('l10n_latam_document_number', 'SIN-NUMERO')
        nombre_archivo = f"{numero_doc.replace('/', '-')}.pdf"
        ruta_completa = Path(output_path) / nombre_archivo
        
        # Crear PDF
        doc = SimpleDocTemplate(str(ruta_completa), pagesize=A4,
                               rightMargin=20*mm, leftMargin=20*mm,
                               topMargin=20*mm, bottomMargin=20*mm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                     fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold')
        elements.append(Paragraph("GUÍA DE REMISIÓN ELECTRÓNICA", title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Emisor
        emisor_data = [
            [Paragraph("<b>EMISOR</b>", styles['Heading2'])],
            [f"RUC: {company.get('vat', 'N/A')}"],
            [f"Razón Social: {company.get('name', 'N/A')}"],
            [f"Dirección: {company.get('street', 'N/A')}"]
        ]
        emisor_table = Table(emisor_data, colWidths=[170*mm])
        emisor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(emisor_table)
        elements.append(Spacer(1, 5*mm))
        
        # Documento
        doc_data = [
            [Paragraph("<b>DOCUMENTO</b>", styles['Heading2']), ""],
            [f"Número: {numero_doc}", f"Fecha: {picking.get('date_done', 'N/A')}"],
            [f"Tipo Operación: {picking.get('type_operation_sunat', 'N/A')}", ""]
        ]
        doc_table = Table(doc_data, colWidths=[85*mm, 85*mm])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('SPAN', (0, 0), (-1, 0)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(doc_table)
        elements.append(Spacer(1, 5*mm))
        
        # Destinatario
        dest_data = [
            [Paragraph("<b>DESTINATARIO</b>", styles['Heading2'])],
            [f"RUC/DNI: {partner.get('vat', 'N/A')}"],
            [f"Nombre: {partner.get('name', 'N/A')}"],
            [f"Dirección: {partner.get('street', 'N/A')}"]
        ]
        dest_table = Table(dest_data, colWidths=[170*mm])
        dest_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(dest_table)
        elements.append(Spacer(1, 5*mm))
        
        # Productos
        elements.append(Paragraph("<b>DETALLE DE PRODUCTOS</b>", styles['Heading2']))
        elements.append(Spacer(1, 3*mm))
        
        prod_data = [["Código", "Descripción", "Cantidad", "Unidad"]]
        for move in moves:
            product_id = move.get('product_id', [False])[0] if move.get('product_id') else None
            product = products.get(product_id, {})
            
            codigo = product.get('default_code', '-')
            descripcion = move.get('name', 'N/A')[:60]
            cantidad = move.get('quantity_done', 0) or move.get('product_uom_qty', 0)
            unidad = move.get('product_uom', [False, 'UND'])[1] if move.get('product_uom') else 'UND'
            
            prod_data.append([str(codigo), str(descripcion), str(cantidad), str(unidad)])
        
        prod_table = Table(prod_data, colWidths=[30*mm, 90*mm, 25*mm, 25*mm])
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(prod_table)
        
        # Generar
        doc.build(elements)
        return ruta_completa
    except:
        return None


# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{'#'*70}")
    print("# GENERACIÓN AUTOMÁTICA DE TODOS LOS PDFs")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # Crear carpeta PDF
    Path(PDF_PATH).mkdir(parents=True, exist_ok=True)
    
    # Listar XMLs
    xml_files = sorted(Path(XML_PATH).glob("*.xml"))
    print(f"\n📋 Encontrados: {len(xml_files)} archivos XML")
    
    if not xml_files:
        print("❌ No se encontraron archivos XML")
        return
    
    # Conectar a Odoo
    uid, models = conectar_odoo()
    
    # Procesar TODOS
    stats = {
        'total': len(xml_files),
        'exitosos': 0,
        'errores': 0,
        'no_encontrados': 0,
        'ya_existen': 0
    }
    
    print(f"\n{'='*70}")
    print(f"PROCESANDO {len(xml_files)} GUÍAS")
    print(f"{'='*70}\n")
    
    for idx, xml_file in enumerate(xml_files, 1):
        numero_doc = extraer_numero_de_xml(xml_file)
        
        # Verificar si ya existe el PDF
        pdf_existente = Path(PDF_PATH) / f"{numero_doc}.pdf"
        if pdf_existente.exists():
            stats['ya_existen'] += 1
            if idx <= 5 or idx % 100 == 0:
                print(f"[{idx}/{len(xml_files)}] {numero_doc} - Ya existe")
            continue
        
        # Mostrar progreso
        if idx <= 10 or idx % 50 == 0:
            print(f"[{idx}/{len(xml_files)}] {numero_doc}")
        
        # Buscar en Odoo
        picking_id = buscar_guia_por_numero(uid, models, numero_doc)
        if not picking_id:
            stats['no_encontrados'] += 1
            if idx <= 5:
                print(f"   ⚠️  No encontrada en Odoo")
            continue
        
        # Extraer datos
        datos = extraer_datos_guia(uid, models, picking_id)
        if not datos:
            stats['errores'] += 1
            continue
        
        # Generar PDF
        pdf_path = generar_pdf_simple(datos, PDF_PATH)
        if pdf_path:
            stats['exitosos'] += 1
            if idx <= 10:
                print(f"   ✅ PDF generado")
        else:
            stats['errores'] += 1
        
        # Progreso cada 100
        if idx % 100 == 0:
            print(f"\n📊 Progreso: {idx}/{len(xml_files)} | Generados: {stats['exitosos']} | Errores: {stats['errores']}\n")
    
    # Resumen
    print(f"\n{'='*70}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"📦 Total procesados: {stats['total']}")
    print(f"✅ PDFs generados: {stats['exitosos']}")
    print(f"📄 Ya existían: {stats['ya_existen']}")
    print(f"⚠️  No encontrados en Odoo: {stats['no_encontrados']}")
    print(f"❌ Errores: {stats['errores']}")
    print(f"\n📂 PDFs guardados en: {PDF_PATH}")
    print(f"{'='*70}\n")
    print("✅ ¡Proceso completado!")


if __name__ == "__main__":
    main()

