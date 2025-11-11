# -*- coding: utf-8 -*-
"""
Script para descarga de Guías de Remisión Electrónicas - ANÁLISIS Y DESCARGA
Investigará el modelo correcto y descargará PDFs y XMLs
"""

import xmlrpc.client
import os
import base64
import sys
import zipfile
import io
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

BASE_PATH = r"C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias\Prueba_Octubre\09_Guias_Remision"

# Filtros específicos del usuario
PICKING_TYPE_ID = 2
TYPE_OPERATION_SUNAT = "01"

# ============================================================================
# FUNCIONES DE ANÁLISIS
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


def analizar_modelos(uid, models):
    """Analizar qué modelo usar: stock.picking vs stock.picking.report"""
    print(f"\n{'='*70}")
    print("🔍 ANÁLISIS DE MODELOS DISPONIBLES")
    print(f"{'='*70}")
    
    modelos_info = {}
    
    # 1. Analizar stock.picking
    print("\n1️⃣  Analizando modelo: stock.picking")
    try:
        campos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'fields_get',
            [],
            {'attributes': ['string', 'type']}
        )
        
        campos_relevantes = [k for k in campos.keys() if 'latam' in k.lower() or 'sunat' in k.lower()]
        
        print(f"   ✅ Campos encontrados relacionados:")
        for campo in campos_relevantes:
            print(f"      • {campo}: {campos[campo].get('string', '')}")
        
        # Probar búsqueda con filtros
        domain_test = [
            ('state', '=', 'done'),
            ('picking_type_id', '=', PICKING_TYPE_ID),
            ('l10n_latam_document_number', '!=', False),
            ('type_operation_sunat', '=', TYPE_OPERATION_SUNAT),
            ('date_done', '>=', f'{FECHA_INICIO} 00:00:00'),
            ('date_done', '<=', f'{FECHA_FIN} 23:59:59'),
        ]
        
        count = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking', 'search_count',
            [domain_test]
        )
        
        print(f"   📊 Registros encontrados con filtros: {count}")
        modelos_info['stock.picking'] = count
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        modelos_info['stock.picking'] = 0
    
    # 2. Analizar stock.picking.report
    print("\n2️⃣  Analizando modelo: stock.picking.report")
    try:
        campos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking.report', 'fields_get',
            [],
            {'attributes': ['string', 'type']}
        )
        
        print(f"   ✅ Campos disponibles:")
        campos_mostrar = list(campos.keys())[:15]
        for campo in campos_mostrar:
            print(f"      • {campo}: {campos[campo].get('string', '')}")
        
        # Este es un modelo de reporte, puede tener estructura diferente
        count = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'stock.picking.report', 'search_count',
            [[]]
        )
        
        print(f"   📊 Total de registros: {count}")
        modelos_info['stock.picking.report'] = count
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        modelos_info['stock.picking.report'] = 0
    
    return modelos_info


def obtener_guias_correctas(uid, models):
    """Obtener guías con los filtros correctos"""
    print(f"\n{'='*70}")
    print("🔍 OBTENIENDO GUÍAS CON FILTROS ESPECÍFICOS")
    print(f"{'='*70}")
    print(f"📅 Período: {FECHA_INICIO} al {FECHA_FIN}")
    print(f"🎯 Filtros:")
    print(f"   • state = done")
    print(f"   • picking_type_id = {PICKING_TYPE_ID}")
    print(f"   • l10n_latam_document_number != False")
    print(f"   • type_operation_sunat = {TYPE_OPERATION_SUNAT}")
    
    try:
        # Usar stock.picking (modelo principal)
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
                'fields': [
                    'id', 'name', 'date_done', 'partner_id', 'origin',
                    'l10n_latam_document_number', 'type_operation_sunat',
                    'picking_type_id', 'state'
                ],
                'order': 'date_done asc'
            }
        )
        
        print(f"\n✅ Encontradas: {len(guias)} guías")
        
        if guias:
            print(f"\n📋 Primeras 5 guías:")
            for idx, g in enumerate(guias[:5], 1):
                print(f"   {idx}. {g['name']} | Doc: {g.get('l10n_latam_document_number', 'N/A')}")
        
        return guias
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def crear_carpetas():
    """Crear estructura de carpetas"""
    print(f"\n{'='*70}")
    print("📁 CREANDO CARPETAS")
    print(f"{'='*70}")
    
    for tipo in ['pdf', 'xml']:
        ruta = Path(BASE_PATH) / tipo
        ruta.mkdir(parents=True, exist_ok=True)
        print(f"✅ {ruta}")


def buscar_reporte_eguia(uid, models):
    """Buscar el reporte de e-Guía AGR"""
    # El nombre exacto del reporte es: agr_shiping_guide.report_edi_gre
    return 'agr_shiping_guide.report_edi_gre'


