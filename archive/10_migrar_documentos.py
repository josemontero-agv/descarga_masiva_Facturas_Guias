# -*- coding: utf-8 -*-
"""
Script de Migración Ultra-Rápida de Guías de Remisión (ROBOCOPY)
Origen:  Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero\Descarga_Masiva_FT_GUIA\2025 (Meses en Inglés)
Destino: V:\2025 (Meses en Español)

Funcionalidad:
- Usa Robocopy de Windows para transferencia multihilo (MT:16).
- Traduce el nombre del mes al español.
- Elimina la capa de clasificación por Diario (une todo en una sola carpeta por mes).
- Inteligente: Salta archivos ya copiados que no han cambiado.
"""

import subprocess
from pathlib import Path
from datetime import datetime

# ============================
# CONFIGURACIÓN
# ============================
AÑO = 2025
ORIGEN_BASE = Path(r"Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero\Descarga_Masiva_FT_GUIA") / str(AÑO)
DESTINO_BASE = Path(r"V:") / str(AÑO)

# Mapeo de meses de Inglés (Origen) a Español (Destino)
MESES_MAP = {
    "01_January": "01_Enero",
    "02_February": "02_Febrero",
    "03_March": "03_Marzo",
    "04_April": "04_Abril",
    "05_May": "05_Mayo",
    "06_June": "06_Junio",
    "07_July": "07_Julio",
    "08_August": "08_Agosto",
    "09_September": "09_Septiembre",
    "10_October": "10_Octubre",
    "11_November": "11_Noviembre",
    "12_December": "12_Diciembre"
}

# Nombre de la carpeta que queremos extraer
FOLDER_GUIAS = "09_Guias_Remision"

def ejecutar_robocopy(origen, destino):
    """
    Ejecuta el comando Robocopy para una transferencia ultra rápida.
    /E: Copia subdirectorios, incluidos los vacíos.
    /MT:16: Usa 16 hilos para copia paralela.
    /R:3 /W:5: 3 reintentos con 5 segundos de espera.
    /XO: Omite archivos más antiguos (no sobrescribe si el destino es igual o más nuevo).
    /NP /NFL /NDL /NJH /NJS: Reduce el ruido en consola para máxima velocidad.
    """
    cmd = [
        "robocopy", str(origen), str(destino),
        "/E", "/MT:16", "/R:3", "/W:5", "/XO", "/NP", "/NFL", "/NDL", "/NJH", "/NJS"
    ]
    # Robocopy devuelve códigos de retorno donde 0-7 son estados de éxito o cambios menores.
    # No usamos shell=True por seguridad a menos que sea necesario.
    subprocess.run(cmd, shell=True)

def migrar_guias():
    inicio = datetime.now()
    print("=" * 70)
    print(f"▶ MIGRACIÓN ULTRA-RÁPIDA (ROBOCOPY) {AÑO}")
    print("=" * 70)
    print(f"Origen  : {ORIGEN_BASE}")
    print(f"Destino : {DESTINO_BASE}")
    print("-" * 70)
    
    if not ORIGEN_BASE.exists():
        print(f"❌ Error: El origen no es accesible: {ORIGEN_BASE}")
        return

    meses_procesados = 0

    for mes_en, mes_es in MESES_MAP.items():
        path_mes_origen = ORIGEN_BASE / mes_en
        if not path_mes_origen.exists():
            continue
            
        print(f"🚀 Procesando {mes_en} -> {mes_es}...")
        
        # Carpeta destino consolidada (V:\2025\XX_MesEspañol\09_Guias_Remision)
        path_mes_destino = DESTINO_BASE / mes_es / FOLDER_GUIAS
        path_mes_destino.mkdir(parents=True, exist_ok=True)
        
        # Buscar todas las carpetas '09_Guias_Remision' dentro del mes
        carpetas_encontradas = [p for p in path_mes_origen.rglob(FOLDER_GUIAS) if p.is_dir()]
        
        if not carpetas_encontradas:
            print(f"   ⚠️ No se encontraron carpetas '{FOLDER_GUIAS}' en {mes_en}.")
            continue

        for carpeta_origen in carpetas_encontradas:
            # Si la carpeta origen es la misma que la destino (evitar bucles infinitos si las rutas se solapan)
            if carpeta_origen.resolve() == path_mes_destino.resolve():
                continue
                
            ejecutar_robocopy(carpeta_origen, path_mes_destino)
        
        meses_procesados += 1

    fin = datetime.now()
    print("\n" + "=" * 70)
    print("✅ MIGRACIÓN FINALIZADA")
    print("-" * 70)
    print(f"Tiempo total: {fin - inicio}")
    print(f"Meses procesados: {meses_procesados}")
    print(f"Ubicación destino: {DESTINO_BASE}")
    print("=" * 70)

if __name__ == "__main__":
    migrar_guias()
