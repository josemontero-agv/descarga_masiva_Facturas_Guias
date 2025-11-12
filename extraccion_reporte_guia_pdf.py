# -*- coding: utf-8 -*-
"""
Script para extraer datos de Odoo y generar PDFs de Guías de Remisión localmente
Replica el reporte: agr_shiping_guide.report_edi_gre

Estrategia:
1. Conectar a Odoo via XML-RPC
2. Extraer TODOS los datos necesarios del modelo stock.picking
3. Analizar estructura del reporte QWeb
4. Generar PDF localmente usando reportlab/weasyprint
5. Guardar en carpeta especificada
"""

import xmlrpc.client
import os
import sys
import base64
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configurar encoding para Windows
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

# Configuración
AÑO = 2025
MES = 10

from calendar import monthrange
ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"

OUTPUT_PATH = r"C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias\Prueba_Octubre\09_Guias_Remision_V2\pdf"

# Filtros específicos
PICKING_TYPE_ID = 2
TYPE_OPERATION_SUNAT = "01"

# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================

def conectar_odoo():
    """Conectar a Odoo"""
    print(f"\n{'='*70}")
    print("🔄 CONECTANDO A ODOO")
    print(f"{'='*70}")
    print(f"📡 URL: {ODOO_URL}")
    
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


# ============================================================================
# FUNCIONES DE ANÁLISIS DEL REPORTE
# ============================================================================

def analizar_reporte_qweb(uid, models):
    """
    Analizar el reporte QWeb para entender su estructura
    Nombre del reporte: agr_shiping_guide.report_edi_gre
    """
    print(f"\n{'='*70}")
    print("🔍 ANALIZANDO REPORTE QWEB")
    print(f"{'='*70}")
    print("📋 Reporte: agr_shiping_guide.report_edi_gre")
    
    reporte_info = {}
    
    try:
        # 1. Buscar el reporte en ir.actions.report
        reportes = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.actions.report', 'search_read',
            [[('report_name', '=', 'agr_shiping_guide.report_edi_gre')]],
            {'fields': ['id', 'name', 'model', 'report_name', 'report_type']}
        )
        
        if reportes:
            reporte = reportes[0]
            print(f"\n✅ Reporte encontrado:")
            print(f"   • ID: {reporte['id']}")
            print(f"   • Nombre: {reporte['name']}")
            print(f"   • Modelo: {reporte['model']}")
            print(f"   • Tipo: {reporte['report_type']}")
            reporte_info['reporte'] = reporte
        else:
            print("⚠️  Reporte no encontrado en ir.actions.report")
            return None
        
        # 2. Obtener campos disponibles del modelo stock.picking
        print(f"\n🔍 Analizando campos del modelo: {reporte['model']}")
        campos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            reporte['model'], 'fields_get',
            [],
            {'attributes': ['string', 'type', 'relation']}
        )
        
        # Filtrar campos relevantes para guías de remisión
        campos_relevantes = {}
        keywords = [
            'latam', 'sunat', 'partner', 'picking', 'move', 'location',
            'carrier', 'transport', 'address', 'delivery', 'date',
            'document', 'warehouse', 'company', 'origin', 'note'
        ]
        
        for campo, info in campos.items():
            if any(keyword in campo.lower() for keyword in keywords):
                campos_relevantes[campo] = info
        
        print(f"\n📋 Campos relevantes encontrados ({len(campos_relevantes)}):")
        for campo, info in sorted(campos_relevantes.items())[:30]:
            tipo = info.get('type', 'unknown')
            desc = info.get('string', campo)
            print(f"   • {campo:40} | {tipo:15} | {desc}")
        
        if len(campos_relevantes) > 30:
            print(f"   ... y {len(campos_relevantes) - 30} más")
        
        reporte_info['campos_relevantes'] = list(campos_relevantes.keys())
        
        return reporte_info
        
    except Exception as e:
        print(f"❌ Error analizando reporte: {e}")
        import traceback
        traceback.print_exc()
        return None


