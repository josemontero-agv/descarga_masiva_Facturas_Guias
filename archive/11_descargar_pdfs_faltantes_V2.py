# -*- coding: utf-8 -*-
"""
Rescate de PDFs faltantes de comprobantes SIN Selenium.

Lee FACTURAS_ANALISIS_sin_pdf.txt y descarga cada PDF por HTTP usando
sesion autenticada de Odoo:
    /report/pdf/<report_name>/<move_id>

Prioriza el reporte "Factura AGR".
"""

import os
import sys
import time
import json
import ssl
import re
import xmlrpc.client
from datetime import datetime
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv


# Importaciones para ejecución simultánea segura
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


# Configurar encoding para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================
AMBIENTE = "produccion"  # "desarrollo" o "produccion"
AÑO = 2026
MES = 2

# Objetivo solicitado por usuario
NOMBRE_REPORTE_OBJETIVO = "Factura AGR"

# Fallback clásico de Odoo (si no existe Factura AGR en ese ambiente)
REPORTE_FALLBACK = "account.report_invoice"


# ============================================================================
# CARGA DE ENTORNO Y RUTAS
# ============================================================================
project_root = Path(__file__).parent.parent
env_file = f".env.{AMBIENTE}"
env_path = project_root / env_file

if not env_path.exists():
    print(f"❌ Error: no se encontró '{env_file}' en {project_root}")
    sys.exit(1)

print(f"📁 Cargando configuración desde: {env_path} (Ambiente: {AMBIENTE})")
load_dotenv(env_path, override=True)

ODOO_URL = (os.getenv("ODOO_URL") or "").rstrip("/")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
    print("❌ Faltan variables ODOO_URL, ODOO_DB, ODOO_USER o ODOO_PASSWORD")
    sys.exit(1)

MESES_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

nombre_mes = MESES_ESPANOL.get(MES, datetime(AÑO, MES, 1).strftime("%B"))
nombre_carpeta_mes = f"{MES:02d}_{nombre_mes}"

if AMBIENTE == "produccion":
    BASE_PATH_RAIZ = Path(rf"V:\{AÑO}\{nombre_carpeta_mes}")
else:
    BASE_PATH_RAIZ = project_root / "Prueba_Octubre" / nombre_carpeta_mes
    print(f"🔧 MODO DESARROLLO: Guardando en ruta local: {BASE_PATH_RAIZ}")

Path(BASE_PATH_RAIZ).mkdir(parents=True, exist_ok=True)
print(f"🔧 Proceso PID: {os.getpid()} | Base: {BASE_PATH_RAIZ}")

MAPEO_CARPETAS = {
    "Factura": "01_Facturas",
    "Boleta": "03_Boletas",
    "Nota de Crédito": "07_Notas_Credito",
    "Nota de Débito": "08_Notas_Debito",
}


# ============================================================================
# BLOQUEOS (ejecución simultánea)
# ============================================================================
def obtener_bloqueo_archivo(ruta_archivo, timeout=5):
    """Obtiene bloqueo exclusivo por archivo .lock."""
    lock_file_path = Path(str(ruta_archivo) + ".lock")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Limpieza de lock huérfano (si no existe el PDF final y lock viejo)
            if lock_file_path.exists():
                try:
                    antiguedad = time.time() - lock_file_path.stat().st_mtime
                    if antiguedad > 300 and not Path(ruta_archivo).exists():
                        os.remove(lock_file_path)
                except Exception:
                    pass

            if sys.platform == "win32":
                try:
                    lock_file = open(lock_file_path, "xb")
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except (FileExistsError, IOError, OSError):
                    time.sleep(0.1)
                    continue
            else:
                try:
                    lock_file = open(lock_file_path, "x")
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (FileExistsError, IOError, OSError):
                    time.sleep(0.1)
                    continue

            return lock_file
        except Exception:
            time.sleep(0.1)

    return None


def liberar_bloqueo_archivo(lock_file, ruta_archivo):
    """Libera bloqueo y elimina .lock."""
    if lock_file:
        try:
            lock_file.close()
        except Exception:
            pass

    lock_file_path = Path(str(ruta_archivo) + ".lock")
    try:
        if lock_file_path.exists():
            os.remove(lock_file_path)
    except Exception:
        pass


