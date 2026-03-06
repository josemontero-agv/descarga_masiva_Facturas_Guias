import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib3

# Añadir la raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import (
    MAPEO_CARPETAS,
    ODOO_DB,
    ODOO_PASSWORD,
    ODOO_URL,
    ODOO_USER,
    get_base_path,
    get_periodo_info,
)
from core.odoo_client import conectar_odoo
from modules.documentos_module import descargar_comprobante_integral

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def buscar_archivo_recursivo(base_path, nombre_archivo):
    """Busca un archivo dentro de una carpeta y todas sus subcarpetas (Diarios)."""
    for path in base_path.rglob(nombre_archivo):
        return path
    return None


def crear_sesion_http():
    session = requests.Session()
    session.verify = False
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        }
    )
    return session


def autenticar_sesion_web(session):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USER,
            "password": ODOO_PASSWORD,
        },
        "id": int(time.time()),
    }
    resp = session.post(
        f"{ODOO_URL.rstrip('/')}/web/session/authenticate",
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    uid = ((data or {}).get("result") or {}).get("uid")
    if not uid:
        raise RuntimeError(f"Auth web fallida: {data}")
    return uid


def buscar_report_name_guia(models, uid):
    dominio = [
        ("model", "=", "stock.picking"),
        ("name", "ilike", "Guía de Remisión AGR"),
    ]
    reps = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [dominio],
        {"fields": ["id", "name", "report_name"], "limit": 5},
    )
    if reps:
        return reps[0].get("report_name") or "agr_shiping_guide.report_edi_gre"
    return "agr_shiping_guide.report_edi_gre"


def buscar_report_names_factura(models, uid):
    candidatos = []

    objetivo = [
        ("model", "=", "account.move"),
        ("name", "ilike", "Factura AGR"),
    ]
    reps_obj = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [objetivo],
        {"fields": ["id", "name", "report_name"], "limit": 10},
    )
    for rep in reps_obj:
        rn = rep.get("report_name")
        if rn and rn not in candidatos:
            candidatos.append(rn)

    amplio = [
        ("model", "=", "account.move"),
        ("name", "ilike", "factura"),
    ]
    reps_amp = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [amplio],
        {"fields": ["id", "name", "report_name"], "limit": 50},
    )
    for rep in reps_amp:
        nombre = (rep.get("name") or "").lower()
        rn = rep.get("report_name")
        if rn and (("agr" in nombre) or ("agr" in rn.lower())) and rn not in candidatos:
            candidatos.append(rn)

    if "account.report_invoice" not in candidatos:
        candidatos.append("account.report_invoice")

    return candidatos


def descargar_pdf_http(session, report_name, model_id, ruta_final):
    url = f"{ODOO_URL.rstrip('/')}/report/pdf/{report_name}/{model_id}"
    resp = session.get(url, timeout=90, allow_redirects=True)
    resp.raise_for_status()
    contenido = resp.content or b""
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if not (contenido.startswith(b"%PDF") or "application/pdf" in ctype):
        return False, "Respuesta no PDF (html/login/redirección)"

    ruta_final.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_final, "wb") as f:
        f.write(contenido)
    return True, None

