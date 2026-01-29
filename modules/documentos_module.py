import base64
import zipfile
import io
from pathlib import Path

# Constantes de mapeo (pueden venir de config)
from core.config import MAPEO_CARPETAS, ODOO_DB, ODOO_PASSWORD

def buscar_adjuntos_comprobante(uid, models, move_id):
    try:
        return models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.attachment', 'search_read',
            [[('res_model', '=', 'account.move'), ('res_id', '=', move_id)]],
            {'fields': ['id', 'name', 'datas', 'mimetype']}
        )
    except:
        return []

def clasificar_archivo_comprobante(nombre_archivo):
    nombre_lower = nombre_archivo.lower()
    if nombre_lower.endswith('.pdf'): return 'pdf'
    elif nombre_lower.endswith('.xml'):
        if 'cdr' in nombre_lower: return 'cdr'
        return 'xml'
    elif nombre_lower.endswith('.zip'): return 'zip'
    return None

def descargar_comprobante_integral(uid, models, move, base_path_mes):
    move_id = move['id']
    tipo_doc = move.get('l10n_latam_document_type_id', [0, ''])[1]
    # Limpiar tipo_doc para carpeta
    tipo_carpeta = 'Otros'
    for k in MAPEO_CARPETAS.keys():
        if k in tipo_doc:
            tipo_carpeta = MAPEO_CARPETAS[k]
            break
    
    numero_doc = move.get('l10n_latam_document_number', f"DOC_{move_id}")
    nombre_base = numero_doc.replace('/', '-').replace('\\', '-')
    
    adjuntos = buscar_adjuntos_comprobante(uid, models, move_id)
    stats = {'xml': 0, 'pdf': 0, 'cdr': 0}
    
    # Pre-verificación: Si ya existen los 3 archivos básicos, podríamos saltar
    # Pero como no sabemos cuántos XML o CDR hay exactamente, verificamos por cada adjunto
    
    for adj in adjuntos:
        nombre_archivo = adj.get('name', '')
        datas = adj.get('datas')
        if not datas: continue
        
        try:
            tipo = clasificar_archivo_comprobante(nombre_archivo)
            if not tipo: continue
            
            if tipo == 'zip':
                contenido = base64.b64decode(datas)
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for filename in z.namelist():
                        tipo_int = clasificar_archivo_comprobante(filename)
                        if tipo_int:
                            ruta = base_path_mes / tipo_carpeta / tipo_int / f"{nombre_base}.{tipo_int}"
                            if ruta.exists():
                                # stats[tipo_int] += 1
                                continue
                                
                            ruta.parent.mkdir(parents=True, exist_ok=True)
                            with open(ruta, 'wb') as f:
                                f.write(z.read(filename))
                            stats[tipo_int] += 1
            else:
                ruta = base_path_mes / tipo_carpeta / tipo / f"{nombre_base}.{tipo}"
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
