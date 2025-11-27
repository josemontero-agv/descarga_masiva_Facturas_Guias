# 🚀 INSTRUCCIONES RÁPIDAS - Configuración y Ejecución

## ⚡ INICIO RÁPIDO (5 minutos)

### 1. Crear archivos de configuración

```powershell
# Abrir PowerShell en la carpeta del proyecto
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"

# Renombrar archivos .env
Rename-Item "env.desarrollo.example" ".env.desarrollo"
Rename-Item "env.produccion.example" ".env.produccion"
```

### 2. Configurar credenciales de producción

Editar `.env.produccion` con tus credenciales reales:

```env
ODOO_URL=https://tu-odoo.com
ODOO_DB=tu_base_datos
ODOO_USER=tu_usuario
ODOO_PASSWORD=tu_password
```

### 3. Ejecutar descarga

**Opción A: Un mes a la vez**
```bash
python 01_descarga_Facturas.py
```

**Opción B: Múltiples meses en paralelo** (Recomendado)

Abrir 3 terminales y ejecutar:

```bash
# Terminal 1
python descargar_octubre.py

# Terminal 2  
python descargar_noviembre.py

# Terminal 3
python descargar_diciembre.py
```

---

## 📋 VERIFICACIÓN PRE-EJECUCIÓN

Antes de ejecutar, verifica:

```powershell
# 1. Verificar unidad Y: está mapeada
Test-Path "Y:\"

# 2. Verificar permisos de escritura
Test-Path "Y:\Finanzas y Contabilidad\Créditos y Cobranzas\José Montero" -PathType Container

# 3. Verificar espacio disponible (mínimo 1 GB)
Get-PSDrive Y | Format-Table Name, Used, Free
```

---

## 🎯 CAMBIAR MES A DESCARGAR

En `01_descarga_Facturas.py`, línea 74:

```python
MES = 11    # ← Cambiar: 1=Enero, 2=Febrero, ..., 12=Diciembre
```

---

## 🔧 CAMBIAR AMBIENTE

En `01_descarga_Facturas.py`, línea 31:

```python
AMBIENTE = "produccion"  # ← Cambiar a "desarrollo" para pruebas
```

---

## ❓ PROBLEMAS COMUNES

### Error: "No se encontró .env.produccion"

**Solución:**
```powershell
# Verificar que existe
Test-Path ".env.produccion"

# Si no existe, renombrar
Rename-Item "env.produccion.example" ".env.produccion"
```

### Error: "No se puede acceder a Y:"

**Solución:**
```powershell
# Ver unidades mapeadas
net use

# Mapear Y: si no existe
net use Y: "\\servidor\ruta" /persistent:yes
```

### Error: Credenciales incorrectas

**Solución:**
1. Verificar `.env.produccion` tiene valores correctos
2. No debe haber espacios extra
3. No debe haber comillas en los valores

---

## 📊 RESULTADO ESPERADO

```
Y:\...\Descarga_Masiva_FT_GUIA\
└── 2025\
    └── 11_November\
        ├── 01_Facturas\
        │   ├── pdf\  (450 archivos)
        │   ├── xml\  (378 archivos)
        │   └── cdr\  (378 archivos)
        ├── 03_Boletas\
        │   └── [archivos]
        └── 07_Notas_Credito\
            └── [archivos]
```

---

## ⏱️ TIEMPO ESTIMADO

- **1 mes (~400 documentos):** 12-15 minutos
- **3 meses en paralelo:** 15-20 minutos total
- **6 meses en paralelo (2 terminales cada 3 meses):** 30-35 minutos total

---

## 📞 SOPORTE

Si encuentras problemas:
1. Revisa `GUIA_EJECUCION_PARALELA.md` para más detalles
2. Verifica logs en consola
3. Contacta al equipo técnico

---

**¡Listo! Tu sistema está configurado para descargas en producción.** ✅

