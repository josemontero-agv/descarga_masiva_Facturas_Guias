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

### 3. Ejecutar descarga de COMPROBANTES (01, 03, 07, 08)

Desde la raíz del proyecto:

```bash
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"
python scripts/documentos/01_descarga_Facturas.py
```

Los resultados se guardan en `Prueba_Octubre/01_Facturas`, `03_Boletas`, `07_Notas_Credito`, `08_Notas_Debito`
en las subcarpetas `pdf`, `xml` y `cdr`.

---

### 4. Ejecutar descarga de GUÍAS – XML (09)

```bash
python scripts/documentos/09_descarga_guias_xml.py
```

Los XML (y CDR si aplica) se guardan en `Prueba_Octubre/09_Guias_Remision/xml`.

---

### 5. Ejecutar descarga de GUÍAS – PDFs (Web Scraping)

Requisitos:
- Google Chrome instalado
- `.env.desarrollo` o `.env.produccion` configurado

Ejecutar:

```bash
python scripts/guias_web_scraping/descargar_pdfs_guias.py
```

Este script abre Chrome, inicia sesión en Odoo y descarga los PDFs de la **e‑Guía de Remisión AGR**
para el mes configurado en el script, guardándolos en `Prueba_Octubre/09_Guias_Remision_V2/pdf`.

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

- En `scripts/documentos/01_descarga_Facturas.py`:

```python
AÑO = 2025
MES = 11    # ← Cambiar: 1=Enero, 2=Febrero, ..., 12=Diciembre
```

- En `scripts/documentos/09_descarga_guias_xml.py` y `scripts/guias_web_scraping/descargar_pdfs_guias.py`:

```python
AÑO = 2025
MES = 10
```

---

## 🔧 CAMBIAR AMBIENTE

En cada script principal (`01_descarga_Facturas.py`, `09_descarga_guias_xml.py`,
`scripts/guias_web_scraping/descargar_pdfs_guias.py`) existe una constante:

```python
AMBIENTE = "produccion"  # o "desarrollo"
```

- **desarrollo**: usa `.env.desarrollo` (servidor de pruebas)
- **produccion**: usa `.env.produccion` (servidor real)

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

