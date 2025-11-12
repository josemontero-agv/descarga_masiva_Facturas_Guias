# 📋 Extracción y Generación Local de PDFs de Guías de Remisión

## 🎯 Objetivo

Este script **extrae datos de Odoo via XML-RPC** y **genera los PDFs localmente en Python**, evitando las limitaciones de los métodos de generación remota de Odoo 16.

## 🔧 Archivos Creados

### 1. `extraccion_reporte_guia_pdf.py` (NUEVO)
**Script principal** que:
- ✅ Se conecta a Odoo via XML-RPC
- ✅ Analiza el reporte QWeb `agr_shiping_guide.report_edi_gre`
- ✅ Extrae TODOS los datos necesarios de cada guía
- ✅ **Genera el PDF localmente** usando `reportlab` (biblioteca Python)
- ✅ Guarda directamente en la carpeta especificada

**Ventajas:**
- ⚡ Más rápido (no depende de Odoo para generar PDFs)
- 🎨 Control total sobre el diseño del PDF
- 🔧 Personalizable según tus necesidades
- 🚀 No tiene limitaciones de XML-RPC

### 2. `09_descaga_guias.py` (ACTUALIZADO)
Script original mejorado con:
- ✅ Métodos correctos de Odoo 16 (`_render`)
- ✅ Estrategia dual: generar nuevo o descargar existente
- ✅ Logging detallado para diagnóstico
- ✅ Nueva ruta: `09_Guias_Remision_V2`

## 🚀 Uso Rápido

### Opción A: Generación Local (RECOMENDADO)

```bash
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"
python extraccion_reporte_guia_pdf.py
```

**Características:**
- Genera PDFs localmente (más rápido)
- 3 modos: análisis (1 guía), prueba (10 guías), completo (todas)
- Control total sobre el formato

### Opción B: Descarga desde Odoo

```bash
python 09_descaga_guias.py
```

**Características:**
- Intenta generar PDF remotamente usando Odoo
- Si falla, descarga PDF existente
- Descarga XMLs automáticamente

## 📊 Proceso del Script de Extracción

### PASO 1: Análisis del Reporte QWeb
```
🔍 ANALIZANDO REPORTE QWEB
- Busca: agr_shiping_guide.report_edi_gre
- Identifica campos necesarios del modelo stock.picking
- Muestra estructura del reporte
```

### PASO 2: Extracción de Datos
Para cada guía, extrae:
- ✅ Datos del picking (documento, fechas, estado)
- ✅ Información del emisor (compañía)
- ✅ Información del destinatario (partner)
- ✅ Líneas de productos (stock.move)
- ✅ Detalles de productos
- ✅ Ubicaciones origen/destino

### PASO 3: Generación de PDF
Usando `reportlab`:
- 📄 Crea PDF con formato profesional
- 🎨 Replica estructura de guía de remisión SUNAT
- 📦 Incluye todos los productos
- 💾 Guarda en carpeta especificada

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

