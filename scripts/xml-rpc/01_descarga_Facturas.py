# -*- coding: utf-8 -*-
"""
Script para descarga masiva de comprobantes electrónicos desde Odoo
Descarga PDF, XML y CDR de facturas, boletas, notas de crédito y débito
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

# Configurar encoding para la consola de Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        # Si falla, usar ASCII y evitar emojis
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
# Buscar en la raíz del proyecto (2 niveles arriba desde scripts/documentos/)
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

load_dotenv(env_path)

# Credenciales de Odoo (se cargan desde .env)
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# Validar que existan las credenciales
if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print(f"❌ Error: El archivo '{env_file}' no tiene todas las variables necesarias")
    print("   Variables requeridas: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD")
    exit(1)

# ============================================
# CONFIGURACIÓN DE FECHAS Y RUTAS
# ============================================

# Configuración de fechas - Cambiar aquí el año y mes que deseas descargar
AÑO = 2025  # ← CAMBIAR AQUÍ EL AÑO
MES = 12    # ← CAMBIAR AQUÍ EL MES (1-12) - Para ejecutar en paralelo, cambiar el mes

# Calcular fechas automáticamente
from calendar import monthrange
ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"

# Obtener nombre del mes
nombre_mes = datetime(AÑO, MES, 1).strftime('%B')
nombre_carpeta_mes = f"{MES:02d}_{nombre_mes}"

# Definir rutas según ambiente
if AMBIENTE == "produccion":
    # Ruta base de descarga (PRODUCCIÓN)
    BASE_PATH = rf"V:\{AÑO}\{nombre_carpeta_mes}"
    
    # Verificar acceso a la ruta de red
    if not Path(BASE_PATH).parent.parent.exists():
        print(f"❌ Error: No se puede acceder a la ruta de red:")
        print(f"   {BASE_PATH}")
        print(f"💡 Verifica que:")
        print(f"   1. La unidad Y: esté mapeada correctamente")
        print(f"   2. Tengas permisos de escritura en la carpeta")
        print(f"   3. Estés conectado a la red de la empresa")
        respuesta = input("\n¿Continuar de todas formas? (s/n): ")
        if respuesta.lower() != 's':
            exit(1)
else:
    # Ruta base de descarga (DESARROLLO)
    BASE_PATH = project_root / "Prueba_Octubre" / nombre_carpeta_mes
    print(f"🔧 MODO DESARROLLO: Guardando en ruta local:")
    print(f"   {BASE_PATH}")

# Crear carpeta raíz si no existe
Path(BASE_PATH).mkdir(parents=True, exist_ok=True)

# Mapeo de tipos de documentos a carpetas
MAPEO_CARPETAS = {
    'Factura': '01_Facturas',
    'Boleta': '03_Boletas',
    'Nota de Crédito': '07_Notas_Credito',
    'Nota de Débito': '08_Notas_Debito'
}

# ============================================================================
# FUNCIONES
# ============================================================================

def conectar_odoo():
    """Conectar a Odoo y retornar uid y models"""
    print(f"\n{'='*70}")
    print("🔄 CONECTANDO A ODOO")
    print(f"{'='*70}")
    print(f"🔧 Ambiente: {AMBIENTE.upper()}")
    print(f"📡 URL: {ODOO_URL}")
    print(f"🗄️  Base de datos: {ODOO_DB}")
    print(f"👤 Usuario: {ODOO_USER}")
    
    try:
        # Autenticación
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            print("❌ Error de autenticación. Verifica tus credenciales.")
            exit(1)
        
        print(f"✅ Conexión exitosa! (UID: {uid})")
        
        # Conexión al objeto de modelos
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        return uid, models
        
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        exit(1)


def crear_estructura_carpetas():
    """
    DEPRECADO: Esta función ya no se usa porque los archivos se guardan
    directamente en la estructura con diarios: {Mes}/{Diario}/{TipoDocumento}/{TipoArchivo}/
    
    Las carpetas se crean automáticamente al guardar archivos con la ruta completa.
    """
    # Función deshabilitada - las carpetas se crean automáticamente al guardar archivos
    pass


def obtener_tipos_documento(uid, models):
    """Obtener los IDs de los tipos de documento que nos interesan"""
    print(f"\n{'='*70}")
    print("🔍 OBTENIENDO TIPOS DE DOCUMENTO")
    print(f"{'='*70}")
    
    try:
        # Buscar tipos de documento en Odoo
        doc_types = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'l10n_latam.document.type', 'search_read',
            [[]],
            {'fields': ['id', 'name', 'code']}
        )
        
        # Mapear tipos de documento
        tipo_doc_ids = {}
        for doc in doc_types:
            nombre = doc.get('name', '')
            for tipo_buscar, carpeta in MAPEO_CARPETAS.items():
                if tipo_buscar.lower() in nombre.lower():
                    tipo_doc_ids[tipo_buscar] = doc['id']
                    print(f"✅ {tipo_buscar}: ID {doc['id']} - {nombre}")
                    break
        
        return tipo_doc_ids
        
    except Exception as e:
        print(f"❌ Error obteniendo tipos de documento: {e}")
        return {}


def verificar_datos_disponibles(uid, models):
    """Verificar qué períodos tienen datos disponibles"""
    print(f"\n{'='*70}")
    print("🔍 VERIFICANDO DATOS DISPONIBLES EN ODOO")
    print(f"{'='*70}")
    
    try:
        # Buscar todos los comprobantes sin filtro de fecha
        comprobantes_total = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.move', 'search_read',
            [[
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ]],
            {'fields': ['invoice_date'], 'limit': 10000}
        )
        
        if not comprobantes_total:
            print("⚠️  No se encontraron comprobantes en la base de datos")
            return
        
        # Agrupar por año-mes
        periodos = {}
        for comp in comprobantes_total:
            fecha = comp.get('invoice_date')
            if fecha:
                año_mes = fecha[:7]  # Formato: YYYY-MM
                periodos[año_mes] = periodos.get(año_mes, 0) + 1
        
        # Mostrar períodos disponibles
        print(f"\n📊 Total de comprobantes en sistema: {len(comprobantes_total)}")
        print(f"\n📅 Períodos con datos disponibles:")
        for periodo in sorted(periodos.keys(), reverse=True)[:12]:  # Últimos 12 meses
            print(f"   • {periodo}: {periodos[periodo]} comprobantes")
        
        # Verificar si el período solicitado tiene datos
        periodo_solicitado = f"{AÑO}-{MES:02d}"
        if periodo_solicitado in periodos:
            print(f"\n✅ El período {periodo_solicitado} tiene {periodos[periodo_solicitado]} comprobantes")
        else:
            print(f"\n⚠️  ATENCIÓN: El período {periodo_solicitado} NO tiene datos")
            print(f"   Revisa las líneas 45-46 del script para cambiar el año/mes")
        
    except Exception as e:
        print(f"⚠️  Error verificando datos: {e}")


def obtener_comprobantes(uid, models, tipo_doc_ids):
    """Obtener todos los comprobantes del mes especificado"""
    print(f"\n{'='*70}")
    print("🔍 BUSCANDO COMPROBANTES DEL PERÍODO SELECCIONADO")
    print(f"{'='*70}")
    print(f"📅 Período: {FECHA_INICIO} al {FECHA_FIN}")
    
    try:
        # Construir dominio de búsqueda
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),  # Facturas y notas
            ('state', '=', 'posted'),  # Solo documentos contabilizados
            ('invoice_date', '>=', FECHA_INICIO),
            ('invoice_date', '<=', FECHA_FIN)
        ]
        
        # NO FILTRAR por tipo de documento aquí, obtener todos y clasificar después
        
        # Buscar comprobantes
        comprobantes = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.move', 'search_read',
            [domain],
            {
                'fields': [
                    'id', 'name', 'invoice_date', 'l10n_latam_document_type_id',
                    'partner_id', 'amount_total', 'state', 'journal_id'
                ],
                'order': 'invoice_date asc'
            }
        )
        
        print(f"\n✅ Se encontraron {len(comprobantes)} comprobantes")
        
        # Estadísticas por tipo
        if comprobantes:
            print(f"\n📊 ESTADÍSTICAS POR TIPO DE DOCUMENTO:")
            tipo_count = {}
            for comp in comprobantes:
                tipo = comp.get('l10n_latam_document_type_id')
                tipo_nombre = tipo[1] if tipo and len(tipo) > 1 else 'Sin tipo'
                tipo_count[tipo_nombre] = tipo_count.get(tipo_nombre, 0) + 1
            
            for tipo, count in tipo_count.items():
                print(f"   • {tipo}: {count} documentos")
        
        return comprobantes
        
    except Exception as e:
        print(f"❌ Error obteniendo comprobantes: {e}")
        return []


def obtener_adjuntos(uid, models, move_id, move_name):
    """Obtener los adjuntos (PDF, XML, CDR) de un comprobante"""
    try:
        # Buscar adjuntos relacionados al comprobante
        adjuntos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move_id)
            ]],
            {'fields': ['id', 'name', 'datas', 'mimetype']}
        )
        
        return adjuntos
        
    except Exception as e:
        print(f"   ⚠️  Error obteniendo adjuntos: {e}")
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


def descargar_comprobantes(uid, models, comprobantes, tipo_doc_ids):
    """Descargar todos los comprobantes con sus adjuntos"""
    print(f"\n{'='*70}")
    print("📥 DESCARGANDO COMPROBANTES")
    print(f"{'='*70}")
    
    # Invertir el mapeo para buscar por ID
    id_to_tipo = {v: k for k, v in tipo_doc_ids.items()}
    
    estadisticas = {
        'total': len(comprobantes),
        'descargados': 0,
        'sin_archivos': 0,
        'errores': 0,
        'archivos_por_tipo': {'pdf': 0, 'xml': 0, 'cdr': 0}
    }
    
    # NUEVO: Análisis detallado de problemas
    analisis_problemas = {
        'sin_adjuntos': [],           # Comprobantes sin ningún adjunto
        'adjuntos_vacios': [],        # Adjuntos sin datos (datas = False)
        'sin_pdf': [],                # Tienen adjuntos pero no PDF
        'sin_xml': [],                # Tienen adjuntos pero no XML
        'sin_cdr': [],                # Tienen adjuntos pero no CDR
        'errores_descarga': [],       # Errores al guardar archivos
        'errores_pdf': [],            # Errores específicos al extraer/guardar PDFs
        'comprobantes_ok': []         # Comprobantes descargados correctamente
    }
    
    for idx, comp in enumerate(comprobantes, 1):
        move_id = comp['id']
        move_name = comp['name']
        fecha = comp.get('invoice_date', '')
        partner = comp.get('partner_id')
        partner_name = partner[1] if partner and len(partner) > 1 else 'Sin cliente'
        
        # Determinar tipo de documento
        tipo_doc_id = comp.get('l10n_latam_document_type_id')
        tipo_doc_id_num = tipo_doc_id[0] if tipo_doc_id and len(tipo_doc_id) > 0 else None
        tipo_doc_nombre = id_to_tipo.get(tipo_doc_id_num, 'Factura')  # Default a Factura
        
        # Si no está en nuestro mapeo, intentar detectar por el nombre del tipo
        if tipo_doc_id and len(tipo_doc_id) > 1:
            tipo_nombre_completo = tipo_doc_id[1].lower()
            for tipo_key in MAPEO_CARPETAS.keys():
                if tipo_key.lower() in tipo_nombre_completo:
                    tipo_doc_nombre = tipo_key
                    break
        
        # Obtener nombre del diario y limpiarlo
        diario_data = comp.get('journal_id')
        nombre_diario = diario_data[1] if diario_data else 'Sin_Diario'
        # Limpiar caracteres no válidos para carpetas
        nombre_diario_limpio = "".join([c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in nombre_diario]).strip()
        
        # Definir ruta relativa: Diario / Tipo_Documento
        # Ejemplo: "F110 (Venta nacional)" / "01_Facturas"
        carpeta_base_tipo = MAPEO_CARPETAS.get(tipo_doc_nombre, '01_Facturas')
        carpeta_destino_relativa = Path(nombre_diario_limpio) / carpeta_base_tipo
        
        print(f"\n[{idx}/{len(comprobantes)}] 📄 {move_name}")
        print(f"   📅 Fecha: {fecha}")
        print(f"   👤 Cliente: {partner_name[:50]}...")
        print(f"   📂 Tipo: {tipo_doc_nombre}")
        print(f"   📓 Diario: {nombre_diario}")
        
        # Obtener adjuntos
        adjuntos = obtener_adjuntos(uid, models, move_id, move_name)
        
        if not adjuntos:
            print(f"   ⚠️  Sin archivos adjuntos")
            estadisticas['sin_archivos'] += 1
            # NUEVO: Registrar en análisis
            analisis_problemas['sin_adjuntos'].append({
                'nombre': move_name,
                'fecha': fecha,
                'partner': partner_name,
                'id': move_id
            })
            continue
        
        print(f"   📎 {len(adjuntos)} archivos encontrados")
        
        # NUEVO: Tracking de archivos por tipo
        archivos_descargados = 0
        tipos_encontrados = {'pdf': False, 'xml': False, 'cdr': False}
        adjuntos_vacios = 0
        
        # Descargar cada adjunto
        for adjunto in adjuntos:
            nombre_archivo = adjunto.get('name', '')
            datas = adjunto.get('datas')
            
            if not datas or not nombre_archivo:
                if nombre_archivo:
                    adjuntos_vacios += 1
                continue
            
            # Clasificar tipo de archivo
            tipo_archivo = clasificar_archivo(nombre_archivo)
            if not tipo_archivo:
                continue
            
            # Construir ruta de destino base (se usará si no es ZIP)
            # Nota: la estructura ahora incluye el diario en carpeta_destino_relativa
            
            try:
                # Decodificar contenido
                contenido = base64.b64decode(datas)
                
                # Manejo especial para ZIP
                if tipo_archivo == 'zip':
                    try:
                        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                            for filename in z.namelist():
                                # Clasificar archivo interno
                                tipo_interno = clasificar_archivo(filename)
                                
                                if not tipo_interno or tipo_interno == 'zip':
                                    continue
                                
                                # Definir ruta destino para archivo interno (incluye Diario)
                                ruta_carpeta = Path(BASE_PATH) / carpeta_destino_relativa / tipo_interno
                                ruta_carpeta.mkdir(parents=True, exist_ok=True)
                                
                                # Construir nombre final
                                nombre_limpio = move_name.replace('/', '-').replace('\\', '-')
                                extension_interna = filename.split('.')[-1]
                                nombre_final = f"{nombre_limpio}_{tipo_interno}.{extension_interna}"
                                
                                ruta_archivo = ruta_carpeta / nombre_final
                                
                                # Extraer y guardar con manejo específico de errores para PDFs
                                try:
                                    with open(ruta_archivo, 'wb') as f:
                                        f.write(z.read(filename))
                                    
                                    print(f"      📦 ZIP -> ✅ {tipo_interno.upper()}: {nombre_final}")
                                    
                                    # Actualizar contadores
                                    archivos_descargados += 1
                                    estadisticas['archivos_por_tipo'][tipo_interno] += 1
                                    tipos_encontrados[tipo_interno] = True
                                    
                                except Exception as e_pdf:
                                    # Si es un PDF, registrar en errores_pdf específicamente
                                    if tipo_interno == 'pdf':
                                        print(f"      ❌ Error extrayendo PDF del ZIP: {nombre_final} - {e_pdf}")
                                        analisis_problemas['errores_pdf'].append({
                                            'nombre': move_name,
                                            'archivo': filename,
                                            'archivo_zip': nombre_archivo,
                                            'error': str(e_pdf)[:100],
                                            'origen': 'zip',
                                            'fecha': fecha,
                                            'id': move_id
                                        })
                                    else:
                                        # Para otros tipos, solo mostrar error pero no detener flujo
                                        print(f"      ❌ Error extrayendo {tipo_interno} del ZIP: {nombre_final} - {e_pdf}")
                                
                    except Exception as e:
                        print(f"      ❌ Error procesando ZIP {nombre_archivo}: {e}")
                        # No contamos como error general para no detener flujo, pero avisamos
                
                else:
                    # Proceso normal para archivos no ZIP
                    ruta_carpeta = Path(BASE_PATH) / carpeta_destino_relativa / tipo_archivo
                    ruta_carpeta.mkdir(parents=True, exist_ok=True)
                    
                    # Limpiar nombre de archivo para evitar caracteres inválidos
                    nombre_limpio = move_name.replace('/', '-').replace('\\', '-')
                    extension = nombre_archivo.split('.')[-1]
                    nombre_final = f"{nombre_limpio}_{tipo_archivo}.{extension}"
                    
                    ruta_archivo = ruta_carpeta / nombre_final
                    
                    with open(ruta_archivo, 'wb') as f:
                        f.write(contenido)
                    
                    print(f"      ✅ {tipo_archivo.upper()}: {nombre_final}")
                    archivos_descargados += 1
                    estadisticas['archivos_por_tipo'][tipo_archivo] += 1
                    tipos_encontrados[tipo_archivo] = True
                
            except Exception as e:
                print(f"      ❌ Error guardando {tipo_archivo}: {e}")
                estadisticas['errores'] += 1
                analisis_problemas['errores_descarga'].append({
                    'nombre': move_name,
                    'archivo': nombre_archivo,
                    'error': str(e)[:100]
                })
        
        # NUEVO: Análisis post-descarga
        if archivos_descargados > 0:
            estadisticas['descargados'] += 1
            
            # Registrar comprobante OK
            analisis_problemas['comprobantes_ok'].append({
                'nombre': move_name,
                'archivos': archivos_descargados
            })
            
            # Verificar archivos faltantes
            if not tipos_encontrados['pdf']:
                analisis_problemas['sin_pdf'].append({
                    'nombre': move_name,
                    'fecha': fecha,
                    'id': move_id
                })
            
            if not tipos_encontrados['xml']:
                analisis_problemas['sin_xml'].append({
                    'nombre': move_name,
                    'fecha': fecha,
                    'id': move_id
                })
            
            if not tipos_encontrados['cdr']:
                analisis_problemas['sin_cdr'].append({
                    'nombre': move_name,
                    'fecha': fecha,
                    'id': move_id
                })
        
        # Registrar adjuntos vacíos
        if adjuntos_vacios > 0:
            analisis_problemas['adjuntos_vacios'].append({
                'nombre': move_name,
                'cantidad': adjuntos_vacios
            })
    
    # NUEVO: Mostrar análisis detallado de problemas
    mostrar_analisis_problemas(analisis_problemas)
    
    return estadisticas


def mostrar_analisis_problemas(analisis):
    """Mostrar análisis detallado de problemas encontrados"""
    print(f"\n{'='*70}")
    print("🔍 ANÁLISIS DETALLADO DE PROBLEMAS")
    print(f"{'='*70}")
    
    total_problemas = (
        len(analisis['sin_adjuntos']) + 
        len(analisis['adjuntos_vacios']) + 
        len(analisis['sin_pdf']) + 
        len(analisis['sin_xml']) + 
        len(analisis['sin_cdr']) + 
        len(analisis['errores_descarga']) +
        len(analisis['errores_pdf'])
    )
    
    if total_problemas == 0:
        print("✅ No se encontraron problemas - Todos los comprobantes OK")
        return
    
    print(f"\n⚠️  Se encontraron {total_problemas} problemas en total:\n")
    
    # 1. Comprobantes sin adjuntos
    if analisis['sin_adjuntos']:
        print(f"❌ SIN ADJUNTOS ({len(analisis['sin_adjuntos'])} comprobantes):")
        print(f"   Motivo: El comprobante no tiene ningún archivo adjunto en Odoo")
        print(f"   Posibles causas:")
        print(f"   - Factura no enviada a SUNAT")
        print(f"   - Error en la generación del comprobante")
        print(f"   - Comprobante anulado sin archivos")
        
        if len(analisis['sin_adjuntos']) <= 10:
            for comp in analisis['sin_adjuntos']:
                print(f"      • {comp['nombre']} (ID: {comp['id']}) - {comp['fecha']}")
        else:
            for comp in analisis['sin_adjuntos'][:5]:
                print(f"      • {comp['nombre']} (ID: {comp['id']}) - {comp['fecha']}")
            print(f"      ... y {len(analisis['sin_adjuntos']) - 5} más")
        
        # Guardar lista completa en archivo
        guardar_lista_problemas('sin_adjuntos', analisis['sin_adjuntos'])
        print(f"   💾 Lista completa guardada en: {BASE_PATH}/Resumen de errores/ANALISIS_sin_adjuntos.txt")
        print()
    
    # 2. Adjuntos vacíos
    if analisis['adjuntos_vacios']:
        print(f"⚠️  ADJUNTOS VACÍOS ({len(analisis['adjuntos_vacios'])} comprobantes):")
        print(f"   Motivo: Tienen adjuntos pero sin contenido (campo 'datas' vacío)")
        print(f"   Posibles causas:")
        print(f"   - Archivo corrupto en Odoo")
        print(f"   - Error en la carga del archivo")
        
        for comp in analisis['adjuntos_vacios'][:5]:
            print(f"      • {comp['nombre']} ({comp['cantidad']} archivos vacíos)")
        
        if len(analisis['adjuntos_vacios']) > 5:
            print(f"      ... y {len(analisis['adjuntos_vacios']) - 5} más")
        
        guardar_lista_problemas('adjuntos_vacios', analisis['adjuntos_vacios'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/FACTURAS_ANALISIS_adjuntos_vacios.txt")
        print()
    
    # 3. Sin PDF
    if analisis['sin_pdf']:
        print(f"📄 SIN PDF ({len(analisis['sin_pdf'])} comprobantes):")
        print(f"   Motivo: Se descargaron XML/CDR pero no PDF")
        print(f"   Posibles causas:")
        print(f"   - PDF no generado por el emisor")
        print(f"   - PDF con nombre diferente al esperado")
        
        for comp in analisis['sin_pdf'][:3]:
            print(f"      • {comp['nombre']} - {comp['fecha']}")
        
        if len(analisis['sin_pdf']) > 3:
            print(f"      ... y {len(analisis['sin_pdf']) - 3} más")
        
        guardar_lista_problemas('sin_pdf', analisis['sin_pdf'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/FACTURAS_ANALISIS_sin_pdf.txt")
        print()
    
    # 3.5. Errores de extracción de PDF
    if analisis['errores_pdf']:
        print(f"📄 ERRORES AL EXTRAER PDF ({len(analisis['errores_pdf'])} archivos):")
        print(f"   Motivo: Error al extraer o guardar archivos PDF")
        print(f"   Posibles causas:")
        print(f"   - PDF corrupto en el ZIP")
        print(f"   - Permisos insuficientes para guardar PDF")
        print(f"   - Disco lleno")
        print(f"   - Caracteres inválidos en nombre de archivo PDF")
        
        for err in analisis['errores_pdf'][:5]:
            origen_texto = "desde ZIP" if err.get('origen') == 'zip' else "directo"
            archivo_mostrar = err.get('archivo_zip', err.get('archivo', 'N/A'))
            print(f"      • {err['nombre']}")
            print(f"        Archivo: {archivo_mostrar} ({origen_texto})")
            print(f"        Error: {err['error']}")
        
        if len(analisis['errores_pdf']) > 5:
            print(f"      ... y {len(analisis['errores_pdf']) - 5} más")
        
        guardar_lista_problemas('errores_pdf', analisis['errores_pdf'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/FACTURAS_ANALISIS_errores_pdf.txt")
        print()
    
    # 4. Sin XML
    if analisis['sin_xml']:
        print(f"📋 SIN XML ({len(analisis['sin_xml'])} comprobantes):")
        print(f"   Motivo: Se descargaron PDF/CDR pero no XML")
        
        for comp in analisis['sin_xml'][:3]:
            print(f"      • {comp['nombre']} - {comp['fecha']}")
        
        if len(analisis['sin_xml']) > 3:
            print(f"      ... y {len(analisis['sin_xml']) - 3} más")
        
        guardar_lista_problemas('sin_xml', analisis['sin_xml'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/FACTURAS_ANALISIS_sin_xml.txt")
        print()
    
    # 5. Sin CDR
    if analisis['sin_cdr']:
        print(f"✅ SIN CDR ({len(analisis['sin_cdr'])} comprobantes):")
        print(f"   Motivo: Se descargaron PDF/XML pero no CDR")
        print(f"   Nota: CDR puede no existir para facturas muy recientes")
        print(f"         o comprobantes aún no confirmados por SUNAT")
        
        guardar_lista_problemas('sin_cdr', analisis['sin_cdr'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/ANALISIS_sin_cdr.txt")
        print()
    
    # 6. Errores de descarga
    if analisis['errores_descarga']:
        print(f"❌ ERRORES AL GUARDAR ({len(analisis['errores_descarga'])} archivos):")
        print(f"   Motivo: Error al escribir el archivo en disco")
        print(f"   Posibles causas:")
        print(f"   - Permisos insuficientes")
        print(f"   - Disco lleno")
        print(f"   - Caracteres inválidos en nombre de archivo")
        
        for err in analisis['errores_descarga'][:3]:
            print(f"      • {err['nombre']}")
            print(f"        Archivo: {err['archivo']}")
            print(f"        Error: {err['error']}")
        
        guardar_lista_problemas('errores_descarga', analisis['errores_descarga'])
        print(f"   💾 Lista guardada en: {BASE_PATH}/Resumen de errores/FACTURAS_ANALISIS_errores_descarga.txt")
        print()
    
    # 7. Generar resumen consolidado
    guardar_resumen_consolidado(analisis, total_problemas)
    
    print(f"{'='*70}\n")


def guardar_resumen_consolidado(analisis, total_problemas):
    """Guardar resumen consolidado de todos los problemas"""
    try:
        # Crear carpeta de logs si no existe
        carpeta_logs = Path(BASE_PATH) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / "FACTURAS_RESUMEN_COMPLETO_PROBLEMAS.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN CONSOLIDADO - ANÁLISIS DE DESCARGA\n")
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
            f.write(f"📄 Comprobantes sin PDF:         {len(analisis['sin_pdf'])}\n")
            f.write(f"📋 Comprobantes sin XML:         {len(analisis['sin_xml'])}\n")
            f.write(f"✅ Comprobantes sin CDR:         {len(analisis['sin_cdr'])}\n")
            f.write(f"❌ Errores de descarga:          {len(analisis['errores_descarga'])}\n")
            f.write(f"📄 Errores al extraer PDF:       {len(analisis['errores_pdf'])}\n")
            f.write(f"✅ Comprobantes OK:              {len(analisis['comprobantes_ok'])}\n")
            f.write("\n")
            
            # Archivos de detalle generados
            f.write("="*70 + "\n")
            f.write("ARCHIVOS DE DETALLE GENERADOS\n")
            f.write("="*70 + "\n")
            if analisis['sin_adjuntos']:
                f.write(f"• FACTURAS_ANALISIS_sin_adjuntos.txt      ({len(analisis['sin_adjuntos'])} registros)\n")
            if analisis['adjuntos_vacios']:
                f.write(f"• FACTURAS_ANALISIS_adjuntos_vacios.txt   ({len(analisis['adjuntos_vacios'])} registros)\n")
            if analisis['sin_pdf']:
                f.write(f"• FACTURAS_ANALISIS_sin_pdf.txt           ({len(analisis['sin_pdf'])} registros)\n")
            if analisis['sin_xml']:
                f.write(f"• FACTURAS_ANALISIS_sin_xml.txt           ({len(analisis['sin_xml'])} registros)\n")
            if analisis['sin_cdr']:
                f.write(f"• FACTURAS_ANALISIS_sin_cdr.txt           ({len(analisis['sin_cdr'])} registros)\n")
            if analisis['errores_descarga']:
                f.write(f"• FACTURAS_ANALISIS_errores_descarga.txt  ({len(analisis['errores_descarga'])} registros)\n")
            if analisis['errores_pdf']:
                f.write(f"• FACTURAS_ANALISIS_errores_pdf.txt      ({len(analisis['errores_pdf'])} registros)\n")
            f.write("\n")
            
            # Prioridades de acción
            f.write("="*70 + "\n")
            f.write("PRIORIDADES DE ACCIÓN\n")
            f.write("="*70 + "\n\n")
            
            if analisis['sin_adjuntos']:
                f.write("🔴 PRIORIDAD ALTA - Comprobantes sin adjuntos\n")
                f.write(f"   Total: {len(analisis['sin_adjuntos'])} comprobantes\n")
                f.write("   Acción: Verificar en Odoo y regenerar/reenviar a SUNAT\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_sin_adjuntos.txt\n\n")
            
            if analisis['errores_descarga']:
                f.write("🔴 PRIORIDAD ALTA - Errores de descarga\n")
                f.write(f"   Total: {len(analisis['errores_descarga'])} archivos\n")
                f.write("   Acción: Revisar permisos y volver a ejecutar\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_errores_descarga.txt\n\n")
            
            if analisis['errores_pdf']:
                f.write("🔴 PRIORIDAD ALTA - Errores al extraer PDF\n")
                f.write(f"   Total: {len(analisis['errores_pdf'])} archivos PDF\n")
                f.write("   Acción: Revisar permisos, espacio en disco y archivos corruptos\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_errores_pdf.txt\n\n")
            
            if analisis['sin_pdf']:
                f.write("🟡 PRIORIDAD MEDIA - Comprobantes sin PDF\n")
                f.write(f"   Total: {len(analisis['sin_pdf'])} comprobantes\n")
                f.write("   Acción: Generar PDF desde Odoo\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_sin_pdf.txt\n\n")
            
            if analisis['sin_xml']:
                f.write("🟡 PRIORIDAD MEDIA - Comprobantes sin XML\n")
                f.write(f"   Total: {len(analisis['sin_xml'])} comprobantes\n")
                f.write("   Acción: Verificar envío a SUNAT\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_sin_xml.txt\n\n")
            
            if analisis['adjuntos_vacios']:
                f.write("🟡 PRIORIDAD MEDIA - Adjuntos vacíos\n")
                f.write(f"   Total: {len(analisis['adjuntos_vacios'])} comprobantes\n")
                f.write("   Acción: Regenerar archivos en Odoo\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_adjuntos_vacios.txt\n\n")
            
            if analisis['sin_cdr']:
                f.write("🟢 PRIORIDAD BAJA - Comprobantes sin CDR\n")
                f.write(f"   Total: {len(analisis['sin_cdr'])} comprobantes\n")
                f.write("   Acción: Esperar confirmación SUNAT y volver a ejecutar\n")
                f.write(f"   Archivo: FACTURAS_ANALISIS_sin_cdr.txt\n\n")
            
            # Instrucciones para reintento
            f.write("="*70 + "\n")
            f.write("INSTRUCCIONES PARA REINTENTO\n")
            f.write("="*70 + "\n\n")
            f.write("1. SOLUCIONAR PROBLEMAS EN ODOO:\n")
            f.write("   - Regenerar comprobantes faltantes\n")
            f.write("   - Reenviar a SUNAT los no enviados\n")
            f.write("   - Generar PDFs faltantes\n\n")
            
            f.write("2. VOLVER A EJECUTAR SCRIPT:\n")
            f.write("   - El script verificará qué archivos YA fueron descargados\n")
            f.write("   - Solo descargará los archivos nuevos o faltantes\n")
            f.write("   - No duplicará archivos existentes\n\n")
            
            f.write("3. VERIFICAR RESULTADOS:\n")
            f.write("   - Revisar nuevo archivo FACTURAS_RESUMEN_COMPLETO_PROBLEMAS.txt\n")
            f.write("   - Comparar cantidad de problemas con ejecución anterior\n")
            f.write("   - Repetir hasta que no haya problemas críticos\n\n")
            
            # IDs de Odoo para búsqueda directa
            if analisis['sin_adjuntos'] or analisis['sin_pdf'] or analisis['sin_xml']:
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
        
        print(f"   📊 Resumen consolidado guardado en: {carpeta_logs}/FACTURAS_RESUMEN_COMPLETO_PROBLEMAS.txt")
        
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar resumen consolidado: {e}")


def guardar_lista_problemas(tipo, lista):
    """Guardar lista de problemas en archivo de texto"""
    try:
        # Crear carpeta de logs si no existe
        carpeta_logs = Path(BASE_PATH) / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        
        ruta_archivo = carpeta_logs / f"FACTURAS_ANALISIS_{tipo}.txt"
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"ANÁLISIS DE PROBLEMAS: {tipo.upper().replace('_', ' ')}\n")
            f.write(f"{'='*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Período: {FECHA_INICIO} al {FECHA_FIN}\n")
            f.write(f"Total de problemas: {len(lista)}\n")
            f.write(f"{'='*70}\n\n")
            
            # Escribir información según el tipo de problema
            for idx, item in enumerate(lista, 1):
                f.write(f"[{idx}] Comprobante: {item['nombre']}\n")
                
                if 'id' in item:
                    f.write(f"    ID Odoo: {item['id']}\n")
                
                if 'fecha' in item:
                    f.write(f"    Fecha: {item['fecha']}\n")
                
                if 'partner' in item:
                    f.write(f"    Cliente: {item['partner']}\n")
                
                if 'cantidad' in item:
                    f.write(f"    Archivos vacíos: {item['cantidad']}\n")
                
                if 'archivo' in item:
                    f.write(f"    Archivo: {item['archivo']}\n")
                
                if 'archivo_zip' in item:
                    f.write(f"    Archivo ZIP origen: {item['archivo_zip']}\n")
                
                if 'origen' in item:
                    origen_texto = "Extraído desde ZIP" if item['origen'] == 'zip' else "Archivo directo"
                    f.write(f"    Origen: {origen_texto}\n")
                
                if 'error' in item:
                    f.write(f"    Error: {item['error']}\n")
                
                if 'archivos' in item:
                    f.write(f"    Archivos descargados: {item['archivos']}\n")
                
                f.write("\n")
            
            # Agregar sección de recomendaciones
            f.write(f"{'='*70}\n")
            f.write("RECOMENDACIONES Y ACCIONES\n")
            f.write(f"{'='*70}\n\n")
            
            if tipo == 'sin_adjuntos':
                f.write("CAUSA PROBABLE:\n")
                f.write("- Facturas no enviadas a SUNAT\n")
                f.write("- Comprobantes anulados sin archivos\n")
                f.write("- Error en la generación del comprobante electrónico\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Verificar en Odoo el estado del comprobante\n")
                f.write("2. Reenviar a SUNAT si es necesario\n")
                f.write("3. Regenerar el comprobante si está corrupto\n")
            
            elif tipo == 'sin_pdf':
                f.write("CAUSA PROBABLE:\n")
                f.write("- PDF no generado en Odoo\n")
                f.write("- Nombre de archivo no estándar\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Generar PDF manualmente desde Odoo\n")
                f.write("2. Volver a ejecutar el script de descarga\n")
            
            elif tipo == 'sin_xml':
                f.write("CAUSA PROBABLE:\n")
                f.write("- XML no generado o no enviado a SUNAT\n")
                f.write("- Archivo XML eliminado\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Verificar envío a SUNAT\n")
                f.write("2. Regenerar comprobante si es necesario\n")
            
            elif tipo == 'sin_cdr':
                f.write("NOTA:\n")
                f.write("- CDR (Constancia de Recepción) solo existe para comprobantes\n")
                f.write("  confirmados por SUNAT\n")
                f.write("- Comprobantes muy recientes pueden no tener CDR aún\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Esperar confirmación de SUNAT (puede tomar horas)\n")
                f.write("2. Volver a ejecutar el script más tarde\n")
            
            elif tipo == 'adjuntos_vacios':
                f.write("CAUSA PROBABLE:\n")
                f.write("- Archivos corruptos en Odoo\n")
                f.write("- Error en la carga del archivo\n")
                f.write("- Base de datos con inconsistencias\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Regenerar los archivos en Odoo\n")
                f.write("2. Contactar soporte técnico si persiste\n")
            
            elif tipo == 'errores_descarga':
                f.write("CAUSA PROBABLE:\n")
                f.write("- Permisos insuficientes en carpeta destino\n")
                f.write("- Caracteres inválidos en nombre de archivo\n")
                f.write("- Disco lleno\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Verificar permisos de escritura\n")
                f.write("2. Verificar espacio en disco\n")
                f.write("3. Revisar errores específicos arriba\n")
            
            elif tipo == 'errores_pdf':
                f.write("CAUSA PROBABLE:\n")
                f.write("- PDF corrupto dentro del archivo ZIP\n")
                f.write("- Permisos insuficientes para guardar PDF\n")
                f.write("- Disco lleno\n")
                f.write("- Caracteres inválidos en nombre de archivo PDF\n")
                f.write("- Error al leer PDF del ZIP\n\n")
                f.write("ACCIÓN RECOMENDADA:\n")
                f.write("1. Verificar permisos de escritura en carpeta PDF\n")
                f.write("2. Verificar espacio en disco disponible\n")
                f.write("3. Regenerar PDF desde Odoo si está corrupto\n")
                f.write("4. Revisar errores específicos arriba para más detalles\n")
            
    except Exception as e:
        print(f"   ⚠️  No se pudo guardar archivo de análisis: {e}")


def mostrar_resumen(estadisticas):
    """Mostrar resumen final de la descarga"""
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE DESCARGA")
    print(f"{'='*70}")
    print(f"📄 Total de comprobantes procesados: {estadisticas['total']}")
    print(f"✅ Comprobantes con archivos descargados: {estadisticas['descargados']}")
    print(f"⚠️  Comprobantes sin archivos: {estadisticas['sin_archivos']}")
    print(f"❌ Errores durante descarga: {estadisticas['errores']}")
    print(f"\n📁 Archivos descargados por tipo:")
    print(f"   • PDF: {estadisticas['archivos_por_tipo']['pdf']}")
    print(f"   • XML: {estadisticas['archivos_por_tipo']['xml']}")
    print(f"   • CDR: {estadisticas['archivos_por_tipo']['cdr']}")
    print(f"\n📂 Ubicación: {BASE_PATH}")
    print(f"{'='*70}\n")


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal"""
    print(f"\n{'#'*70}")
    print("# DESCARGA MASIVA DE COMPROBANTES ELECTRÓNICOS - ODOO")
    print(f"# Ambiente: {AMBIENTE.upper()}")
    print(f"# Período: {FECHA_INICIO} al {FECHA_FIN} ({nombre_mes} {AÑO})")
    print(f"# Destino: {BASE_PATH}")
    print(f"# Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # 1. Conectar a Odoo
    uid, models = conectar_odoo()
    
    # 2. Verificar qué datos están disponibles
    verificar_datos_disponibles(uid, models)
    
    # 3. Crear estructura de carpetas (DESHABILITADO - se crean automáticamente con diarios)
    # crear_estructura_carpetas()  # Ya no se crean carpetas directamente en el mes
    
    # 4. Obtener tipos de documento
    tipo_doc_ids = obtener_tipos_documento(uid, models)
    
    # 5. Obtener comprobantes del mes
    comprobantes = obtener_comprobantes(uid, models, tipo_doc_ids)
    
    if not comprobantes:
        print("\n⚠️  No se encontraron comprobantes para el período especificado.")
        print(f"💡 SOLUCIÓN: Cambia el año y mes en las líneas 45-46 del script")
        print(f"   Archivo: {__file__}")
        return
    
    # 6. Descargar comprobantes
    estadisticas = descargar_comprobantes(uid, models, comprobantes, tipo_doc_ids)
    
    # 7. Mostrar resumen
    mostrar_resumen(estadisticas)
    
    print("✅ ¡Proceso completado exitosamente!")


if __name__ == "__main__":
    main()

