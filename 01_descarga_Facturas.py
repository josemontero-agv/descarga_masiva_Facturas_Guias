# -*- coding: utf-8 -*-
"""
Script para descarga masiva de comprobantes electrónicos desde Odoo
Descarga PDF, XML y CDR de facturas, boletas, notas de crédito y débito
"""

import xmlrpc.client
import os
import base64
import sys
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

# Cargar variables de entorno desde el directorio actual o padre
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    # Intentar buscar en directorios padres
    parent_dirs = [Path(__file__).parent.parent, Path(__file__).parent.parent.parent]
    for parent_dir in parent_dirs:
        test_env = parent_dir / '.env'
        if test_env.exists():
            env_path = test_env
            break

load_dotenv(env_path)

# Credenciales de Odoo
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# Validar que existan las credenciales
if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("❌ Error: Asegúrate de tener un archivo .env con las variables:")
    print("   ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD")
    exit(1)

# Configuración de fechas - Cambiar aquí el año y mes que deseas descargar
# IMPORTANTE: Ajusta el año según tus datos
AÑO = 2025  # ← CAMBIAR AQUÍ EL AÑO
MES = 10     # ← CAMBIAR AQUÍ EL MES (1-12)

# Calcular fechas automáticamente
from calendar import monthrange
ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"

# Ruta base de descarga
BASE_PATH = r"C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias\Prueba_Octubre"

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
    """Crear la estructura de carpetas para cada tipo de documento"""
    print(f"\n{'='*70}")
    print("📁 CREANDO ESTRUCTURA DE CARPETAS")
    print(f"{'='*70}")
    
    for doc_tipo, carpeta_doc in MAPEO_CARPETAS.items():
        for tipo_archivo in ['pdf', 'xml', 'cdr']:
            ruta = Path(BASE_PATH) / carpeta_doc / tipo_archivo
            ruta.mkdir(parents=True, exist_ok=True)
            print(f"✅ Creada: {ruta}")


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
                    'partner_id', 'amount_total', 'state'
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
        
        carpeta_destino = MAPEO_CARPETAS.get(tipo_doc_nombre, '01_Facturas')
        
        print(f"\n[{idx}/{len(comprobantes)}] 📄 {move_name}")
        print(f"   📅 Fecha: {fecha}")
        print(f"   👤 Cliente: {partner_name[:50]}...")
        print(f"   📂 Tipo: {tipo_doc_nombre}")
        
        # Obtener adjuntos
        adjuntos = obtener_adjuntos(uid, models, move_id, move_name)
        
        if not adjuntos:
            print(f"   ⚠️  Sin archivos adjuntos")
            estadisticas['sin_archivos'] += 1
            continue
        
        print(f"   📎 {len(adjuntos)} archivos encontrados")
        
        # Descargar cada adjunto
        archivos_descargados = 0
        for adjunto in adjuntos:
            nombre_archivo = adjunto.get('name', '')
            datas = adjunto.get('datas')
            
            if not datas or not nombre_archivo:
                continue
            
            # Clasificar tipo de archivo
            tipo_archivo = clasificar_archivo(nombre_archivo)
            if not tipo_archivo:
                continue
            
            # Construir ruta de destino
            ruta_carpeta = Path(BASE_PATH) / carpeta_destino / tipo_archivo
            
            # Limpiar nombre de archivo para evitar caracteres inválidos
            nombre_limpio = move_name.replace('/', '-').replace('\\', '-')
            extension = nombre_archivo.split('.')[-1]
            nombre_final = f"{nombre_limpio}_{tipo_archivo}.{extension}"
            
            ruta_archivo = ruta_carpeta / nombre_final
            
            try:
                # Decodificar y guardar archivo
                contenido = base64.b64decode(datas)
                with open(ruta_archivo, 'wb') as f:
                    f.write(contenido)
                
                print(f"      ✅ {tipo_archivo.upper()}: {nombre_final}")
                archivos_descargados += 1
                estadisticas['archivos_por_tipo'][tipo_archivo] += 1
                
            except Exception as e:
                print(f"      ❌ Error guardando {tipo_archivo}: {e}")
                estadisticas['errores'] += 1
        
        if archivos_descargados > 0:
            estadisticas['descargados'] += 1
    
    return estadisticas


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
    print(f"# Período: {FECHA_INICIO} al {FECHA_FIN}")
    print(f"# Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # 1. Conectar a Odoo
    uid, models = conectar_odoo()
    
    # 2. Verificar qué datos están disponibles
    verificar_datos_disponibles(uid, models)
    
    # 3. Crear estructura de carpetas
    crear_estructura_carpetas()
    
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

