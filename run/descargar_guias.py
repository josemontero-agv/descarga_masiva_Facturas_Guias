import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib3

# Añadir la raíz del proyecto al path para importar core y modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.config import (
    ODOO_DB,
    ODOO_PASSWORD,
    ODOO_URL,
    ODOO_USER,
    get_base_path,
    get_periodo_info,
)
from core.odoo_client import conectar_odoo
from modules.guias_module import (
    descargar_xml_cdr_guia,
    liberar_bloqueo_archivo,
    verificar_y_reservar_descarga,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def guardar_resumen_guias(base_path_raiz, analisis):
    """Guardar resumen de guías faltantes para reparación"""
    try:
        carpeta_logs = base_path_raiz / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)
        ruta_archivo = carpeta_logs / "GUIAS_RESUMEN_COMPLETO_PROBLEMAS.txt"

        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"{'#'*70}\n")
            f.write(f"# RESUMEN DE DESCARGA DE GUIAS\n")
            f.write(f"{'#'*70}\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"❌ Fallidos/Faltantes: {len(analisis['errores'])}\n")
            f.write(f"✅ Exitosos:           {len(analisis['comprobantes_ok'])}\n")
            f.write(f"{'#'*70}\n\n")

            if analisis['errores']:
                f.write("IDs DE ODOO CON ERRORES (Para Reparación):\n")
                ids = [str(item['id']) for item in analisis['errores']]
                f.write(", ".join(ids))
                f.write("\n")
        print(f"   📊 Resumen de guías guardado en: {ruta_archivo}")
    except Exception as e:
        print(f"   ⚠️ No se pudo guardar el resumen de guías: {e}")


def buscar_report_name_guia(models, uid):
    """Detecta report_name para e-Guía de Remisión AGR."""
    dominio = [
        ("model", "=", "stock.picking"),
        ("name", "ilike", "Guía de Remisión AGR"),
    ]
    reportes = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [dominio],
        {"fields": ["id", "name", "report_name", "report_type"], "limit": 5},
    )
    if reportes:
        rep = reportes[0]
        report_name = rep.get("report_name") or "agr_shiping_guide.report_edi_gre"
        print(f"✅ Reporte guía detectado: {rep.get('name')} | {report_name}")
        return report_name

    fallback = "agr_shiping_guide.report_edi_gre"
    print(f"⚠️ No se detectó e-Guía AGR, usando fallback: {fallback}")
    return fallback


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


def descargar_pdf_guia_http(session, report_name, guia_id, ruta_final):
    url = f"{ODOO_URL.rstrip('/')}/report/pdf/{report_name}/{guia_id}"
    r = session.get(url, timeout=90, allow_redirects=True)
    r.raise_for_status()
    contenido = r.content or b""
    ctype = (r.headers.get("Content-Type") or "").lower()
    es_pdf = contenido.startswith(b"%PDF") or "application/pdf" in ctype
    if not es_pdf:
        return False, "Respuesta no es PDF (login/html/redirección)"

    ruta_final.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_final, "wb") as f:
        f.write(contenido)
    return True, None


def main():
    print(f"\n{'#'*70}")
    print("# PROCESO INTEGRAL DE DESCARGA DE GUÍAS (XML + PDF)")
    print(f"# Ejecución Segura para Terminales Múltiples (PID: {os.getpid()})")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    # 1. Configuración de periodo
    año = 2026
    mes = 2
    info = get_periodo_info(año, mes)
    base_path_raiz = get_base_path(año, info['nombre_carpeta_mes'])
    base_path_guia = base_path_raiz / "09_Guias_Remision"

    (base_path_guia / "xml").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "cdr").mkdir(parents=True, exist_ok=True)
    (base_path_guia / "pdf").mkdir(parents=True, exist_ok=True)

    # 2. Conexión Odoo (XML-RPC)
    uid, models = conectar_odoo()
    if not uid:
        print("❌ No se pudo conectar a Odoo. Verifica tu .env")
        return

    # 3. Buscar Guías
    print(f"🔍 Buscando guías del {info['fecha_inicio']} al {info['fecha_fin']}...")
    domain = [
        ('state', '=', 'done'),
        ('picking_type_id', '=', 2),
        ('l10n_latam_document_number', '!=', False),
        ('date_done', '>=', f"{info['fecha_inicio']} 00:00:00"),
        ('date_done', '<=', f"{info['fecha_fin']} 23:59:59"),
    ]
    guias = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'stock.picking', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'l10n_latam_document_number', 'date_done'], 'order': 'date_done asc'}
    )

    if not guias:
        print("⚠️ No se encontraron guías en este periodo.")
        return

    print(f"✅ Se encontraron {len(guias)} guías.")

    report_name = buscar_report_name_guia(models, uid)
    session = crear_sesion_http()
    try:
        uid_web = autenticar_sesion_web(session)
        print(f"✅ Sesión web autenticada (uid={uid_web}).")
    except Exception as e:
        print(f"❌ Error autenticando sesión web: {e}")
        return

    stats = {'descargados': 0, 'errores': 0, 'saltados': 0}
    analisis = {'errores': [], 'comprobantes_ok': []}
    for idx, guia in enumerate(guias, 1):
        num_doc = guia["l10n_latam_document_number"]
        nombre_base = num_doc.replace("/", "-").replace("\\", "-")
        ruta_pdf = base_path_guia / "pdf" / f"{nombre_base}.pdf"

        puede_procesar, lock_file = verificar_y_reservar_descarga(ruta_pdf)
        if not puede_procesar:
            stats["saltados"] += 1
            analisis["comprobantes_ok"].append({"id": guia["id"], "nombre": num_doc})
            if idx % 100 == 0 or idx == len(guias):
                print(f"   [{idx}/{len(guias)}] Skipped: {num_doc} (Ya existe o en proceso)")
            continue

        try:
            # A) XML + CDR por XML-RPC
            descargar_xml_cdr_guia(uid, models, guia, base_path_guia)

            # B) PDF por HTTP autenticado
            ok, motivo = descargar_pdf_guia_http(session, report_name, guia["id"], ruta_pdf)
            if not ok:
                try:
                    autenticar_sesion_web(session)
                    ok, motivo = descargar_pdf_guia_http(session, report_name, guia["id"], ruta_pdf)
                except Exception as e_auth:
                    motivo = f"{motivo} | reauth: {e_auth}"

            if ok:
                stats["descargados"] += 1
                analisis["comprobantes_ok"].append({"id": guia["id"], "nombre": num_doc})
                if idx % 25 == 0 or idx == len(guias):
                    print(f"   [{idx}/{len(guias)}] ✅ {num_doc}")
            else:
                stats["errores"] += 1
                analisis["errores"].append({"id": guia["id"], "nombre": num_doc, "error": motivo})
                print(f"   [{idx}/{len(guias)}] ❌ {num_doc} ({motivo})")
        except Exception as e:
            stats["errores"] += 1
            analisis["errores"].append({"id": guia["id"], "nombre": num_doc, "error": str(e)})
            print(f"   [{idx}/{len(guias)}] ❌ {num_doc} ({str(e)[:80]})")
        finally:
            liberar_bloqueo_archivo(lock_file, ruta_pdf)

    guardar_resumen_guias(base_path_raiz, analisis)

    print(f"\n{'='*70}")
    print(f"✅ PROCESO FINALIZADO")
    print(f"   - Procesados:  {stats['descargados']}")
    print(f"   - Con errores: {stats['errores']}")
    print(f"   - Saltados:    {stats['saltados']}")
    print(f"   - Ubicación:   {base_path_guia}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