def generar_pdf_guia(uid, models, picking_id, reporte_nombre):
    """Generar PDF de guía"""
    errores = []
    
    if not reporte_nombre:
        return None, ["No se proporcionó nombre de reporte"]
    
    # Intentar con _render_qweb_pdf
    try:
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.actions.report', '_render_qweb_pdf',
            [reporte_nombre, [picking_id]]
        )
        if result and len(result) > 0 and result[0]:
            return result[0], None
    except Exception as e:
        errores.append(f"_render_qweb_pdf: {str(e)[:100]}")
    
    # Intentar con render_qweb_pdf
    try:
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.actions.report', 'render_qweb_pdf',
            [reporte_nombre, [picking_id]]
        )
        if result and len(result) > 0 and result[0]:
            return result[0], None
    except Exception as e:
        errores.append(f"render_qweb_pdf: {str(e)[:100]}")
    
    # Intentar método alternativo con report_action
    try:
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.actions.report', 'report_action',
            [[picking_id]],
            {'report_name': reporte_nombre}
        )
        if result and isinstance(result, dict):
            return None, ["report_action retornó diccionario (modo interactivo)"]
    except Exception as e:
        errores.append(f"report_action: {str(e)[:100]}")
    
    return None, errores


def buscar_adjuntos(uid, models, picking_id):
    """Buscar adjuntos (PDF y XML) de la guía"""
    try:
        adjuntos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking_id)
            ]],
            {'fields': ['id', 'name', 'datas', 'mimetype', 'description']}
        )
        return adjuntos
    except:
        return []


def buscar_pdf_eguia_agr(adjuntos):
    """Buscar específicamente el PDF de 'e-Guía de Remisión AGR' entre los adjuntos"""
    # Buscar por nombre que contenga indicadores del reporte AGR
    for adj in adjuntos:
        nombre = adj.get('name', '').lower()
        descripcion = adj.get('description', '').lower() if adj.get('description') else ''
        
        # Buscar PDF con indicadores de e-Guía AGR
        if adj.get('mimetype') == 'application/pdf' or nombre.endswith('.pdf'):
            # Verificar si es el PDF de e-Guía
            if any(keyword in nombre for keyword in ['e-guia', 'eguia', 'agr', 'remision', 'delivery']):
                return adj
            if 'agr' in descripcion or 'e-guía' in descripcion:
                return adj
    
    # Si no se encuentra específicamente, retornar el primer PDF
    for adj in adjuntos:
        if adj.get('mimetype') == 'application/pdf' or adj.get('name', '').lower().endswith('.pdf'):
            return adj
    
    return None


