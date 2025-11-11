# -*- coding: utf-8 -*-
"""
Script para ANALIZAR reportes PDF disponibles en Odoo para Guías de Remisión
"""

import xmlrpc.client
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar credenciales
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

# Conectar
print("\n" + "="*70)
print("🔍 ANÁLISIS DE REPORTES PDF DISPONIBLES EN ODOO")
print("="*70)
print(f"📡 Conectando a: {ODOO_URL}")

common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"✅ Conectado (UID: {uid})")

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