def verificar_y_reservar_descarga(ruta_final):
    if ruta_final.exists():
        return False, None

    lock_file = obtener_bloqueo_archivo(ruta_final, timeout=2)
    if lock_file is None:
        return False, None

    if ruta_final.exists():
        liberar_bloqueo_archivo(lock_file, ruta_final)
        return False, None

    return True, lock_file


# ============================================================================
# XML-RPC + HTTP SESSION
# ============================================================================
def conectar_xmlrpc():
    print("📡 Conectando por XML-RPC...")
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
    r = session.post(
        f"{ODOO_URL}/web/session/authenticate",
        data=json.dumps(payload),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    uid = ((data or {}).get("result") or {}).get("uid")
    if not uid:
        raise RuntimeError(f"Auth web fallida: {data}")
    return uid


def buscar_report_names_factura(models, uid):
    """
    Retorna lista ordenada de report_name para account.move.
    1) Prioriza "Factura AGR"
    2) Luego otros reportes con factura+agr
    3) Fallback account.report_invoice
    """
    candidatos = []

    # Búsqueda exacta/fuerte
    dominio_objetivo = [
        ("model", "=", "account.move"),
        ("name", "ilike", "Factura AGR"),
    ]
    reps_objetivo = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [dominio_objetivo],
        {"fields": ["id", "name", "report_name", "report_type"], "limit": 10},
    )

    for rep in reps_objetivo:
        rn = rep.get("report_name")
        if rn and rn not in candidatos:
            candidatos.append(rn)
            print(f"✅ Reporte objetivo: {rep.get('name')} | {rn}")

    # Búsqueda amplia
    dominio_amplio = [
        ("model", "=", "account.move"),
        ("name", "ilike", "factura"),
    ]
    reps_amplio = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "ir.actions.report",
        "search_read",
        [dominio_amplio],
        {"fields": ["id", "name", "report_name", "report_type"], "limit": 50},
    )
    for rep in reps_amplio:
        nombre = (rep.get("name") or "").lower()
        rn = rep.get("report_name")
        if not rn:
            continue
        if ("agr" in nombre or "agr" in rn.lower()) and rn not in candidatos:
            candidatos.append(rn)
            print(f"ℹ️ Reporte AGR alternativo: {rep.get('name')} | {rn}")

    if REPORTE_FALLBACK not in candidatos:
        candidatos.append(REPORTE_FALLBACK)
        print(f"ℹ️ Fallback agregado: {REPORTE_FALLBACK}")

    return candidatos


# ============================================================================
# LÓGICA DE RESCATE
# ============================================================================
def leer_archivo_analisis():
    """Lee FACTURAS_ANALISIS_sin_pdf.txt y extrae (id, nombre)."""
    ruta_analisis = BASE_PATH_RAIZ / "Resumen de errores" / "FACTURAS_ANALISIS_sin_pdf.txt"
    if not ruta_analisis.exists():
        print(f"❌ No se encontró: {ruta_analisis}")
        return []

    print(f"📖 Leyendo: {ruta_analisis}")
    contenido = ruta_analisis.read_text(encoding="utf-8", errors="ignore")

    patron = r"\[(\d+)\]\s+Comprobante:\s+([^\n]+)\s+ID Odoo:\s+(\d+)"
    matches = re.findall(patron, contenido)

    comprobantes = []
    for num, comprobante, odoo_id in matches:
        comprobantes.append(
            {
                "id": int(odoo_id.strip()),
                "nombre": comprobante.strip(),
                "numero": int(num),
            }
        )

    print(f"✅ Se encontraron {len(comprobantes)} comprobantes sin PDF")
    return comprobantes