def main():
    t_inicio = datetime.now()
    print(f"\n{'='*70}")
    print("🛠️  HERRAMIENTA DE REPARACIÓN DE FALTANTES (MODO RECURSIVO)")
    print(f"   Fecha Inicio: {t_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # CONFIGURACIÓN DE PERIODO (Ajustar según necesidad)
    año = 2026
    mes = 1
    info = get_periodo_info(año, mes)
    base_path_mes = get_base_path(año, info['nombre_carpeta_mes'])

    uid, models = conectar_odoo()
    if not uid: 
        print("❌ No se pudo conectar a Odoo.")
        return

    # ============================================================================
    # 1. REPARAR COMPROBANTES (Facturas, Boletas, Notas)
    # ============================================================================
    print(f"\n🔍 Verificando Comprobantes faltantes en {base_path_mes}...")
    
    # Obtener todos los comprobantes del periodo desde Odoo
    domain_docs = [
        ('state', '=', 'posted'),
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('invoice_date', '>=', info['fecha_inicio']),
        ('invoice_date', '<=', info['fecha_fin']),
    ]
    docs_odoo = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD, 
        'account.move', 'search_read', 
        [domain_docs], 
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'l10n_latam_document_type_id', 'journal_id']}
    )

    docs_faltantes = []
    for doc in docs_odoo:
        num_doc = doc.get('name') or doc.get('l10n_latam_document_number', f"DOC_{doc['id']}")
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')
        
        # Búsqueda recursiva con sufijos exactos de archive
        tiene_pdf = buscar_archivo_recursivo(base_path_mes, f"{nombre_base}_pdf.pdf")
        tiene_xml = buscar_archivo_recursivo(base_path_mes, f"{nombre_base}_xml.xml")
        tiene_cdr = buscar_archivo_recursivo(base_path_mes, f"{nombre_base}_cdr.xml")
        
        # Si falta alguno de los 3 básicos para archive, lo marcamos para reparar
        if not tiene_pdf or not tiene_xml or not tiene_cdr:
            docs_faltantes.append(doc)

    if docs_faltantes:
        print(f"⚠️  Se encontraron {len(docs_faltantes)} comprobantes faltantes.")
        for idx, doc in enumerate(docs_faltantes, 1):
            num_doc = doc.get('l10n_latam_document_number') or doc['name']
            diario_raw = doc.get('journal_id', [0, ''])
            nombre_diario = diario_raw[1] if diario_raw else 'Sin_Diario'
            
            print(f"   [{idx}/{len(docs_faltantes)}] Reparando: {num_doc} ({nombre_diario})")
            descargar_comprobante_integral(uid, models, doc, base_path_mes, nombre_diario=nombre_diario)
    else:
        print("✅ Todos los comprobantes (Facturas/Boletas) están completos.")

    # ============================================================================
    # 2. REPARAR GUÍAS (PDF/XML/CDR faltantes) SIN SELENIUM
    # ============================================================================
    print(f"\n🔍 Verificando Guías sin PDF...")
    base_path_guia = base_path_mes / "09_Guias_Remision"
    (base_path_guia / "pdf").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "xml").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "cdr").mkdir(parents=True, exist_ok=True)
    
    domain_guias = [
        ('state', '=', 'done'),
        ('picking_type_id', '=', 2),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias_odoo = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD, 
        'stock.picking', 'search_read', 
        [domain_guias], 
        {'fields': ['id', 'l10n_latam_document_number']}
    )
    
    guias_faltantes = []
    for g in guias_odoo:
        num_doc = g['l10n_latam_document_number']
        if num_doc:
            nombre_base = num_doc.replace('/', '-').replace('\\', '-')
            
            # Verificamos PDF, XML y CDR para guías
            tiene_pdf = buscar_archivo_recursivo(base_path_guia, f"{nombre_base}.pdf")
            tiene_xml = buscar_archivo_recursivo(base_path_guia, f"{nombre_base}.xml")
            tiene_cdr = buscar_archivo_recursivo(base_path_guia, f"{nombre_base}_cdr.xml")
            
            if not tiene_pdf or not tiene_xml or not tiene_cdr:
                guias_faltantes.append(g)

    if guias_faltantes:
        print(f"⚠️  Se encontraron {len(guias_faltantes)} guías incompletas. Reparando por HTTP...")
        report_name_guia = buscar_report_name_guia(models, uid)
        session = crear_sesion_http()
        try:
            uid_web = autenticar_sesion_web(session)
            print(f"✅ Sesión web autenticada para guías (uid={uid_web})")
        except Exception as e:
            print(f"❌ No se pudo autenticar sesión web para guías: {e}")
            return

        for idx, g in enumerate(guias_faltantes, 1):
            num_doc = g.get("l10n_latam_document_number")
            if not num_doc:
                continue
            nombre_base = num_doc.replace("/", "-").replace("\\", "-")
            ruta_pdf = base_path_guia / "pdf" / f"{nombre_base}.pdf"

            try:
                ok, motivo = descargar_pdf_http(session, report_name_guia, g["id"], ruta_pdf)
                if not ok:
                    autenticar_sesion_web(session)
                    ok, motivo = descargar_pdf_http(session, report_name_guia, g["id"], ruta_pdf)

                if ok:
                    print(f"   [{idx}/{len(guias_faltantes)}] ✅ Guía PDF reparada: {num_doc}")
                else:
                    print(f"   [{idx}/{len(guias_faltantes)}] ❌ Guía {num_doc}: {motivo}")
            except Exception as e:
                print(f"   [{idx}/{len(guias_faltantes)}] ❌ Guía {num_doc}: {str(e)[:80]}")
    else:
        print("✅ Todas las guías tienen su PDF.")

    # ============================================================================
    # 3. RESCATE DE PDFs DE COMPROBANTES CON REPORTE FACTURA AGR (SIN SELENIUM)
    # ============================================================================
    print("\n🔍 Aplicando rescate HTTP de PDFs faltantes de comprobantes...")
    report_names_factura = buscar_report_names_factura(models, uid)
    session_docs = crear_sesion_http()
    try:
        uid_web_docs = autenticar_sesion_web(session_docs)
        print(f"✅ Sesión web autenticada para comprobantes (uid={uid_web_docs})")
    except Exception as e:
        print(f"❌ No se pudo autenticar sesión web de comprobantes: {e}")
        return

    for idx, doc in enumerate(docs_faltantes, 1):
        num_doc = doc.get('name') or doc.get('l10n_latam_document_number', f"DOC_{doc['id']}")
        nombre_base = num_doc.replace('/', '-').replace('\\', '-')

        diario_raw = doc.get('journal_id', [0, ''])
        nombre_diario = diario_raw[1] if diario_raw else 'Sin_Diario'
        nombre_diario_limpio = "".join(
            [c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in nombre_diario]
        ).strip()

        tipo_doc_raw = doc.get('l10n_latam_document_type_id', [0, ''])[1]
        tipo_carpeta = 'Otros'
        for k, v in MAPEO_CARPETAS.items():
            if k in tipo_doc_raw:
                tipo_carpeta = v
                break

        ruta_pdf = base_path_mes / nombre_diario_limpio / tipo_carpeta / "pdf" / f"{nombre_base}_pdf.pdf"
        if ruta_pdf.exists():
            continue

        descargado = False
        ultimo_error = "sin detalle"
        for rep in report_names_factura:
            try:
                ok, motivo = descargar_pdf_http(session_docs, rep, doc["id"], ruta_pdf)
                if ok:
                    print(f"   [{idx}/{len(docs_faltantes)}] ✅ PDF comprobante {num_doc} con {rep}")
                    descargado = True
                    break
                ultimo_error = motivo
            except Exception as e:
                ultimo_error = str(e)

        if not descargado:
            print(f"   [{idx}/{len(docs_faltantes)}] ❌ No se pudo rescatar {num_doc}: {ultimo_error}")

    # Calcular duración
    t_final = datetime.now()
    duracion = t_final - t_inicio

    print(f"\n✅ PROCESO DE REPARACIÓN FINALIZADO en {duracion}.")
    print(f"   Ubicación: {base_path_mes}")

if __name__ == "__main__":
    main()
