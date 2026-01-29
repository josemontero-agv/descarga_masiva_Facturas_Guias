import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from calendar import monthrange

# Configurar encoding para la consola de Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================
# CONFIGURACIÓN DE RUTAS BASE
# ============================================
CORE_DIR = Path(__file__).parent
PROJECT_ROOT = CORE_DIR.parent

# ============================================
# CARGA DE AMBIENTE
# ============================================
# Por defecto buscamos el ambiente en una variable de entorno, si no, usa "produccion"
# Esto permite cambiarlo fácilmente sin editar el código del core
AMBIENTE = os.getenv("APP_AMBIENTE", "produccion")

env_file = f'.env.{AMBIENTE}'
env_path = PROJECT_ROOT / env_file

if not env_path.exists():
    # Búsqueda recursiva hacia arriba por si acaso
    curr = PROJECT_ROOT
    while curr != curr.parent:
        test_env = curr / env_file
        if test_env.exists():
            env_path = test_env
            break
        curr = curr.parent

if not env_path.exists():
    # Si no existe, intentar cargar .env genérico
    env_path = PROJECT_ROOT / '.env'

if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    print(f"⚠️ Advertencia: No se encontró archivo de configuración (.env.{AMBIENTE} o .env)")

# ============================================
# CREDENCIALES ODOO
# ============================================
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USER = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

# ============================================
# CONFIGURACIÓN DE FECHAS (VALORES POR DEFECTO)
# ============================================
# Estos valores pueden ser sobreescritos en los scripts de ejecución
AHORA = datetime.now()
DEFAULT_AÑO = int(os.getenv('DEFAULT_AÑO', AHORA.year))
DEFAULT_MES = int(os.getenv('DEFAULT_MES', AHORA.month))

MESES_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def get_periodo_info(año=None, mes=None):
    año = año or DEFAULT_AÑO
    mes = mes or DEFAULT_MES
    _, ultimo_dia = monthrange(año, mes)
    fecha_inicio = f"{año}-{mes:02d}-01"
    fecha_fin = f"{año}-{mes:02d}-{ultimo_dia}"
    nombre_mes = MESES_ESPANOL.get(mes, "Desconocido")
    nombre_carpeta_mes = f"{mes:02d}_{nombre_mes}"
    return {
        "año": año,
        "mes": mes,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "nombre_mes": nombre_mes,
        "nombre_carpeta_mes": nombre_carpeta_mes
    }

# ============================================
# RUTAS DE DESCARGA
# ============================================
def get_base_path(año, nombre_carpeta_mes):
    if AMBIENTE == "produccion":
        return Path(rf"V:\{año}\{nombre_carpeta_mes}")
    else:
        return PROJECT_ROOT / "Prueba_Octubre" / nombre_carpeta_mes

MAPEO_CARPETAS = {
    'Factura': '01_Facturas',
    'Boleta': '03_Boletas',
    'Nota de Crédito': '07_Notas_Credito',
    'Nota de Débito': '08_Notas_Debito',
    'Guía de Remisión': '09_Guias_Remision'
}