def extraer_datos_completos_guia(uid, models, picking_id):
    """
    Extraer TODOS los datos necesarios de una guía para generar el PDF
    """
    print(f"\n{'='*70}")
    print(f"📦 EXTRAYENDO DATOS COMPLETOS DE GUÍA ID: {picking_id}")
    print(f"{'='*70}")
    
    datos = {}
    
    try:
        # 1. Datos principales del picking
        print("📋 1. Datos principales del stock.picking...")
        picking = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'read',
            [[picking_id]],
            {
                'fields': [
                    # Identificación
                    'id', 'name', 'origin', 'state',
                    
                    # Fechas
                    'date_done', 'scheduled_date', 'date_deadline',
                    
                    # Documento SUNAT
                    'l10n_latam_document_type_id', 'l10n_latam_document_number',
                    'type_operation_sunat',
                    
                    # Partners y direcciones
                    'partner_id', 'company_id', 
                    'location_id', 'location_dest_id',
                    
                    # Transporte
                    'carrier_id', 'carrier_tracking_ref',
                    
                    # Otros
                    'picking_type_id', 'note',
                    'move_ids_without_package',
                    
                    # Campos específicos AGR (si existen)
                    'x_studio_motivo_traslado', 'x_studio_punto_partida',
                    'x_studio_punto_llegada', 'x_studio_conductor',
                    'x_studio_vehiculo', 'x_studio_peso_bruto'
                ]
            }
        )
        
        if picking:
            datos['picking'] = picking[0]
            print(f"   ✅ Datos del picking extraídos")
        
        # 2. Datos del partner (destinatario)
        if datos['picking'].get('partner_id'):
            partner_id = datos['picking']['partner_id'][0]
            print(f"📋 2. Datos del partner (ID: {partner_id})...")
            partner = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'read',
                [[partner_id]],
                {
                    'fields': [
                        'name', 'vat', 'street', 'street2', 'city', 
                        'state_id', 'country_id', 'zip', 'phone', 'email',
                        'l10n_latam_identification_type_id'
                    ]
                }
            )
            if partner:
                datos['partner'] = partner[0]
                print(f"   ✅ Datos del partner extraídos")
        
        # 3. Datos de la compañía (emisor)
        if datos['picking'].get('company_id'):
            company_id = datos['picking']['company_id'][0]
            print(f"📋 3. Datos de la compañía (ID: {company_id})...")
            company = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.company', 'read',
                [[company_id]],
                {
                    'fields': [
                        'name', 'vat', 'street', 'street2', 'city',
                        'state_id', 'country_id', 'zip', 'phone', 'email',
                        'logo', 'partner_id'
                    ]
                }
            )
            if company:
                datos['company'] = company[0]
                print(f"   ✅ Datos de la compañía extraídos")
        
        # 4. Líneas de movimiento (productos)
        move_ids = datos['picking'].get('move_ids_without_package') or []
        if move_ids:
            print(f"📋 4. Líneas de movimiento ({len(move_ids)} productos)...")
            moves = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'stock.move', 'read',
                [move_ids],
                {
                    'fields': [
                        'id', 'name', 'product_id', 'product_uom_qty',
                        'product_uom', 'quantity_done', 'description_picking'
                    ]
                }
            )
            if moves:
                datos['moves'] = moves
                print(f"   ✅ {len(moves)} líneas extraídas")
                
                # Extraer detalles de productos
                product_ids = [m['product_id'][0] for m in moves if m.get('product_id')]
                if product_ids:
                    products = models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'product.product', 'read',
                        [product_ids],
                        {'fields': ['id', 'name', 'default_code', 'barcode', 'weight']}
                    )
                    datos['products'] = {p['id']: p for p in products}
        
        # 5. Ubicaciones
        if datos['picking'].get('location_id'):
            location_id = datos['picking']['location_id'][0]
            location = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'stock.location', 'read',
                [[location_id]],
                {'fields': ['id', 'name', 'complete_name']}
            )
            if location:
                datos['location_origen'] = location[0]
        
        if datos['picking'].get('location_dest_id'):
            location_dest_id = datos['picking']['location_dest_id'][0]
            location_dest = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'stock.location', 'read',
                [[location_dest_id]],
                {'fields': ['id', 'name', 'complete_name']}
            )
            if location_dest:
                datos['location_destino'] = location_dest[0]
        
        print(f"\n✅ Extracción completa finalizada")
        print(f"📊 Secciones extraídas:")
        for key in datos.keys():
            print(f"   • {key}")
        
        return datos
        
    except Exception as e:
        print(f"❌ Error extrayendo datos: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# FUNCIONES DE GENERACIÓN DE PDF
# ============================================================================

def generar_pdf_guia_local(datos, output_path):
    """
    Generar PDF de guía de remisión localmente usando reportlab
    Replica el formato del reporte agr_shiping_guide.report_edi_gre
    """
    print(f"\n{'='*70}")
    print("📄 GENERANDO PDF LOCALMENTE")
    print(f"{'='*70}")
    
    try:
        # Verificar si reportlab está instalado
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            print("✅ Biblioteca reportlab disponible")
        except ImportError:
            print("⚠️  reportlab no está instalada. Instalando...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Preparar datos
        picking = datos.get('picking', {})
        partner = datos.get('partner', {})
        company = datos.get('company', {})
        moves = datos.get('moves', [])
        products = datos.get('products', {})
        
        numero_doc = picking.get('l10n_latam_document_number', 'SIN-NUMERO')
        nombre_archivo = f"{numero_doc.replace('/', '-')}.pdf"
        ruta_completa = Path(output_path) / nombre_archivo
        
        print(f"📋 Generando: {nombre_archivo}")
        
        # Crear PDF
        doc = SimpleDocTemplate(str(ruta_completa), pagesize=A4,
                               rightMargin=20*mm, leftMargin=20*mm,
                               topMargin=20*mm, bottomMargin=20*mm)
        
        # Elementos del PDF
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para encabezados
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            fontName='Helvetica-Bold'
        )
        
        # Estilo para contenido
        normal_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555')
        )
        
        # === ENCABEZADO ===
        # Título del documento
        elements.append(Paragraph("GUÍA DE REMISIÓN ELECTRÓNICA", title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Información de la empresa (emisor)
        empresa_data = [
            [Paragraph("<b>EMISOR</b>", header_style)],
            [Paragraph(f"<b>RUC:</b> {company.get('vat', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Razón Social:</b> {company.get('name', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Dirección:</b> {company.get('street', 'N/A')}", normal_style)],
        ]
        
        empresa_table = Table(empresa_data, colWidths=[170*mm])
        empresa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(empresa_table)
        elements.append(Spacer(1, 5*mm))
        
        # Información del documento
        doc_data = [
            [Paragraph("<b>DOCUMENTO</b>", header_style), ""],
            [Paragraph("<b>Número:</b>", normal_style), Paragraph(f"{numero_doc}", normal_style)],
            [Paragraph("<b>Fecha Emisión:</b>", normal_style), 
             Paragraph(f"{picking.get('date_done', 'N/A')}", normal_style)],
            [Paragraph("<b>Tipo Operación:</b>", normal_style), 
             Paragraph(f"{picking.get('type_operation_sunat', 'N/A')}", normal_style)],
        ]
        
        doc_table = Table(doc_data, colWidths=[85*mm, 85*mm])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('SPAN', (0, 0), (-1, 0)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(doc_table)
        elements.append(Spacer(1, 5*mm))
        
        # Información del destinatario
        destinatario_data = [
            [Paragraph("<b>DESTINATARIO</b>", header_style)],
            [Paragraph(f"<b>RUC/DNI:</b> {partner.get('vat', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Nombre:</b> {partner.get('name', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Dirección:</b> {partner.get('street', 'N/A')}", normal_style)],
        ]
        
        destinatario_table = Table(destinatario_data, colWidths=[170*mm])
        destinatario_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(destinatario_table)
        elements.append(Spacer(1, 5*mm))
        
        # Detalle de productos
        elements.append(Paragraph("<b>DETALLE DE PRODUCTOS</b>", header_style))
        elements.append(Spacer(1, 3*mm))
        
        productos_data = [
            [
                Paragraph("<b>Código</b>", normal_style),
                Paragraph("<b>Descripción</b>", normal_style),
                Paragraph("<b>Cantidad</b>", normal_style),
                Paragraph("<b>Unidad</b>", normal_style)
            ]
        ]
        
        for move in moves:
            product_id = move.get('product_id', [False, 'N/A'])[0]
            product = products.get(product_id, {})
            
            codigo = product.get('default_code', '-')
            descripcion = move.get('name', 'N/A')
            cantidad = move.get('quantity_done', 0) or move.get('product_uom_qty', 0)
            unidad = move.get('product_uom', [False, 'UND'])[1]
            
            productos_data.append([
                Paragraph(str(codigo), normal_style),
                Paragraph(str(descripcion)[:60], normal_style),
                Paragraph(str(cantidad), normal_style),
                Paragraph(str(unidad), normal_style)
            ])
        
        productos_table = Table(productos_data, colWidths=[30*mm, 90*mm, 25*mm, 25*mm])
        productos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(productos_table)
        elements.append(Spacer(1, 5*mm))
        
        # Observaciones
        if picking.get('note'):
            elements.append(Paragraph("<b>OBSERVACIONES</b>", header_style))
            elements.append(Paragraph(picking.get('note', ''), normal_style))
        
        # Generar PDF
        doc.build(elements)
        
        print(f"✅ PDF generado: {ruta_completa}")
        return ruta_completa
        
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def obtener_guias(uid, models):
    """Obtener guías del período especificado"""
    print(f"\n{'='*70}")
    print("🔍 OBTENIENDO GUÍAS DEL PERÍODO")
    print(f"{'='*70}")
    print(f"📅 Período: {FECHA_INICIO} al {FECHA_FIN}")
    
    try:
        domain = [
            ('state', '=', 'done'),
            ('picking_type_id', '=', PICKING_TYPE_ID),
            ('l10n_latam_document_number', '!=', False),
            ('type_operation_sunat', '=', TYPE_OPERATION_SUNAT),
            ('date_done', '>=', f'{FECHA_INICIO} 00:00:00'),
            ('date_done', '<=', f'{FECHA_FIN} 23:59:59'),
        ]
        
        guias = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'search_read',
            [domain],
            {
                'fields': ['id', 'name', 'l10n_latam_document_number'],
                'order': 'date_done asc'
            }
        )
        
        print(f"\n✅ Encontradas: {len(guias)} guías")
        return guias
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def main():
    """Función principal"""
    print(f"\n{'#'*70}")
    print("# EXTRACCIÓN Y GENERACIÓN LOCAL DE PDFs DE GUÍAS")
    print(f"# Análisis del reporte: agr_shiping_guide.report_edi_gre")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # Crear carpeta de salida
    Path(OUTPUT_PATH).mkdir(parents=True, exist_ok=True)
    
    # Conectar a Odoo
    uid, models = conectar_odoo()
    
    # PASO 1: Analizar reporte QWeb
    print("\n" + "="*70)
    print("PASO 1: ANÁLISIS DEL REPORTE QWEB")
    print("="*70)
    reporte_info = analizar_reporte_qweb(uid, models)
    
    if not reporte_info:
        print("\n⚠️  No se pudo analizar el reporte")
        respuesta = input("\n¿Continuar de todas formas? (s/n): ")
        if respuesta.lower() != 's':
            return
    
    # PASO 2: Obtener guías
    print("\n" + "="*70)
    print("PASO 2: OBTENCIÓN DE GUÍAS")
    print("="*70)
    guias = obtener_guias(uid, models)
    
    if not guias:
        print("\n⚠️  No se encontraron guías")
        return
    
    # Preguntar cuántas procesar
    print(f"\n📊 Se encontraron {len(guias)} guías")
    print("Opciones:")
    print("  1. Procesar solo la primera guía (análisis)")
    print("  2. Procesar las primeras 10 guías (prueba)")
    print(f"  3. Procesar TODAS las {len(guias)} guías")
    
    opcion = input("\nSelecciona una opción (1-3): ").strip()
    
    if opcion == '1':
        guias_procesar = guias[:1]
    elif opcion == '2':
        guias_procesar = guias[:10]
    else:
        guias_procesar = guias
    
    # PASO 3: Procesar guías
    print("\n" + "="*70)
    print(f"PASO 3: PROCESAMIENTO DE {len(guias_procesar)} GUÍAS")
    print("="*70)
    
    stats = {
        'total': len(guias_procesar),
        'exitosos': 0,
        'errores': 0
    }
    
    for idx, guia in enumerate(guias_procesar, 1):
        print(f"\n{'='*70}")
        print(f"📦 PROCESANDO GUÍA {idx}/{len(guias_procesar)}")
        print(f"{'='*70}")
        print(f"ID: {guia['id']} | {guia['name']} | Doc: {guia.get('l10n_latam_document_number')}")
        
        # Extraer datos completos
        datos = extraer_datos_completos_guia(uid, models, guia['id'])
        
        if not datos:
            print("❌ No se pudieron extraer los datos")
            stats['errores'] += 1
            continue
        
        # Generar PDF
        pdf_path = generar_pdf_guia_local(datos, OUTPUT_PATH)
        
        if pdf_path:
            stats['exitosos'] += 1
            print(f"✅ PDF generado exitosamente")
        else:
            stats['errores'] += 1
            print(f"❌ Error generando PDF")
    
    # Resumen final
    print(f"\n{'='*70}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"📦 Total procesadas: {stats['total']}")
    print(f"✅ Exitosas: {stats['exitosos']}")
    print(f"❌ Errores: {stats['errores']}")
    print(f"\n📂 PDFs guardados en: {OUTPUT_PATH}")
    print(f"{'='*70}\n")
    
    print("✅ ¡Proceso completado!")


if __name__ == "__main__":
    main()