def descargar_guias(uid, models, guias):
    """Descargar PDFs (método e-Guía AGR) y XMLs de las guías"""
    print(f"\n{'='*70}")
    print("📥 DESCARGANDO GUÍAS DE REMISIÓN")
    print(f"{'='*70}")
    print("💡 Estrategia:")
    print("   1. Buscar PDF 'e-Guía de Remisión AGR' en adjuntos")
    print("   2. Si no existe, intentar generarlo dinámicamente")
    print("   3. Descargar XMLs adjuntos")
    
    # Buscar reporte como fallback
    print("\n🔍 Buscando reporte de e-Guía para generación dinámica...")
    reporte = buscar_reporte_eguia(uid, models)
    if reporte:
        print(f"✅ Reporte disponible: {reporte}")
    else:
        print("⚠️  No se encontró reporte, solo se descargarán PDFs existentes")
    
    stats = {
        'total': len(guias),
        'pdf_descargados': 0,
        'pdf_generados': 0,
        'xml_descargados': 0,
        'sin_pdf': 0,
        'errores': 0
    }
    
    for idx, guia in enumerate(guias, 1):
        guia_id = guia['id']
        numero_doc = guia.get('l10n_latam_document_number', f"GUIA_{guia_id}")
        nombre_base = numero_doc.replace('/', '-').replace('\\', '-')
        
        mostrar_detalle = (idx <= 10 or idx % 50 == 1)
        
        if mostrar_detalle:
            print(f"\n[{idx}/{len(guias)}] {guia['name']} | Doc: {numero_doc}")
        
        pdf_obtenido = False
        
        # PASO 1: Buscar adjuntos (PDF y XML)
        adjuntos = buscar_adjuntos(uid, models, guia_id)
        
        # PASO 2: Buscar PDF de e-Guía AGR en los adjuntos
        pdf_eguia = buscar_pdf_eguia_agr(adjuntos)
        if pdf_eguia and pdf_eguia.get('datas'):
            try:
                ruta_pdf = Path(BASE_PATH) / 'pdf' / f"{nombre_base}.pdf"
                content = base64.b64decode(pdf_eguia['datas'])
                with open(ruta_pdf, 'wb') as f:
                    f.write(content)
                stats['pdf_descargados'] += 1
                pdf_obtenido = True
                if mostrar_detalle:
                    print(f"   ✅ PDF descargado: {pdf_eguia.get('name', nombre_base + '.pdf')}")
            except Exception as e:
                if mostrar_detalle:
                    print(f"   ⚠️  Error descargando PDF: {str(e)[:50]}")
        
        # PASO 3: Si no hay PDF, intentar generarlo (solo si tenemos reporte)
        if not pdf_obtenido and reporte:
            try:
                pdf_content, errores = generar_pdf_guia(uid, models, guia_id, reporte)
                if pdf_content:
                    ruta_pdf = Path(BASE_PATH) / 'pdf' / f"{nombre_base}.pdf"
                    with open(ruta_pdf, 'wb') as f:
                        f.write(pdf_content)
                    stats['pdf_generados'] += 1
                    pdf_obtenido = True
                    if mostrar_detalle:
                        print(f"   ✅ PDF generado: {nombre_base}.pdf")
                elif errores and idx <= 3:  # Solo mostrar errores en las primeras 3
                    print(f"   ⚠️  No se pudo generar PDF:")
                    for error in errores[:1]:
                        print(f"      • {error}")
            except Exception as e:
                if idx <= 3:
                    print(f"   ❌ Error generando PDF: {str(e)[:50]}")
        
        if not pdf_obtenido:
            stats['sin_pdf'] += 1
        
        # PASO 4: Descargar XMLs
        for adj in adjuntos:
            if adj.get('name', '').lower().endswith('.xml'):
                try:
                    ruta_xml = Path(BASE_PATH) / 'xml' / f"{nombre_base}.xml"
                    if not ruta_xml.exists() and adj.get('datas'):
                        content = base64.b64decode(adj['datas'])
                        with open(ruta_xml, 'wb') as f:
                            f.write(content)
                        stats['xml_descargados'] += 1
                        if mostrar_detalle:
                            print(f"   ✅ XML: {adj.get('name', nombre_base + '.xml')}")
                except Exception as e:
                    if mostrar_detalle:
                        print(f"   ⚠️  Error XML: {str(e)[:50]}")
        
        if idx % 100 == 0:
            total_pdfs = stats['pdf_descargados'] + stats['pdf_generados']
            print(f"\n   💾 Progreso: {idx}/{len(guias)}")
            print(f"   📊 PDFs: {total_pdfs} (descargados: {stats['pdf_descargados']}, generados: {stats['pdf_generados']}) | XMLs: {stats['xml_descargados']}")
    
    return stats


def mostrar_resumen(stats):
    """Mostrar resumen"""
    print(f"\n{'='*70}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"📦 Total de guías procesadas: {stats['total']}")
    print(f"\n📄 Archivos PDF:")
    print(f"   • PDFs descargados (e-Guía AGR): {stats['pdf_descargados']}")
    print(f"   • PDFs generados dinámicamente: {stats['pdf_generados']}")
    print(f"   • TOTAL PDFs: {stats['pdf_descargados'] + stats['pdf_generados']}")
    print(f"   • Sin PDF: {stats['sin_pdf']}")
    print(f"\n📄 Archivos XML:")
    print(f"   • XMLs descargados: {stats['xml_descargados']}")
    print(f"\n❌ Errores: {stats['errores']}")
    print(f"\n📂 Ubicación: {BASE_PATH}")
    print(f"   • Carpeta PDF: {Path(BASE_PATH) / 'pdf'}")
    print(f"   • Carpeta XML: {Path(BASE_PATH) / 'xml'}")
    print(f"{'='*70}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{'#'*70}")
    print("# DESCARGA DE GUÍAS DE REMISIÓN ELECTRÓNICAS")
    print(f"# Análisis + Descarga con filtros específicos")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    uid, models = conectar_odoo()
    
    # PASO 1: Análisis de modelos
    modelos_info = analizar_modelos(uid, models)
    
    # PASO 2: Obtener guías con filtros correctos
    guias = obtener_guias_correctas(uid, models)
    
    if not guias:
        print("\n⚠️  No se encontraron guías con los filtros especificados")
        return
    
    # PASO 3: Crear carpetas
    crear_carpetas()
    
    # PASO 4: Descargar
    stats = descargar_guias(uid, models, guias)
    
    # PASO 5: Resumen
    mostrar_resumen(stats)
    
    print("✅ ¡Completado!")


if __name__ == "__main__":
    main()
