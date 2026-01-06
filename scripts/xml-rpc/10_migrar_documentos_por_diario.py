# -*- coding: utf-8 -*-
"""
Migración de documentos desde:
Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero\Descarga_Masiva_FT_GUIA\{AÑO}
→
X:\Finanzas y contabilidad\FACTURACIÓN ELECTRONICA\{AÑO}

Agregando una capa adicional de organización por Diario:
- F110 (Venta nacional)
- F150 (Venta exterior)
- F060 (Venta exterior)
- Facturas Sunat

Soporta dos estructuras de origen por mes:
A) {Mes}\{Diario}\{TipoDocumento}\{TipoArchivo}\files...
B) {Mes}\{TipoDocumento}\{TipoArchivo}\files...   (sin capa de Diario)

Para el caso B, se usará un diario por defecto.
"""

from pathlib import Path
import shutil
import sys
import re
from datetime import datetime

# ============================
# CONFIGURACIÓN
# ============================
AÑO = 2025
ORIGEN_BASE = Path(r"Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero\Descarga_Masiva_FT_GUIA") / str(AÑO)
DESTINO_BASE = Path(r"X:\Finanzas y contabilidad\FACTURACIÓN ELECTRONICA") / str(AÑO)

# Si el mes no se indica, migra todos los meses dentro del año
MESES_A_MIGRAR = []  # por ejemplo: ["06_June", "07_July"]; vacío => todos

# Diario por defecto cuando el origen no tiene capa de diario
DIARIO_POR_DEFECTO = "F110 (Venta nacional)"

# Evitar sobrescribir archivos existentes. Si True: omite cuando existe; si False: renombra con sufijo
OMITIR_SI_EXISTE = True

# Simular la migración (dry-run) para revisar rutas sin mover archivos
MODO_PRUEBA = False

# Tipos de carpetas válidas
TIPOS_DOCUMENTO_VALIDOS = {"01_Facturas", "03_Boletas", "07_Notas_Credito", "08_Notas_Debito"}
TIPOS_ARCHIVO_VALIDOS = {"pdf", "xml", "cdr"}


def es_mes(dir_name: str) -> bool:
    """Heurística simple para detectar carpetas de mes: 'MM_Month'."""
    return bool(re.match(r"^\d{2}_.+", dir_name))


def detectar_estructura_mes(path_mes: Path):
    """
    Retorna 'con_diario' si el mes contiene subcarpetas que NO son tipos de documento (asumimos que son diarios),
    en caso contrario 'sin_diario'.
    """
    hijos = [p.name for p in path_mes.iterdir() if p.is_dir()]
    if not hijos:
        return "vacio"
    # Si alguna subcarpeta coincide con tipos de documento, consideramos 'sin_diario'
    if any(h in TIPOS_DOCUMENTO_VALIDOS for h in hijos):
        return "sin_diario"
    return "con_diario"


