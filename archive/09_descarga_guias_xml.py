# -*- coding: utf-8 -*-
"""
Script para descarga de XMLs de Guías de Remisión Electrónicas desde Odoo
Descarga los archivos XML adjuntos de las guías (funcional)
NOTA: Para PDFs de guías, usar el script de web scraping
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

# ============================================
# CONFIGURACIÓN DE AMBIENTE
# ============================================
# Cambiar entre "desarrollo" y "produccion"
AMBIENTE = "produccion"  # ← CAMBIAR AQUÍ: "desarrollo" o "produccion"

# Cargar variables de entorno según ambiente
env_file = f'.env.{AMBIENTE}'
# Buscar en la raíz del proyecto (3 niveles arriba desde scripts/documentos/)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / env_file

if not env_path.exists():
    # Intentar buscar en directorios padres
    parent_dirs = [Path(__file__).parent.parent, project_root]
    for parent_dir in parent_dirs:
        test_env = parent_dir / env_file
        if test_env.exists():
            env_path = test_env
            break

if not env_path.exists():
    print(f"❌ Error: No se encontró el archivo '{env_file}'")
    print(f"💡 Crea el archivo con las credenciales de Odoo")
    print(f"   Archivos disponibles:")
    print(f"   - .env.desarrollo  (para pruebas)")
    print(f"   - .env.produccion  (para ambiente real)")
    exit(1)

print(f"📁 Cargando configuración desde: {env_path} (Ambiente: {AMBIENTE})")
load_dotenv(env_path, override=True)

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("❌ Error: Credenciales no encontradas")
    exit(1)

# Configuración
AÑO = 2026
MES = 2

from calendar import monthrange
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
    
    # Verificar acceso a la ruta de red
    if not Path(BASE_PATH_RAIZ).parent.parent.exists():
        print(f"❌ Error: No se puede acceder a la ruta de red V:")
        print(f"   {BASE_PATH_RAIZ}")
        # No salimos drásticamente para permitir pruebas si el usuario quiere, pero advertimos
else:
    BASE_PATH_RAIZ = project_root / "Prueba_Octubre" / nombre_carpeta_mes
    print(f"🔧 MODO DESARROLLO: Guardando en ruta local: {BASE_PATH_RAIZ}")

# Ruta específica para Guías
BASE_PATH = Path(BASE_PATH_RAIZ) / "09_Guias_Remision"

# Crear carpeta raíz si no existe
try:
    BASE_PATH.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️  No se pudo crear la carpeta base: {e}")

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
    
    subcarpetas = ['xml', 'cdr']
    
    for tipo in subcarpetas:
        ruta = Path(BASE_PATH) / tipo
        try:
            ruta.mkdir(parents=True, exist_ok=True)
            print(f"✅ Carpeta verificada: {ruta}")
        except OSError as e:
            print(f"❌ Error crítico creando carpeta {tipo}: {e}")


def buscar_reporte_eguia(uid, models):
    """Buscar el reporte de e-Guía AGR"""
    # El nombre exacto del reporte es: agr_shiping_guide.report_edi_gre
    return 'agr_shiping_guide.report_edi_gre'


def generar_pdf_guia(uid, models, picking_id, reporte_nombre):
    """
    Generar PDF de guía de remisión usando métodos compatibles con Odoo 16.
    
    Estrategia:
    1. Intentar generar con _render (método estándar Odoo 16)
    2. Si falla, buscar adjunto PDF generado automáticamente
    3. Retornar PDF bytes o None con lista de errores
    """
    errores = []
    
    if not reporte_nombre:
        return None, ["No se proporcionó nombre de reporte"]
    
    # MÉTODO 1: _render (Odoo 16 estándar via XML-RPC)
    try:
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.actions.report', '_render',
            [reporte_nombre, [picking_id]]
        )
        if result:
            # _render retorna tupla (pdf_bytes, format) o solo pdf_bytes
            pdf_content = result[0] if isinstance(result, tuple) else result
            if pdf_content:
                return pdf_content, None
    except Exception as e:
        errores.append(f"_render: {str(e)[:100]}")
    
    # MÉTODO 2: Buscar adjunto PDF generado por el reporte
    try:
        adjuntos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking_id),
                ('name', 'ilike', 'agr'),  # Filtro para reportes AGR
                ('mimetype', '=', 'application/pdf')
            ]],
            {'fields': ['datas'], 'limit': 1, 'order': 'id desc'}
        )
        if adjuntos and adjuntos[0].get('datas'):
            pdf_content = base64.b64decode(adjuntos[0]['datas'])
            return pdf_content, None
    except Exception as e:
        errores.append(f"adjuntos_reporte: {str(e)[:100]}")
    
    # MÉTODO 3: Intentar con _render_qweb_pdf (para compatibilidad con versiones anteriores)
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


def clasificar_archivo(nombre_archivo):
    """Clasificar el tipo de archivo por su extensión y nombre"""
    nombre_lower = nombre_archivo.lower()
    
    if nombre_lower.endswith('.pdf'):
        return 'pdf'
    elif nombre_lower.endswith('.zip'):
        return 'zip'
    elif nombre_lower.endswith('.xml'):
        if 'cdr' in nombre_lower or 'constancia' in nombre_lower:
            return 'cdr'
        return 'xml'
    elif 'cdr' in nombre_lower:
        return 'cdr'
    else:
        return None


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
    """Descargar XMLs y CDRs de las guías (PDFs se descargan con otro script)"""
    print(f"\n{'='*70}")
    print("📥 DESCARGANDO XML/CDR DE GUÍAS DE REMISIÓN")
    print(f"{'='*70}")
    print("💡 Estrategia:")
    print("   1. Buscar adjuntos en cada guía")
    print("   2. Descargar XMLs y CDRs (incluyendo contenido de ZIPs)")
    print("   3. Ignorar PDFs (se manejan en otro script)")
    
    stats = {
        'total': len(guias),
        'xml_descargados': 0,
        'cdr_descargados': 0,
        'sin_xml': 0,
        'errores': 0,
        'archivos_por_tipo': {'xml': 0, 'cdr': 0}
    }
    
    analisis_problemas = {
        'sin_adjuntos': [],
        'adjuntos_vacios': [],
        'sin_xml': [],
        'sin_cdr': [],
        'errores_descarga': [],
        'comprobantes_ok': []
    }
    
    carpeta_guias = Path(BASE_PATH)
    
    for idx, guia in enumerate(guias, 1):
        guia_id = guia['id']
        numero_doc = guia.get('l10n_latam_document_number', f"GUIA_{guia_id}")
        nombre_base = numero_doc.replace('/', '-').replace('\\', '-')
        fecha = guia.get('date_done', '')
        
        # Mostrar más detalles en las primeras 10 guías
        mostrar_detalle = (idx <= 10 or idx % 50 == 1)
        
        if mostrar_detalle:
            print(f"\n[{idx}/{len(guias)}] {guia['name']} | Doc: {numero_doc}")
        
        # Variables para tracking por guía
        archivos_descargados_guia = 0
        tipos_encontrados = {'xml': False, 'cdr': False}
        adjuntos_vacios_guia = 0
        
        # Obtener adjuntos
        adjuntos = buscar_adjuntos(uid, models, guia_id)
        
        if not adjuntos:
            analisis_problemas['sin_adjuntos'].append({
                'nombre': numero_doc,
                'fecha': fecha,
                'id': guia_id
            })
        
        # Procesar adjuntos
        if adjuntos:
            for adj in adjuntos:
                nombre_archivo = adj.get('name', '')
                datas = adj.get('datas')
                
                if not datas:
                    if nombre_archivo:
                        adjuntos_vacios_guia += 1
                    continue
                
                try:
                    tipo_archivo = clasificar_archivo(nombre_archivo)
                    
                    if not tipo_archivo or tipo_archivo == 'pdf':
                        continue
                    
                    contenido = base64.b64decode(datas)
                    
                    # Manejo de ZIP
                    if tipo_archivo == 'zip':
                        try:
                            with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                                for filename in z.namelist():
                                    tipo_interno = clasificar_archivo(filename)
                                    
                                    if not tipo_interno or tipo_interno in ['zip', 'pdf']:
                                        continue
                                    
                                    ruta_carpeta = carpeta_guias / tipo_interno
                                    extension_interna = filename.split('.')[-1]
                                    nombre_final = f"{nombre_base}.{extension_interna}"
                                    ruta_archivo = ruta_carpeta / nombre_final
                                    
                                    with open(ruta_archivo, 'wb') as f:
                                        f.write(z.read(filename))
                                    
                                    if tipo_interno in stats['archivos_por_tipo']:
                                        stats['archivos_por_tipo'][tipo_interno] += 1
                                    
                                    if tipo_interno == 'xml': stats['xml_descargados'] += 1
                                    if tipo_interno == 'cdr': stats['cdr_descargados'] += 1
                                    
                                    tipos_encontrados[tipo_interno] = True
                                    archivos_descargados_guia += 1
                                    
                                    if mostrar_detalle:
                                        print(f"      📦 ZIP -> ✅ {tipo_interno.upper()}: {nombre_final}")
                                        
                        except Exception as e:
                            if mostrar_detalle:
                                print(f"      ❌ Error procesando ZIP: {e}")
                                
                    # Archivos normales (XML, CDR)
                    elif tipo_archivo in ['xml', 'cdr']:
                        ruta_carpeta = carpeta_guias / tipo_archivo
                        extension = nombre_archivo.split('.')[-1]
                        nombre_final = f"{nombre_base}.{extension}"
                        ruta_archivo = ruta_carpeta / nombre_final
                        
                        with open(ruta_archivo, 'wb') as f:
                            f.write(contenido)
                            
                        stats['archivos_por_tipo'][tipo_archivo] += 1
                        if tipo_archivo == 'xml': stats['xml_descargados'] += 1
                        if tipo_archivo == 'cdr': stats['cdr_descargados'] += 1
                        
                        tipos_encontrados[tipo_archivo] = True
                        archivos_descargados_guia += 1
                        
                        if mostrar_detalle:
                            print(f"   ✅ {tipo_archivo.upper()}: {nombre_final}")
                            
                except Exception as e:
                    stats['errores'] += 1
                    analisis_problemas['errores_descarga'].append({
                        'nombre': numero_doc,
                        'archivo': nombre_archivo,
                        'error': str(e)[:100]
                    })
        
        # Análisis final de la guía
        if archivos_descargados_guia > 0:
            analisis_problemas['comprobantes_ok'].append({
                'nombre': numero_doc,
                'archivos': archivos_descargados_guia
            })
            
        if not tipos_encontrados['xml']:
            stats['sin_xml'] += 1
            analisis_problemas['sin_xml'].append({
                'nombre': numero_doc,
                'fecha': fecha,
                'id': guia_id
            })
            
        if not tipos_encontrados['cdr']:
            analisis_problemas['sin_cdr'].append({
                'nombre': numero_doc,
                'fecha': fecha,
                'id': guia_id
            })
            
        if adjuntos_vacios_guia > 0:
            analisis_problemas['adjuntos_vacios'].append({
                'nombre': numero_doc,
                'cantidad': adjuntos_vacios_guia
            })

        if idx % 100 == 0:
            print(f"\n   💾 Progreso: {idx}/{len(guias)}")
            print(f"   📊 XMLs: {stats['xml_descargados']} | CDRs: {stats['cdr_descargados']}")
    
    # Mostrar análisis al final
    mostrar_analisis_problemas(analisis_problemas)
    
    return stats


def guardar_resumen_consolidado(analisis, total_problemas):
    """Guardar resumen consolidado de todos los problemas"""
    try:
        # Crear carpeta de logs si no existe en la raíz del mes (compartida con facturas)
        carpeta_logs = Path(BASE_PATH_RAIZ) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / "RESUMEN_COMPLETO_PROBLEMAS_GUIAS_XML.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN CONSOLIDADO - DESCARGA XML GUIAS\n")
            f.write(f"{'#'*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Período: {FECHA_INICIO} al {FECHA_FIN} ({nombre_mes} {AÑO})\n")
            f.write(f"Ambiente: {AMBIENTE.upper()}\n")
            f.write(f"{'#'*70}\n\n")
            
            # Resumen ejecutivo
            f.write("="*70 + "\n")
            f.write("RESUMEN EJECUTIVO\n")
            f.write("="*70 + "\n")
            f.write(f"Total de problemas encontrados: {total_problemas}\n\n")
            
            f.write(f"❌ Comprobantes sin adjuntos:    {len(analisis['sin_adjuntos'])}\n")
            f.write(f"⚠️  Adjuntos vacíos:              {len(analisis['adjuntos_vacios'])}\n")
            f.write(f"📋 Comprobantes sin XML:         {len(analisis['sin_xml'])}\n")
            f.write(f"✅ Comprobantes sin CDR:         {len(analisis['sin_cdr'])}\n")
            f.write(f"❌ Errores de descarga:          {len(analisis['errores_descarga'])}\n")
            f.write(f"✅ Comprobantes OK:              {len(analisis['comprobantes_ok'])}\n")
            f.write("\n")
            
            # Archivos de detalle generados
            f.write("="*70 + "\n")
            f.write("ARCHIVOS DE DETALLE GENERADOS\n")
            f.write("="*70 + "\n")
            if analisis['sin_adjuntos']:
                f.write(f"• ANALISIS_sin_adjuntos_guias.txt      ({len(analisis['sin_adjuntos'])} registros)\n")
            if analisis['adjuntos_vacios']:
                f.write(f"• ANALISIS_adjuntos_vacios_guias.txt   ({len(analisis['adjuntos_vacios'])} registros)\n")
            if analisis['sin_xml']:
                f.write(f"• ANALISIS_sin_xml_guias.txt           ({len(analisis['sin_xml'])} registros)\n")
            if analisis['sin_cdr']:
                f.write(f"• ANALISIS_sin_cdr_guias.txt           ({len(analisis['sin_cdr'])} registros)\n")
            if analisis['errores_descarga']:
                f.write(f"• ANALISIS_errores_descarga_guias.txt  ({len(analisis['errores_descarga'])} registros)\n")
            f.write("\n")
            
            # IDs de Odoo para búsqueda directa
            if analisis['sin_adjuntos'] or analisis['sin_xml']:
                f.write("="*70 + "\n")
                f.write("IDs DE ODOO PARA BÚSQUEDA DIRECTA\n")
                f.write("="*70 + "\n\n")
                
                if analisis['sin_adjuntos']:
                    f.write("SIN ADJUNTOS (IDs para buscar en Odoo):\n")
                    ids = [str(item['id']) for item in analisis['sin_adjuntos'][:20]]
                    f.write(", ".join(ids))
                    if len(analisis['sin_adjuntos']) > 20:
                        f.write(f"... y {len(analisis['sin_adjuntos']) - 20} más")
                    f.write("\n\n")
        
        print(f"   📊 Resumen consolidado guardado en: {carpeta_logs}/RESUMEN_COMPLETO_PROBLEMAS_GUIAS_XML.txt")
        
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar resumen consolidado: {e}")


def guardar_lista_problemas(tipo, lista):
    """Guardar lista de problemas en archivo de texto"""
    try:
        # Crear carpeta de logs si no existe
        carpeta_logs = Path(BASE_PATH_RAIZ) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / f"ANALISIS_{tipo}_guias.txt"
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
                if 'fecha' in item: f.write(f"    Fecha: {item['fecha']}\n")
                if 'error' in item: f.write(f"    Error: {item['error']}\n")
                f.write("\n")
            
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar archivo de análisis: {e}")


def mostrar_analisis_problemas(analisis):
    """Mostrar análisis detallado de problemas encontrados"""
    print(f"\n{'='*70}")
    print("🔍 ANÁLISIS DETALLADO DE PROBLEMAS")
    print(f"{'='*70}")
    
    total_problemas = (
        len(analisis['sin_adjuntos']) + 
        len(analisis['adjuntos_vacios']) + 
        len(analisis['sin_xml']) + 
        len(analisis['sin_cdr']) + 
        len(analisis['errores_descarga'])
    )
    
    if total_problemas == 0:
        print("✅ No se encontraron problemas - Todas las guías OK")
        return
    
    print(f"\n⚠️  Se encontraron {total_problemas} problemas en total:\n")
    
    if analisis['sin_adjuntos']:
        print(f"❌ SIN ADJUNTOS ({len(analisis['sin_adjuntos'])} guías)")
        guardar_lista_problemas('sin_adjuntos', analisis['sin_adjuntos'])

    if analisis['sin_xml']:
        print(f"📋 SIN XML ({len(analisis['sin_xml'])} guías)")
        guardar_lista_problemas('sin_xml', analisis['sin_xml'])

    if analisis['errores_descarga']:
        print(f"❌ ERRORES DE DESCARGA ({len(analisis['errores_descarga'])} guías)")
        guardar_lista_problemas('errores_descarga', analisis['errores_descarga'])

    # Generar resumen consolidado
    guardar_resumen_consolidado(analisis, total_problemas)
    print(f"{'='*70}\n")


def mostrar_resumen(stats):
    """Mostrar resumen"""
    print(f"\n{'='*70}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"📦 Total de guías procesadas: {stats['total']}")
    print(f"\n📄 Archivos XML/CDR:")
    print(f"   • XMLs descargados: {stats['xml_descargados']}")
    print(f"   • CDRs descargados: {stats['cdr_descargados']}")
    print(f"\n❌ Errores: {stats['errores']}")
    print(f"\n📂 Ubicación: {BASE_PATH}")
    print(f"   • Carpeta XML: {Path(BASE_PATH) / 'xml'}")
    print(f"   • Carpeta CDR: {Path(BASE_PATH) / 'cdr'}")
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
