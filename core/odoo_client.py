import xmlrpc.client
from .config import ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD

def conectar_odoo():
    """
    Establece conexión con Odoo vía XML-RPC.
    Retorna (uid, models) si tiene éxito.
    """
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            return None, None
            
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        return uid, models
    except Exception as e:
        print(f"❌ Error conectando a Odoo: {e}")
        return None, None
