import xmlrpc.client
import os  # Importamos la librería del sistema operativo para leer variables de entorno
from dotenv import load_dotenv  # Importamos la función para cargar el archivo .env
import ssl
from urllib.parse import urlparse

# --- 1. CARGAR VARIABLES DE ENTORNO ---
# ============================================
# CONFIGURACIÓN DE AMBIENTE
# ============================================
# Cambiar entre "desarrollo" y "produccion"
AMBIENTE = "desarrollo"  # ← CAMBIAR AQUÍ: "desarrollo" o "produccion"

# El archivo .env está en la raíz del proyecto (2 niveles arriba desde Prueba_test_odoo_conexion/)
script_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.dirname(script_dir)  # Sube un nivel desde Prueba_test_odoo_conexion a utils
project_root = os.path.dirname(utils_dir)  # Sube otro nivel desde utils a la raíz
env_file = f'.env.{AMBIENTE}'
env_path = os.path.join(project_root, env_file)

print(f"📁 Buscando archivo {env_file} en: {env_path}")

# Verificar si el archivo existe
if os.path.exists(env_path):
    print(f"✅ Archivo encontrado (Ambiente: {AMBIENTE})")
    load_dotenv(env_path, override=True)
else:
    print(f"⚠️  Archivo {env_file} no encontrado, intentando con .env...")
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        print(f"✅ Archivo .env encontrado")
        load_dotenv(env_path, override=True)
    else:
        print(f"❌ Error: No se encontró el archivo '{env_file}' ni '.env'")
        print(f"💡 Crea el archivo con las credenciales de Odoo")
        print(f"   Archivos disponibles:")
        print(f"   - .env.desarrollo  (para pruebas)")
        print(f"   - .env.produccion  (para ambiente real)")
        exit(1)

# Leemos las credenciales desde las variables de entorno que cargamos.
# os.getenv() obtiene el valor de la variable especificada.
url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USER')
password = os.getenv('ODOO_PASSWORD')

# --- DEPURACIÓN: Mostrar qué variables se cargaron (sin mostrar la contraseña completa) ---
print("\n🔍 Variables de entorno cargadas:")
print(f"  ODOO_URL: {url if url else '❌ NO ENCONTRADA'}")
print(f"  ODOO_DB: {db if db else '❌ NO ENCONTRADA'}")
print(f"  ODOO_USER: {username if username else '❌ NO ENCONTRADA'}")
print(f"  ODOO_PASSWORD: {'✅ Configurada' if password else '❌ NO ENCONTRADA'}")

# Verificamos que todas las variables necesarias se hayan cargado correctamente.
if not all([url, db, username, password]):
    print("\n❌ Error: Asegúrate de que las variables ODOO_URL, ODOO_DB, ODOO_USER y ODOO_PASSWORD estén definidas en tu archivo .env")
    print("   El archivo .env debe estar en la misma carpeta que este script.")
    exit(1)

# --- VALIDACIÓN Y NORMALIZACIÓN DE URL ---
# Eliminar espacios en blanco
url = url.strip()

# Asegurar que la URL no termine con /
if url.endswith('/'):
    url = url.rstrip('/')

# Verificar que la URL tenga protocolo
parsed_url = urlparse(url)
if not parsed_url.scheme:
    print(f"\n⚠️  Advertencia: La URL no tiene protocolo (http:// o https://). Intentando con https://")
    url = f"https://{url}"

print(f"\n🌐 URL final que se usará: {url}")

# --- 2. AUTENTICACIÓN ---
# Configurar el proxy XML-RPC con timeout y manejo de SSL
common_url = f'{url}/xmlrpc/2/common'
print(f"\n🔌 Intentando conectar a: {common_url}")

# Crear contexto SSL que acepta certificados (útil para desarrollo)
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

try:
    # Crear el proxy con timeout
    common = xmlrpc.client.ServerProxy(
        common_url,
        allow_none=True,
        use_datetime=True,
        context=context,
        verbose=False  # Cambiar a True para ver las peticiones HTTP
    )
    
    print("📡 Probando conexión al servidor...")
    
    # Primero intentamos verificar la versión (esto confirma que el endpoint está disponible)
    try:
        version_info = common.version()
        print(f"✅ Servidor Odoo accesible. Versión: {version_info}")
    except Exception as ver_e:
        print(f"⚠️  No se pudo obtener la versión del servidor: {ver_e}")
        print("   Continuando con la autenticación...")
    
    # Intentar autenticación
    print(f"🔐 Intentando autenticar usuario: {username} en base de datos: {db}")
    uid = common.authenticate(db, username, password, {})
    
    if uid:
        print(f"✅ ¡Conexión exitosa! Tu ID de usuario es: {uid}")
    else:
        print("❌ Error de autenticación. El servidor rechazó las credenciales.")
        print("   Verifica:")
        print("   1. Que el nombre de la base de datos sea correcto")
        print("   2. Que el usuario y contraseña sean correctos")
        print("   3. Que el usuario tenga permisos en esa base de datos")
        exit(1)
        
except xmlrpc.client.ProtocolError as e:
    print(f"\n❌ Error de protocolo HTTP:")
    print(f"   Código: {e.errcode}")
    print(f"   Mensaje: {e.errmsg}")
    print(f"   URL: {e.url}")
    print(f"\n💡 Posibles soluciones:")
    print(f"   1. Verifica que la URL sea correcta: {url}")
    print(f"   2. Verifica que el servidor Odoo esté ejecutándose")
    print(f"   3. Verifica que el endpoint XML-RPC esté habilitado en Odoo")
    print(f"   4. Verifica la configuración del firewall")
    exit(1)
    
except xmlrpc.client.Fault as e:
    print(f"\n❌ Error del servidor Odoo:")
    print(f"   Código: {e.faultCode}")
    print(f"   Mensaje: {e.faultString}")
    exit(1)
    
except ConnectionError as e:
    print(f"\n❌ Error de conexión:")
    print(f"   {e}")
    print(f"\n💡 Posibles soluciones:")
    print(f"   1. Verifica que la URL sea correcta: {url}")
    print(f"   2. Verifica que el servidor esté accesible desde tu red")
    print(f"   3. Verifica la configuración del firewall/proxy")
    exit(1)
    
except Exception as e:
    print(f"\n❌ Error inesperado al conectar:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    print(f"\n💡 Información adicional:")
    print(f"   URL intentada: {common_url}")
    print(f"   Base de datos: {db}")
    print(f"   Usuario: {username}")
    exit(1)

# --- 3. EJECUTAR UNA ACCIÓN (LEER DATOS) ---
models_url = f'{url}/xmlrpc/2/object'
print(f"\n🔌 Conectando al endpoint de modelos: {models_url}")

models = xmlrpc.client.ServerProxy(
    models_url,
    allow_none=True,
    use_datetime=True,
    context=context,
    verbose=False
)

print("\n📦 Buscando los primeros 5 productos...")

try:
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[]], {'limit': 5})

    if not product_ids:
        print("ℹ️  No se encontraron productos en la base de datos.")
    else:
        products = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids], {'fields': ['id', 'name', 'default_code']})
        
        print(f"✅ Productos encontrados ({len(products)}):")
        for product in products:
            print(f"  - ID: {product.get('id')}, Código: {product.get('default_code', 'N/A')}, Nombre: {product.get('name')}")

except xmlrpc.client.Fault as e:
    print(f"❌ Error del servidor al consultar productos:")
    print(f"   Código: {e.faultCode}")
    print(f"   Mensaje: {e.faultString}")
except Exception as e:
    print(f"❌ Ocurrió un error al consultar los productos:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")