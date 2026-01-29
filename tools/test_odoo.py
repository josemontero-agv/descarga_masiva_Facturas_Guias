import os
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path para poder importar core
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Configurar el ambiente antes de importar el core (opcional)
# os.environ["APP_AMBIENTE"] = "produccion" 

from core.config import AMBIENTE, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD, PROJECT_ROOT as CFG_ROOT
from core.odoo_client import conectar_odoo

def test_conexion():
    print(f"\n{'='*70}")
    print("🧪 TEST DE CONEXIÓN A ODOO")
    print(f"{'='*70}")
    print(f"📁 Raíz del proyecto detectada: {CFG_ROOT}")
    print(f"🔧 Ambiente: {AMBIENTE.upper()}")
    print(f"📡 URL: {ODOO_URL}")
    print(f"🗄️  Base de Datos: {ODOO_DB}")
    print(f"👤 Usuario: {ODOO_USER}")
    print(f"{'-'*70}")

    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        print("❌ Error: Faltan credenciales en el archivo .env correspondente.")
        return

    uid, models = conectar_odoo()

    if uid:
        print(f"✅ ¡CONEXIÓN EXITOSA!")
        print(f"🆔 Tu ID de usuario (UID) es: {uid}")
        
        # Prueba simple: leer 3 productos
        print("\n📦 Probando lectura de productos...")
        try:
            product_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search', [[]], {'limit': 3})
            if product_ids:
                products = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'read', [product_ids], {'fields': ['name', 'default_code']})
                for p in products:
                    print(f"  • [{p.get('default_code', 'N/A')}] {p.get('name')}")
                print("\n✅ La lectura de datos funciona correctamente.")
            else:
                print("⚠️  Conexión OK, pero no se encontraron productos.")
        except Exception as e:
            print(f"❌ Error al leer productos: {e}")
    else:
        print("❌ FALLÓ LA AUTENTICACIÓN")
        print("💡 Revisa que el archivo .env tenga las credenciales correctas.")

if __name__ == "__main__":
    test_conexion()
