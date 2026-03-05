# -*- coding: utf-8 -*-
"""
Descarga de PDFs de guias sin Selenium (HTTP + session Odoo).

Estrategia:
1) XML-RPC: listar guias del periodo.
2) XML-RPC: ubicar el reporte "e-Guia de Remision AGR" y su report_name tecnico.
3) HTTP session: autenticar en /web/session/authenticate.
4) HTTP GET: descargar /report/pdf/<report_name>/<id_guia>.
"""

import os
import sys
import time
import ssl
import json
import xmlrpc.client
from pathlib import Path
from datetime import datetime
from calendar import monthrange

import requests
from dotenv import load_dotenv
import urllib3


# Configurar salida UTF-8 en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================================
# CONFIG
# ============================================================================

AMBIENTE = "produccion"  # "desarrollo" o "produccion"
AÑO = 2026
MES = 2
PICKING_TYPE_ID = 2

# Nombre funcional del reporte solicitado por usuario
REPORTE_FUNCIONAL = "e-Guía de Remisión AGR"

# Fallback tecnico por si no se encuentra en search_read
REPORTE_TECNICO_FALLBACK = "agr_shiping_guide.report_edi_gre"

# En varios entornos corporativos hay inspeccion SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================================
# CARGA DE ENTORNO Y RUTAS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
env_file = f".env.{AMBIENTE}"
env_path = PROJECT_ROOT / env_file

if not env_path.exists():
    print(f"❌ No se encontró {env_file} en {PROJECT_ROOT}")
    sys.exit(1)

load_dotenv(env_path, override=True)
print(f"📁 Cargando configuración desde: {env_path}")

ODOO_URL = (os.getenv("ODOO_URL") or "").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("❌ Faltan credenciales Odoo en .env")
    sys.exit(1)

MESES_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

ultimo_dia = monthrange(AÑO, MES)[1]
FECHA_INICIO = f"{AÑO}-{MES:02d}-01"
FECHA_FIN = f"{AÑO}-{MES:02d}-{ultimo_dia}"
NOMBRE_MES = MESES_ESPANOL.get(MES, str(MES))
NOMBRE_CARPETA_MES = f"{MES:02d}_{NOMBRE_MES}"

if AMBIENTE == "produccion":
    BASE_PATH_RAIZ = Path(rf"V:\{AÑO}\{NOMBRE_CARPETA_MES}")
else:
    BASE_PATH_RAIZ = PROJECT_ROOT / "Prueba_Octubre" / NOMBRE_CARPETA_MES

BASE_PATH_PDF = BASE_PATH_RAIZ / "09_Guias_Remision" / "pdf"
LOGS_PATH = BASE_PATH_RAIZ / "Resumen de errores"

BASE_PATH_PDF.mkdir(parents=True, exist_ok=True)
LOGS_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================================
# XML-RPC
# ============================================================================

def conectar_xmlrpc():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    common = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/common",
        allow_none=True,
        use_datetime=True,
        context=context,
    )
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise RuntimeError("No se pudo autenticar por XML-RPC")

    models = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/object",
        allow_none=True,
        use_datetime=True,
        context=context,
    )
    return uid, models


def buscar_report_name(models, uid):
    """
    Busca el report_name tecnico para "e-Guía de Remisión AGR".
    """
    domain = [
        ("model", "=", "stock.picking"),
        ("name", "ilike", "Guía de Remisión AGR"),
    ]

    reportes = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [domain],
        {"fields": ["id", "name", "report_name", "report_type"], "limit": 5},
    )

    if reportes:
        rep = reportes[0]
        print(
            f"✅ Reporte detectado: {rep.get('name')} | report_name={rep.get('report_name')}"
        )
        return rep.get("report_name") or REPORTE_TECNICO_FALLBACK

    print(
        f"⚠️ No se encontró '{REPORTE_FUNCIONAL}'. "
        f"Usando fallback: {REPORTE_TECNICO_FALLBACK}"
    )
    return REPORTE_TECNICO_FALLBACK


def obtener_guias(models, uid):
    print(f"📡 Buscando guías del {FECHA_INICIO} al {FECHA_FIN}...")
    domain = [
        ("picking_type_id", "=", PICKING_TYPE_ID),
        ("state", "=", "done"),
        ("date_done", ">=", f"{FECHA_INICIO} 00:00:00"),
        ("date_done", "<=", f"{FECHA_FIN} 23:59:59"),
        ("l10n_latam_document_number", "!=", False),
    ]
    return models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "stock.picking",
        "search_read",
        [domain],
        {
            "fields": ["id", "name", "l10n_latam_document_number", "date_done"],
            "order": "date_done asc",
        },
    )


# ============================================================================
# HTTP SESSION + DESCARGA PDF
# ============================================================================

def crear_sesion_http():
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
    })
    return session