def obtener_info_comprobante(uid, models, move_id):
    """Obtiene diario y tipo de documento para construir ruta destino."""
    try:
        rows = models.execute_kw(
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "account.move",
            "read",
            [[move_id]],
            {"fields": ["id", "name", "journal_id", "l10n_latam_document_type_id", "invoice_date"]},
        )
        if not rows:
            return None
        comp = rows[0]

        diario_data = comp.get("journal_id")
        diario = diario_data[1] if diario_data else "Sin_Diario"
        diario_limpio = "".join(
            [c if c.isalnum() or c in (" ", "-", "_", ".") else "_" for c in diario]
        ).strip()

        tipo_doc_data = comp.get("l10n_latam_document_type_id")
        tipo_doc_nombre = tipo_doc_data[1] if tipo_doc_data and len(tipo_doc_data) > 1 else "Factura"

        tipo_doc_carpeta = "01_Facturas"
        for tipo_key, carpeta in MAPEO_CARPETAS.items():
            if tipo_key.lower() in tipo_doc_nombre.lower():
                tipo_doc_carpeta = carpeta
                break

        return {
            "id": comp["id"],
            "name": comp.get("name", ""),
            "diario": diario_limpio,
            "tipo_doc": tipo_doc_carpeta,
            "fecha": comp.get("invoice_date", ""),
        }
    except Exception as e:
        print(f"   ⚠️ Error obteniendo info de comprobante {move_id}: {e}")
        return None


def descargar_pdf_move(session, report_name, move_id, ruta_final):
    """Descarga PDF de account.move por endpoint /report/pdf/..."""
    url = f"{ODOO_URL}/report/pdf/{report_name}/{move_id}"
    r = session.get(url, timeout=90, allow_redirects=True)
    r.raise_for_status()

    contenido = r.content or b""
    content_type = (r.headers.get("Content-Type") or "").lower()
    es_pdf = contenido.startswith(b"%PDF") or "application/pdf" in content_type

    if not es_pdf:
        return False, "Respuesta no es PDF (posible redirect/login/html)"

    ruta_final.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_final, "wb") as f:
        f.write(contenido)
    return True, None


def descargar_pdfs_faltantes_v2(comprobantes, uid, models, session, report_names):
    print(f"\n⚡ Iniciando rescate HTTP de {len(comprobantes)} PDFs faltantes...")
    total = len(comprobantes)
    descargados = 0
    errores = 0
    inicio = time.time()

    resultados = {
        "exitosos": [],
        "fallidos": [],
        "ya_existentes": [],
    }

    for idx, comp_info in enumerate(comprobantes, 1):
        move_id = comp_info["id"]
        nombre_comprobante = comp_info["nombre"]
        print(f"\n[{idx}/{total}] 📄 {nombre_comprobante} (ID: {move_id})")

        info = obtener_info_comprobante(uid, models, move_id)
        if not info:
            errores += 1
            resultados["fallidos"].append(
                {"nombre": nombre_comprobante, "id": move_id, "error": "No se pudo obtener info XML-RPC"}
            )
            continue

        ruta_pdf = BASE_PATH_RAIZ / info["diario"] / info["tipo_doc"] / "pdf"
        nombre_limpio = nombre_comprobante.replace("/", "-").replace("\\", "-")
        ruta_final = ruta_pdf / f"{nombre_limpio}.pdf"

        puede_descargar, lock_file = verificar_y_reservar_descarga(ruta_final)
        if not puede_descargar:
            print("   ⏭️ Ya existe o en proceso")
            resultados["ya_existentes"].append(
                {
                    "nombre": nombre_comprobante,
                    "id": move_id,
                    "ruta": str(ruta_final),
                }
            )
            continue

        try:
            exito = False
            ultimo_error = "Sin detalle"
            reporte_exitoso = None

            # Probar reportes candidatos en orden
            for rep in report_names:
                try:
                    ok, motivo = descargar_pdf_move(session, rep, move_id, ruta_final)
                    if ok:
                        exito = True
                        reporte_exitoso = rep
                        print(f"   ✅ Descargado con reporte: {rep}")
                        break
                    ultimo_error = motivo
                except requests.HTTPError as he:
                    # Reautenticar una vez y reintentar el mismo reporte
                    try:
                        autenticar_sesion_web(session)
                        ok, motivo = descargar_pdf_move(session, rep, move_id, ruta_final)
                        if ok:
                            exito = True
                            print(f"   ✅ Descargado con reporte: {rep} (reintento)")
                            break
                        ultimo_error = motivo
                    except Exception as e2:
                        ultimo_error = f"HTTP {he} | retry {e2}"
                except Exception as e:
                    ultimo_error = str(e)

            if exito:
                descargados += 1
                resultados["exitosos"].append(
                    {
                        "nombre": nombre_comprobante,
                        "id": move_id,
                        "reporte": reporte_exitoso,
                        "ruta": str(ruta_final),
                    }
                )
                elapsed = time.time() - inicio
                vel = descargados / elapsed if elapsed > 0 else 0
                eta = (total - idx) / vel if vel > 0 else 0
                print(f"   🚀 Vel: {vel:.2f} docs/s | ETA: {eta/60:.1f} min")
            else:
                errores += 1
                print(f"   ❌ Falló en todos los reportes ({ultimo_error})")
                resultados["fallidos"].append(
                    {"nombre": nombre_comprobante, "id": move_id, "error": ultimo_error}
                )
        finally:
            liberar_bloqueo_archivo(lock_file, ruta_final)

    t = time.time() - inicio
    print(f"\n✨ Proceso completado en {t/60:.1f} minutos.")
    print(f"📊 Total: {total} | Descargados: {descargados} | Errores: {errores}")
    return resultados


