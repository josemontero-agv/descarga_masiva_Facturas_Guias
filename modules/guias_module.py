import os
import sys
import time
import base64
import zipfile
import io
from pathlib import Path
from datetime import datetime

# Importar configuración y cliente de Odoo
from core.config import ODOO_DB, ODOO_PASSWORD, ODOO_URL, get_base_path, MAPEO_CARPETAS, PROJECT_ROOT

# Importaciones para ejecución simultánea segura
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

# ============================================================================
# SISTEMA DE BLOQUEO ATÓMICO (Para ejecución en paralelo)
# ============================================================================

def obtener_bloqueo_archivo(ruta_archivo, timeout=2):
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if sys.platform == 'win32':
                lock_file = open(lock_file_path, 'xb')
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                lock_file = open(lock_file_path, 'x')
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except (FileExistsError, IOError, OSError):
            time.sleep(0.1)
            continue
    return None

def liberar_bloqueo_archivo(lock_file, ruta_archivo):
    if lock_file:
        try:
            lock_file.close()
        except:
            pass
    
    lock_file_path = Path(str(ruta_archivo) + '.lock')
    try:
        if lock_file_path.exists():
            os.remove(lock_file_path)
    except:
        pass

def verificar_y_reservar_descarga(ruta_final):
    if ruta_final.exists():
        return False, None
    
    lock_file = obtener_bloqueo_archivo(ruta_final)
    if lock_file is None:
        return False, None
    
    if ruta_final.exists():
        liberar_bloqueo_archivo(lock_file, ruta_final)
        return False, None
        
    return True, lock_file

# ============================================================================
# LÓGICA DE XML-RPC (XML / CDR)
# ============================================================================

def buscar_adjuntos_guia(uid, models, picking_id):
    try:
        return models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[('res_model', '=', 'stock.picking'), ('res_id', '=', picking_id)]],
            {'fields': ['id', 'name', 'datas', 'mimetype', 'description']}
        )
    except:
        return []

def clasificar_archivo_guia(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if nombre_lower.endswith('.pdf'): return 'pdf'
    elif nombre_lower.endswith('.zip'): return 'zip'
    elif nombre_lower.endswith('.xml'):
        if 'cdr' in nombre_lower or 'constancia' in nombre_lower: return 'cdr'
        return 'xml'
    elif 'cdr' in nombre_lower: return 'cdr'
    return None

def descargar_xml_cdr_guia(uid, models, guia, base_path_guia):
    guia_id = guia['id']
    numero_doc = guia.get('l10n_latam_document_number', f"GUIA_{guia_id}")
    nombre_base = numero_doc.replace('/', '-').replace('\\', '-')
    
    adjuntos = buscar_adjuntos_guia(uid, models, guia_id)
    stats = {'xml': 0, 'cdr': 0}
    
    for adj in adjuntos:
        nombre_archivo = adj.get('name', '')
        datas = adj.get('datas')
        if not datas: continue
        
        try:
            tipo = clasificar_archivo_guia(nombre_archivo)
            if not tipo or tipo == 'pdf': continue
            
            if tipo == 'zip':
                contenido = base64.b64decode(datas)
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for filename in z.namelist():
                        tipo_int = clasificar_archivo_guia(filename)
                        if tipo_int and tipo_int in ['xml', 'cdr']:
                            ext = ".xml"
                            if tipo_int == 'cdr':
                                ext = "_cdr.xml"
                                
                            ruta = base_path_guia / tipo_int / f"{nombre_base}{ext}"
                            if ruta.exists():
                                stats[tipo_int] += 1
                                continue
                                
                            ruta.parent.mkdir(parents=True, exist_ok=True)
                            with open(ruta, 'wb') as f:
                                f.write(z.read(filename))
                            stats[tipo_int] += 1
            else:
                ext = ".xml"
                if tipo == 'cdr':
                    ext = "_cdr.xml"
                    
                ruta = base_path_guia / tipo / f"{nombre_base}{ext}"
                if ruta.exists():
                    stats[tipo] += 1
                    continue
                    
                contenido = base64.b64decode(datas)
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with open(ruta, 'wb') as f:
                    f.write(contenido)
                stats[tipo] += 1
        except:
            pass
    return stats