def asegurar_carpeta(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def mover_archivo(origen: Path, destino: Path, contadores):
    asegurar_carpeta(destino.parent)
    if destino.exists():
        if OMITIR_SI_EXISTE:
            contadores["omitidos"] += 1
            return
        else:
            # Renombrar con sufijo incremental
            base = destino.stem
            sufijo = 1
            while destino.exists():
                destino = destino.with_name(f"{base}__{sufijo}{destino.suffix}")
                sufijo += 1
    if MODO_PRUEBA:
        contadores["simulados"] += 1
        return
    shutil.move(str(origen), str(destino))
    contadores["movidos"] += 1


def migrar_mes(path_mes: Path, contadores):
    estructura = detectar_estructura_mes(path_mes)
    if estructura == "vacio":
        return

    if estructura == "con_diario":
        # {Mes}\{Diario}\{TipoDocumento}\{TipoArchivo}\files...
        for path_diario in (p for p in path_mes.iterdir() if p.is_dir()):
            diario = path_diario.name
            for path_tipo_doc in (p for p in path_diario.iterdir() if p.is_dir()):
                tipo_doc = path_tipo_doc.name
                if tipo_doc not in TIPOS_DOCUMENTO_VALIDOS:
                    continue
                for path_tipo_archivo in (p for p in path_tipo_doc.iterdir() if p.is_dir()):
                    tipo_archivo = path_tipo_archivo.name
                    if tipo_archivo not in TIPOS_ARCHIVO_VALIDOS:
                        continue
                    for archivo in path_tipo_archivo.glob("*.*"):
                        if not archivo.is_file():
                            continue
                        destino = DESTINO_BASE / path_mes.name / diario / tipo_doc / tipo_archivo / archivo.name
                        mover_archivo(archivo, destino, contadores)
                        contadores["por_diario"][diario] = contadores["por_diario"].get(diario, 0) + 1
    else:
        # 'sin_diario': {Mes}\{TipoDocumento}\{TipoArchivo}\files...
        diario = DIARIO_POR_DEFECTO
        for path_tipo_doc in (p for p in path_mes.iterdir() if p.is_dir()):
            tipo_doc = path_tipo_doc.name
            if tipo_doc not in TIPOS_DOCUMENTO_VALIDOS:
                continue
            for path_tipo_archivo in (p for p in path_tipo_doc.iterdir() if p.is_dir()):
                tipo_archivo = path_tipo_archivo.name
                if tipo_archivo not in TIPOS_ARCHIVO_VALIDOS:
                    continue
                for archivo in path_tipo_archivo.glob("*.*"):
                    if not archivo.is_file():
                        continue
                    destino = DESTINO_BASE / path_mes.name / diario / tipo_doc / tipo_archivo / archivo.name
                    mover_archivo(archivo, destino, contadores)
                    contadores["por_diario"][diario] = contadores["por_diario"].get(diario, 0) + 1


def main():
    inicio = datetime.now()
    print("=" * 70)
    print("▶ MIGRACIÓN DE DOCUMENTOS POR DIARIO")
    print("=" * 70)
    print(f"Año: {AÑO}")
    print(f"Origen : {ORIGEN_BASE}")
    print(f"Destino: {DESTINO_BASE}")
    print(f"Meses  : {'Todos' if not MESES_A_MIGRAR else ', '.join(MESES_A_MIGRAR)}")
    print(f"Default Diario (si no existe capa): {DIARIO_POR_DEFECTO}")
    print(f"Modo prueba (dry-run): {'SI' if MODO_PRUEBA else 'NO'}")
    print("=" * 70)

    if not ORIGEN_BASE.exists():
        print(f"❌ Origen no existe: {ORIGEN_BASE}")
        sys.exit(1)

    contadores = {
        "movidos": 0,
        "omitidos": 0,
        "simulados": 0,
        "por_diario": {}
    }

    asegurar_carpeta(DESTINO_BASE)

    meses = [p for p in ORIGEN_BASE.iterdir() if p.is_dir() and es_mes(p.name)]
    if MESES_A_MIGRAR:
        meses = [p for p in meses if p.name in MESES_A_MIGRAR]

    meses = sorted(meses, key=lambda p: p.name)

    if not meses:
        print("⚠️  No se encontraron carpetas de mes para migrar.")
        return

    for path_mes in meses:
        print(f"\n📦 Migrando mes: {path_mes.name}")
        migrar_mes(path_mes, contadores)

    fin = datetime.now()
    print("\n" + "=" * 70)
    print("✅ MIGRACIÓN FINALIZADA")
    print("=" * 70)
    print(f"Tiempo total: {fin - inicio}")
    if MODO_PRUEBA:
        print(f"Archivos simulados (sin mover): {contadores['simulados']}")
    print(f"Archivos movidos: {contadores['movidos']}")
    print(f"Archivos omitidos por existir: {contadores['omitidos']}")
    print("\n📊 Por Diario:")
    for diario, count in sorted(contadores["por_diario"].items(), key=lambda x: x[0]):
        print(f"   • {diario}: {count}")
    print("=" * 70)


if __name__ == "__main__":
    main()