def guardar_log_revision(resultados, report_names):
    """Guarda reporte detallado."""
    try:
        carpeta_logs = BASE_PATH_RAIZ / "Resumen de errores"
        carpeta_logs.mkdir(parents=True, exist_ok=True)

        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_archivo = carpeta_logs / f"RESCATE_PDF_V2_LOG_{fecha_str}.txt"

        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(f"{'='*70}\n")
            f.write("REPORTE DE RESCATE DE PDFs FALTANTES (V2 SIN SELENIUM)\n")
            f.write(f"{'='*70}\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Mes procesado: {nombre_carpeta_mes}\n")
            f.write(f"Reporte objetivo: {NOMBRE_REPORTE_OBJETIVO}\n")
            f.write(f"Reportes probados: {', '.join(report_names)}\n")
            f.write(f"{'='*70}\n\n")

            f.write("RESUMEN EJECUTIVO:\n")
            f.write(f"✅ Recuperados con éxito: {len(resultados['exitosos'])}\n")
            f.write(f"❌ Siguen fallando:       {len(resultados['fallidos'])}\n")
            f.write(f"⏭️ Ya estaban presentes:  {len(resultados['ya_existentes'])}\n\n")

            if resultados["fallidos"]:
                f.write(f"{'='*70}\n")
                f.write("DETALLE DE DOCUMENTOS QUE SIGUEN FALLANDO:\n")
                f.write(f"{'='*70}\n")
                for err in resultados["fallidos"]:
                    f.write(f"• {err['nombre']} (ID: {err['id']}) - Error: {err['error']}\n")
                f.write("\n")

            if resultados["exitosos"]:
                f.write(f"{'='*70}\n")
                f.write("DETALLE DE DOCUMENTOS RECUPERADOS:\n")
                f.write(f"{'='*70}\n")
                for ok in resultados["exitosos"]:
                    f.write(
                        f"• {ok['nombre']} (ID: {ok['id']}) | "
                        f"Reporte: {ok.get('reporte', 'N/A')} | Ruta: {ok.get('ruta', 'N/A')}\n"
                    )
                f.write("\n")

            if resultados["ya_existentes"]:
                f.write(f"{'='*70}\n")
                f.write("DETALLE DE DOCUMENTOS YA EXISTENTES / SALTADOS:\n")
                f.write(f"{'='*70}\n")
                for item in resultados["ya_existentes"]:
                    f.write(
                        f"• {item['nombre']} (ID: {item['id']}) | "
                        f"Ruta: {item.get('ruta', 'N/A')}\n"
                    )

        print(f"💾 Log guardado en: {ruta_archivo}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar log: {e}")


def main():
    print("\n" + "#" * 70)
    print("# RESCATE PDFs FALTANTES V2 (HTTP + XML-RPC, SIN SELENIUM)")
    print(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    comprobantes = leer_archivo_analisis()
    if not comprobantes:
        print("❌ No se encontraron comprobantes para procesar")
        return

    try:
        uid, models = conectar_xmlrpc()
    except Exception as e:
        print(f"❌ Error conectando XML-RPC: {e}")
        return

    report_names = buscar_report_names_factura(models, uid)

    session = crear_sesion_http()
    try:
        uid_web = autenticar_sesion_web(session)
        print(f"✅ Sesión web autenticada (uid={uid_web})")
    except Exception as e:
        print(f"❌ Error autenticando sesión web: {e}")
        return

    resultados = descargar_pdfs_faltantes_v2(comprobantes, uid, models, session, report_names)
    guardar_log_revision(resultados, report_names)


if __name__ == "__main__":
    main()
