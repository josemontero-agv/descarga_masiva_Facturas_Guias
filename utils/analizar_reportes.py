# -*- coding: utf-8 -*-
"""
Script para ANALIZAR reportes PDF disponibles en Odoo para Guías de Remisión
"""

import xmlrpc.client
import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================
# CONFIGURACIÓN DE AMBIENTE
# ============================================
# Cambiar entre "desarrollo" y "produccion"
AMBIENTE = "desarrollo"  # ← CAMBIAR AQUÍ: "desarrollo" o "produccion"

# Cargar credenciales
# El archivo .env está en la raíz del proyecto (1 nivel arriba desde utils/)
script_dir = Path(__file__).parent
project_root = script_dir.parent  # Subir un nivel desde utils/ a la raíz
env_file = f'.env.{AMBIENTE}'
env_path = project_root / env_file

print(f"📁 Buscando archivo {env_file} en: {env_path}")

# Verificar si el archivo existe
if not env_path.exists():
    # Intentar buscar en directorios padre
    parent_dirs = [Path(__file__).parent.parent, project_root]
    for parent_dir in parent_dirs:
        test_env = parent_dir / env_file
        if test_env.exists():
            env_path = test_env
            break

if not env_path.exists():
    print(f"⚠️  Archivo {env_file} no encontrado, intentando con .env...")
    env_path = project_root / '.env'
    if not env_path.exists():
        print(f"❌ Error: No se encontró el archivo '{env_file}' ni '.env'")
        print(f"💡 Crea el archivo con las credenciales de Odoo")
        print(f"   Archivos disponibles:")
        print(f"   - .env.desarrollo  (para pruebas)")
        print(f"   - .env.produccion  (para ambiente real)")
        exit(1)

print(f"✅ Archivo encontrado: {env_path} (Ambiente: {AMBIENTE})")
load_dotenv(env_path, override=True)

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# Verificar que todas las variables se cargaron
print("\n🔍 Variables de entorno cargadas:")
print(f"  ODOO_URL: {ODOO_URL if ODOO_URL else '❌ NO ENCONTRADA'}")
print(f"  ODOO_DB: {ODOO_DB if ODOO_DB else '❌ NO ENCONTRADA'}")
print(f"  ODOO_USER: {ODOO_USER if ODOO_USER else '❌ NO ENCONTRADA'}")
print(f"  ODOO_PASSWORD: {'✅ Configurada' if ODOO_PASSWORD else '❌ NO ENCONTRADA'}")

if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("\n❌ Error: Faltan credenciales. Verifica tu archivo .env.desarrollo")
    exit(1)

# Conectar
print("\n" + "="*70)
print("🔍 ANÁLISIS DE REPORTES PDF DISPONIBLES EN ODOO")
print("="*70)
print(f"📡 Conectando a: {ODOO_URL}")

try:
    import ssl
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    common = xmlrpc.client.ServerProxy(
        f'{ODOO_URL}/xmlrpc/2/common',
        allow_none=True,
        use_datetime=True,
        context=context
    )
    
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    
    if not uid:
        print("❌ Error de autenticación. Revisa tus credenciales.")
        exit(1)
        
except Exception as e:
    print(f"❌ Error al conectar: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print(f"✅ Conectado (UID: {uid})")

try:
    models = xmlrpc.client.ServerProxy(
        f'{ODOO_URL}/xmlrpc/2/object',
        allow_none=True,
        use_datetime=True,
        context=context
    )
except:
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

# ============================================================================
# BUSCAR TODOS LOS REPORTES PARA stock.picking
# ============================================================================

print("\n" + "="*70)
print("📋 REPORTES PDF DISPONIBLES PARA GUÍAS (stock.picking)")
print("="*70)

try:
    reportes = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'ir.actions.report', 'search_read',
        [[('model', '=', 'stock.picking')]],
        {'fields': ['id', 'name', 'report_name', 'report_type', 'paperformat_id', 'print_report_name']}
    )
    
    if reportes:
        print(f"\n✅ Se encontraron {len(reportes)} reportes PDF:\n")
        
        for idx, rep in enumerate(reportes, 1):
            print(f"{idx}. 📄 {rep.get('name', 'Sin nombre')}")
            print(f"   ID: {rep['id']}")
            print(f"   Report Name: {rep.get('report_name', 'N/A')}")
            print(f"   Tipo: {rep.get('report_type', 'N/A')}")
            if rep.get('paperformat_id'):
                print(f"   Formato papel: {rep['paperformat_id'][1] if len(rep['paperformat_id']) > 1 else 'N/A'}")
            print(f"   Nombre impresión: {rep.get('print_report_name', 'N/A')}")
            print()
    else:
        print("⚠️  No se encontraron reportes para stock.picking")
        
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# BUSCAR REPORTES RELACIONADOS CON GUÍAS (búsqueda amplia)
# ============================================================================