def autenticar_web(session):
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
    url = f"{ODOO_URL}/web/session/authenticate"
    r = session.post(url, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    data = r.json()
    uid = ((data or {}).get("result") or {}).get("uid")
    if not uid:
        raise RuntimeError(f"Autenticación web fallida: {data}")
    return uid


def descargar_pdf_guia(session, report_name, guia_id, destino_pdf):
    url = f"{ODOO_URL}/report/pdf/{report_name}/{guia_id}"
    r = session.get(url, timeout=90, allow_redirects=True)
    r.raise_for_status()

    # Validación rápida: la respuesta debe parecer PDF
    content_type = (r.headers.get("Content-Type") or "").lower()
    contenido = r.content or b""
    parece_pdf = contenido.startswith(b"%PDF")
    if "application/pdf" not in content_type and not parece_pdf:
        return False, "Respuesta no es PDF (posible HTML/login/bloqueo)"

    with open(destino_pdf, "wb") as f:
        f.write(contenido)
    return True, None


def guardar_resumen(errores, exitosos, saltados, report_name):
    archivo = LOGS_PATH / "GUIAS_PDF_V2_RESUMEN.txt"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(f"{'#'*70}\n")
        f.write("# RESUMEN DESCARGA GUIAS PDF V2 (HTTP SIN SELENIUM)\n")
        f.write(f"{'#'*70}\n")
        f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Periodo: {FECHA_INICIO} a {FECHA_FIN}\n")
        f.write(f"Ambiente: {AMBIENTE}\n")
        f.write(f"Reporte tecnico: {report_name}\n")
        f.write(f"{'#'*70}\n\n")
        f.write(f"✅ Descargados: {exitosos}\n")
        f.write(f"⏭️ Saltados: {saltados}\n")
        f.write(f"❌ Errores: {len(errores)}\n\n")
        if errores:
            f.write("DETALLE DE ERRORES:\n")
            for item in errores:
                f.write(f"- {item['doc']} (id={item['id']}): {item['error']}\n")
    print(f"📊 Resumen guardado en: {archivo}")


def main():
    print("\n" + "#" * 70)
    print("# DESCARGA GUIAS PDF V2 (HTTP + XML-RPC, SIN SELENIUM)")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        uid, models = conectar_xmlrpc()
    except Exception as e:
        print(f"❌ Error XML-RPC: {e}")
        return

    report_name = buscar_report_name(models, uid)
    guias = obtener_guias(models, uid)
    if not guias:
        print("⚠️ No se encontraron guías en ese periodo.")
        return

    print(f"✅ Se encontraron {len(guias)} guías.")

    session = crear_sesion_http()
    try:
        uid_web = autenticar_web(session)
        print(f"✅ Sesión web autenticada (uid={uid_web}).")
    except Exception as e:
        print(f"❌ No se pudo autenticar sesión web: {e}")
        return

    errores = []
    exitosos = 0
    saltados = 0

    for idx, guia in enumerate(guias, 1):
        doc = (guia.get("l10n_latam_document_number") or f"GUIA_{guia['id']}").replace("/", "-")
        destino = BASE_PATH_PDF / f"{doc}.pdf"

        if destino.exists():
            saltados += 1
            if idx % 100 == 0 or idx == len(guias):
                print(f"[{idx}/{len(guias)}] ⏭️ {doc} (ya existe)")
            continue

        try:
            ok, motivo = descargar_pdf_guia(session, report_name, guia["id"], destino)
            if ok:
                exitosos += 1
                if idx % 25 == 0 or idx == len(guias):
                    print(f"[{idx}/{len(guias)}] ✅ {doc}")
            else:
                errores.append({"id": guia["id"], "doc": doc, "error": motivo})
                print(f"[{idx}/{len(guias)}] ❌ {doc} ({motivo})")
        except requests.HTTPError as e:
            # Si la sesión expira, reautenticar y reintentar 1 vez.
            try:
                autenticar_web(session)
                ok, motivo = descargar_pdf_guia(session, report_name, guia["id"], destino)
                if ok:
                    exitosos += 1
                    print(f"[{idx}/{len(guias)}] ✅ {doc} (reintento OK)")
                else:
                    errores.append({"id": guia["id"], "doc": doc, "error": motivo})
                    print(f"[{idx}/{len(guias)}] ❌ {doc} ({motivo})")
            except Exception as e2:
                errores.append({"id": guia["id"], "doc": doc, "error": f"HTTP: {e} | retry: {e2}"})
                print(f"[{idx}/{len(guias)}] ❌ {doc} (HTTP error)")
        except Exception as e:
            errores.append({"id": guia["id"], "doc": doc, "error": str(e)})
            print(f"[{idx}/{len(guias)}] ❌ {doc} ({str(e)[:80]})")

    print("\n" + "=" * 70)
    print("✅ PROCESO FINALIZADO")
    print(f"   - Descargados: {exitosos}")
    print(f"   - Saltados:    {saltados}")
    print(f"   - Errores:     {len(errores)}")
    print(f"   - Carpeta:     {BASE_PATH_PDF}")
    print("=" * 70)

    guardar_resumen(errores, exitosos, saltados, report_name)


if __name__ == "__main__":
    main()
