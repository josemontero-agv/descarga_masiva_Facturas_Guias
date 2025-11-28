# 📋 Guías de Remisión – Documentación Histórica

## ℹ️ Contexto

Este archivo documenta los **enfoques antiguos** que se probaron para generar PDFs
de Guías de Remisión (generación local con `reportlab`, uso intensivo de XML‑RPC, etc.).

Actualmente, la solución recomendada es:

- **XMLs de Guías**: `scripts/documentos/09_descarga_guias_xml.py`
- **PDFs de Guías (web scraping)**: `scripts/guias_web_scraping/descargar_pdfs_guias.py`

Esta documentación se conserva solo como **referencia técnica**.

## Enfoques Probados (NO recomendados hoy)

- `extraccion_reporte_guia_pdf.py`  
  - Analizaba el reporte QWeb `agr_shiping_guide.report_edi_gre`
  - Extraía todos los datos de `stock.picking`
  - Generaba el PDF localmente con `reportlab`

- `09_descaga_guias.py`  
  - Intentaba usar métodos internos de Odoo (`_render`, `_render_qweb_pdf`)
  - Mezclaba descarga de PDFs y XMLs vía XML‑RPC

Limitaciones detectadas:

- Cambios de versión de Odoo rompían los métodos internos (`_render`, etc.).
- Mantenimiento complejo y difícil de explicar a usuarios no técnicos.
- Problemas de rendimiento para volúmenes altos (> 10,000 guías).

## Solución Actual (Resumen)

Para conocer la solución vigente de extracción y descarga de guías,
revisa:

- `README.md` → sección **“Guía de Uso por Tipo de Documento”**
- `ARCHITECTURA.md` → sección **“Tipos de Documentos”**
- `scripts/guias_web_scraping/README.md` → detalles del web scraping

Si necesitas estudiar el diseño anterior (por ejemplo, para auditoría o ideas futuras),
puedes leer las versiones anteriores de este archivo en el historial de Git.

## 🎨 Estructura del PDF Generado

```
┌─────────────────────────────────────────┐
│   GUÍA DE REMISIÓN ELECTRÓNICA          │
├─────────────────────────────────────────┤
│ EMISOR                                  │
│ RUC: xxx | Razón Social | Dirección     │
├─────────────────────────────────────────┤
│ DOCUMENTO                               │
│ Número: Txxx-xxxxx | Fecha | Tipo Op.   │
├─────────────────────────────────────────┤
│ DESTINATARIO                            │
│ RUC/DNI: xxx | Nombre | Dirección       │
├─────────────────────────────────────────┤
│ DETALLE DE PRODUCTOS                    │
│ Código | Descripción | Cant. | Unidad   │
│ ...                                     │
├─────────────────────────────────────────┤
│ OBSERVACIONES                           │
└─────────────────────────────────────────┘
```

## 📦 Requisitos

### Biblioteca Principal
```bash
pip install reportlab
```

El script **instala automáticamente** `reportlab` si no está disponible.

### Otras dependencias (ya incluidas)
- `xmlrpc.client` (estándar Python)
- `python-dotenv`
- `pathlib`

## 🔧 Configuración

### Archivo `.env`
```env
ODOO_URL=https://tu-odoo.com
ODOO_DB=tu_base_datos
ODOO_USER=tu_usuario
ODOO_PASSWORD=tu_password
```

### Variables en el script
```python
# Período
AÑO = 2025
MES = 10

# Ruta de salida
OUTPUT_PATH = r"C:\...\09_Guias_Remision_V2\pdf"

# Filtros
PICKING_TYPE_ID = 2
TYPE_OPERATION_SUNAT = "01"
```

## 📈 Ejemplo de Salida