print("\n" + "="*70)
print("🔎 BÚSQUEDA AMPLIA: Reportes con 'guía' o 'delivery' en el nombre")
print("="*70)

try:
    reportes_guia = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'ir.actions.report', 'search_read',
        [[
            '|', '|', '|',
            ('name', 'ilike', 'guía'),
            ('name', 'ilike', 'guia'),
            ('name', 'ilike', 'delivery'),
            ('name', 'ilike', 'remision')
        ]],
        {'fields': ['id', 'name', 'report_name', 'model']}
    )
    
    if reportes_guia:
        print(f"\n✅ Se encontraron {len(reportes_guia)} reportes relacionados:\n")
        
        for idx, rep in enumerate(reportes_guia, 1):
            print(f"{idx}. 📄 {rep.get('name', 'Sin nombre')}")
            print(f"   Modelo: {rep.get('model', 'N/A')}")
            print(f"   Report Name: {rep.get('report_name', 'N/A')}")
            print()
    else:
        print("⚠️  No se encontraron reportes relacionados")
        
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# VERIFICAR SI EXISTE "e-Guía de Remisión AGR"
# ============================================================================

print("\n" + "="*70)
print("🎯 BÚSQUEDA ESPECÍFICA: 'e-Guía de Remisión AGR'")
print("="*70)

try:
    reporte_agr = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'ir.actions.report', 'search_read',
        [[
            '&',
            ('name', 'ilike', 'e-guía'),
            ('name', 'ilike', 'agr')
        ]],
        {'fields': ['id', 'name', 'report_name', 'model', 'report_type']}
    )
    
    if reporte_agr:
        print(f"\n✅ ENCONTRADO:\n")
        for rep in reporte_agr:
            print(f"📄 {rep.get('name')}")
            print(f"   ID: {rep['id']}")
            print(f"   Report Name: {rep.get('report_name')}")
            print(f"   Modelo: {rep.get('model')}")
            print(f"   Tipo: {rep.get('report_type')}")
    else:
        print("⚠️  No se encontró reporte 'e-Guía de Remisión AGR'")
        print("💡 Intenta buscar variantes del nombre o revisa los reportes listados arriba")
        
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# ANALIZAR ADJUNTOS DE UNA GUÍA DE MUESTRA
# ============================================================================

print("\n" + "="*70)
print("🔬 ANÁLISIS DE ADJUNTOS EN UNA GUÍA DE MUESTRA")
print("="*70)

try:
    # Buscar una guía del mes actual
    guias_muestra = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'stock.picking', 'search_read',
        [[
            ('picking_type_id', '=', 2),
            ('state', '=', 'done'),
            ('l10n_latam_document_number', '!=', False)
        ]],
        {'fields': ['id', 'name', 'l10n_latam_document_number'], 'limit': 1}
    )
    
    if guias_muestra:
        guia = guias_muestra[0]
        print(f"\n📦 Guía de muestra: {guia['name']}")
        print(f"   Doc: {guia.get('l10n_latam_document_number')}")
        
        # Buscar adjuntos
        adjuntos = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', guia['id'])
            ]],
            {'fields': ['id', 'name', 'mimetype', 'description', 'file_size']}
        )
        
        if adjuntos:
            print(f"\n✅ Adjuntos encontrados ({len(adjuntos)}):\n")
            for idx, adj in enumerate(adjuntos, 1):
                print(f"{idx}. {adj.get('name', 'Sin nombre')}")
                print(f"   Tipo: {adj.get('mimetype', 'N/A')}")
                print(f"   Tamaño: {adj.get('file_size', 0)} bytes")
                if adj.get('description'):
                    print(f"   Descripción: {adj.get('description')}")
                print()
        else:
            print("⚠️  No se encontraron adjuntos en esta guía")
    else:
        print("⚠️  No se encontró guía de muestra")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ ANÁLISIS COMPLETADO")
print("="*70)