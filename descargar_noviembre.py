# -*- coding: utf-8 -*-
"""
Script dedicado para descargar NOVIEMBRE 2025
Ejecutar en una terminal independiente para procesamiento paralelo
"""

# Importar el script principal pero con MES fijo
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar y ejecutar con configuración específica
if __name__ == "__main__":
    # Configurar MES antes de importar
    import os
    os.environ['FORCE_MES'] = '11'
    os.environ['FORCE_NOMBRE_MES'] = 'Noviembre'
    
    print("="*70)
    print(" 📅 DESCARGA DE NOVIEMBRE 2025")
    print("="*70)
    
    # Importar el script principal
    from importlib import import_module
    main_script = import_module('01_descarga_Facturas')
    
    # Modificar variables globales
    main_script.MES = 11
    main_script.AÑO = 2025
    from calendar import monthrange
    from datetime import datetime
    
    main_script.ultimo_dia = monthrange(2025, 11)[1]
    main_script.FECHA_INICIO = "2025-11-01"
    main_script.FECHA_FIN = f"2025-11-{main_script.ultimo_dia}"
    main_script.nombre_mes = "November"
    main_script.BASE_PATH = rf"Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero\Descarga_Masiva_FT_GUIA\2025\11_November"
    
    # Ejecutar main
    main_script.main()