```
######################################################################
# EXTRACCIÓN Y GENERACIÓN LOCAL DE PDFs DE GUÍAS
# Análisis del reporte: agr_shiping_guide.report_edi_gre
# 2025-11-11 14:30:00
######################################################################

🔄 CONECTANDO A ODOO
✅ Conectado (UID: 2)

🔍 ANALIZANDO REPORTE QWEB
✅ Reporte encontrado: agr_shiping_guide.report_edi_gre
📋 Campos relevantes: 45

🔍 OBTENIENDO GUÍAS DEL PERÍODO
✅ Encontradas: 832 guías

📊 Opciones:
  1. Procesar solo la primera guía (análisis)
  2. Procesar las primeras 10 guías (prueba)
  3. Procesar TODAS las 832 guías

Selecciona: 1

📦 PROCESANDO GUÍA 1/1
ID: 12345 | WH/OUT/00123 | Doc: T007-00001234

📦 EXTRAYENDO DATOS COMPLETOS
✅ Datos del picking extraídos
✅ Datos del partner extraídos
✅ Datos de la compañía extraídos
✅ 5 líneas extraídas

📄 GENERANDO PDF LOCALMENTE
✅ PDF generado: T007-00001234.pdf

📊 RESUMEN FINAL
✅ Exitosas: 1
❌ Errores: 0

📂 PDFs guardados en: C:\...\09_Guias_Remision_V2\pdf
```

## 🎯 Diferencias Clave

| Aspecto | Script Original | Script Nuevo |
|---------|----------------|--------------|
| **Generación PDF** | Remota (Odoo) | Local (Python) |
| **Velocidad** | Lenta (depende de Odoo) | Rápida (local) |
| **Personalización** | Limitada | Total |
| **Dependencias Odoo** | Alta | Baja (solo datos) |
| **Limitaciones XML-RPC** | ❌ Sí | ✅ No |
| **Control diseño** | No | Sí |

## 💡 Casos de Uso

### 1. Análisis Inicial
```bash
python extraccion_reporte_guia_pdf.py
# Seleccionar opción 1 (1 guía)
```
Revisa el PDF generado para verificar formato.

### 2. Prueba
```bash
python extraccion_reporte_guia_pdf.py
# Seleccionar opción 2 (10 guías)
```
Valida que todo funciona correctamente.

### 3. Producción
```bash
python extraccion_reporte_guia_pdf.py
# Seleccionar opción 3 (todas las guías)
```
Procesa las 832 guías completas.

## 🔍 Troubleshooting

### Error: "reportlab no está instalada"
```bash
pip install reportlab
```

### Error: "No se encontró el reporte"
- Verifica que el reporte existe en Odoo
- Nombre correcto: `agr_shiping_guide.report_edi_gre`

### PDFs vacíos o incompletos
- Revisa que los datos se extraigan correctamente
- Verifica permisos de usuario en Odoo
- Comprueba que las guías tengan productos asociados

### Error de conexión a Odoo
- Verifica credenciales en `.env`
- Comprueba conectividad a la URL de Odoo
- Confirma que el usuario tiene permisos

## 🎨 Personalización del PDF

Para modificar el diseño del PDF, edita la función `generar_pdf_guia_local()`:

```python
# Cambiar colores
colors.HexColor('#1a1a1a')  # Color de título

# Cambiar tamaños de fuente
fontSize=16  # Tamaño de título

# Agregar logo
# Descomentar sección de logo en el código

# Modificar estructura
# Ajustar las tablas y secciones según necesites
```

## 📚 Recursos

- [Documentación Reportlab](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Odoo XML-RPC](https://www.odoo.com/documentation/16.0/developer/misc/api/odoo.html)
- [Guías de Remisión SUNAT](https://www.sunat.gob.pe/)

## ✅ Checklist

- [x] Script de extracción creado
- [x] Análisis de reporte QWeb implementado
- [x] Extracción completa de datos
- [x] Generación local de PDFs con reportlab
- [x] Manejo de errores robusto
- [x] Logging detallado
- [x] Modos de procesamiento (1, 10, todas)
- [x] Documentación completa

---

**Autor:** Script generado para AGV  
**Fecha:** Noviembre 2025  
**Versión:** 1.0

