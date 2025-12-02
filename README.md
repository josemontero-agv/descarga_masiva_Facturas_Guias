# 📦 Descarga Masiva de Comprobantes Electrónicos desde Odoo

Sistema para descargar masivamente documentos electrónicos (facturas, boletas, notas de crédito/débito) desde Odoo ERP mediante XML-RPC.

## 📁 Estructura del Proyecto

```
descarga_masiva_Facturas_Guias/
├── scripts/
│   ├── documentos/              # Scripts para documentos electrónicos
│   │   ├── 01_descarga_Facturas.py    # Facturas, boletas, notas
│   │   └── 09_descarga_guias_xml.py   # XMLs de guías (funcional)
│   │
│   ├── guias_web_scraping/      # Web scraping para PDFs de guías (funcional)
│   │   ├── README.md
│   │   └── 09_descargar_pdfs_guias.py  # Script funcional con ejecución simultánea
│   │
│   └── guias_deprecated/        # Scripts antiguos (no usar)
│
├── utils/                       # Utilidades y herramientas
│   ├── analizar_reportes.py     # Analiza reportes disponibles en Odoo
│   └── Prueba_test_odoo_conexion/
│       └── conectar_odoo.py    # Script de prueba de conexión
│
├── tests/                       # Scripts de prueba
│   └── README.md
│
├── docs/                        # Documentación
│   ├── INSTRUCCIONES_RAPIDAS.md
│   └── README_EXTRACCION_GUIAS.md
│
├── config/                      # Archivos de configuración
│
├── Prueba_Octubre/              # Datos de prueba y resultados
│   ├── 01_Facturas/
│   ├── 03_Boletas/
│   ├── 07_Notas_Credito/
│   ├── 08_Notas_Debito/
│   └── 09_Guias_Remision/
│
└── requirements.txt             # Dependencias Python
```

## 🚀 Inicio Rápido

### 1. Instalación

```bash
# Clonar o descargar el proyecto
cd descarga_masiva_Facturas_Guias

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

Crear archivo `.env.desarrollo` o `.env.produccion` en la raíz del proyecto:

```env
ODOO_URL=https://tu-servidor-odoo.com
ODOO_DB=nombre_base_datos
ODOO_USER=tu_usuario
ODOO_PASSWORD=tu_contraseña
```

### 3. Ejecutar

```bash
# Descargar documentos (facturas, boletas, notas)
python scripts/documentos/01_descarga_Facturas.py

# Descargar XMLs de guías de remisión
python scripts/documentos/09_descarga_guias_xml.py

# Web scraping para PDFs de guías (con ejecución simultánea)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
```

## 📋 Documentos Soportados

- ✅ **Facturas** (01) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Boletas** (03) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Notas de Crédito** (07) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Notas de Débito** (08) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Guías de Remisión - XMLs** (09) - `scripts/documentos/09_descarga_guias_xml.py` (XMLs oficiales SUNAT)
- ✅ **Guías de Remisión - PDFs** (09) - `scripts/guias_web_scraping/09_descargar_pdfs_guias.py` (web scraping, ejecución simultánea soportada)

## 📖 Guía de Uso por Tipo de Documento

- **Facturas, Boletas, Notas de Crédito y Débito (01, 03, 07, 08)**  
  1. Editar `scripts/documentos/01_descarga_Facturas.py` y ajustar:
     - **AMBIENTE**: `"desarrollo"` o `"produccion"`.
     - **AÑO / MES**: periodo a descargar.  
  2. Ejecutar:
     ```bash
     python scripts/documentos/01_descarga_Facturas.py
     ```
  3. Los archivos se guardan en `Prueba_Octubre/01_Facturas`, `03_Boletas`, `07_Notas_Credito`, `08_Notas_Debito`
     con subcarpetas `pdf`, `xml`, `cdr`.

- **Guías de Remisión – XML (09)**  
  1. Editar `scripts/documentos/09_descarga_guias_xml.py` y ajustar **AÑO / MES**.  
  2. Ejecutar:
     ```bash
     python scripts/documentos/09_descarga_guias_xml.py
     ```
  3. Los XML se guardan en `Prueba_Octubre/09_Guias_Remision/xml` (y PDF/CDR si aplica).

- **Guías de Remisión – PDFs (Web Scraping, interfaz web)**  
  1. Verificar que Google Chrome esté instalado en Windows.  
  2. Editar `scripts/guias_web_scraping/09_descargar_pdfs_guias.py`:
     - **AMBIENTE**: `"desarrollo"` o `"produccion"`.
     - **AÑO / MES**: periodo de guías a descargar.
  3. Ejecutar:
     ```bash
     python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
     ```
  4. El script:
     - Se conecta a Odoo por XML‑RPC para listar las guías.
     - Abre Chrome, inicia sesión automáticamente.
     - Para cada guía, invoca el reporte **e‑Guía de Remisión AGR** y descarga el PDF.
     - Guarda los PDFs en `Prueba_Octubre/09_Guias_Remision/pdf` con nombre `Txxx-xxxxxx.pdf`.

### ⚡ Ejecución Simultánea (Múltiples Terminales)

El script `09_descargar_pdfs_guias.py` **soporta ejecución simultánea** en múltiples terminales para acelerar la descarga:

#### ✅ Características de Ejecución Simultánea
- **Carpeta temporal única por proceso**: Cada proceso usa `temp_downloads_{PID}` para evitar conflictos
- **Sistema de bloqueo de archivos**: Previene descargas duplicadas automáticamente
- **Verificación atómica**: Cada proceso verifica si el archivo ya existe o está siendo procesado
- **Sin interferencias**: Los procesos trabajan en paralelo sin conflictos

#### 🚀 Ejemplo de Uso Simultáneo
```bash
# Terminal 1
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 2 (simultáneamente - mismo mes)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 3 (simultáneamente - mismo mes)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
```

Cada proceso:
- ✅ Usará su propia carpeta temporal (`temp_downloads_{PID}`)
- ✅ Evitará descargar archivos ya procesados por otros procesos
- ✅ No interferirá con otros procesos en ejecución
- ✅ Mostrará su PID al inicio para identificación

### Ejecutar varios meses en paralelo

- Abrir una terminal por cada mes, cambiar **AÑO / MES** en el script correspondiente (facturas o guías) y ejecutar en paralelo.
- Ejemplo (tres meses de guías XML):
  ```bash
  # Terminal 1
  python scripts/documentos/09_descarga_guias_xml.py   # MES = 10
  # Terminal 2
  python scripts/documentos/09_descarga_guias_xml.py   # MES = 11
  # Terminal 3
  python scripts/documentos/09_descarga_guias_xml.py   # MES = 12
  ```
  
- **Nota**: Para PDFs de guías, puedes ejecutar múltiples instancias del mismo mes simultáneamente gracias al sistema de bloqueo implementado.

## 🛠️ Utilidades

### Analizar Reportes Disponibles en Odoo

```bash
python utils/analizar_reportes.py
```

Este script muestra todos los reportes PDF disponibles en Odoo para diferentes modelos.

### Probar Conexión a Odoo

```bash
python utils/Prueba_test_odoo_conexion/conectar_odoo.py
```

## 📚 Documentación

- [Instrucciones Rápidas](docs/INSTRUCCIONES_RAPIDAS.md) - Guía de configuración y uso general
- [Arquitectura](ARCHITECTURA.md) - Visión técnica de la estructura del proyecto
- [Guías de Remisión (histórico)](docs/README_EXTRACCION_GUIAS.md) - Enfoques antiguos, solo referencia

## ⚠️ Notas Importantes

- **XMLs de Guías**: Usar `scripts/documentos/09_descarga_guias_xml.py` (funcional)
- **PDFs de Guías**: Usar `scripts/guias_web_scraping/09_descargar_pdfs_guias.py` (funcional con ejecución simultánea)
- Los scripts antiguos están en `scripts/guias_deprecated/` y **no se recomiendan usar**
- Asegúrate de tener las credenciales correctas en el archivo `.env.desarrollo` o `.env.produccion`
- Los documentos descargados se guardan en `Prueba_Octubre/` organizados por tipo
- **Ejecución simultánea**: El script de PDFs de guías soporta múltiples terminales simultáneas para acelerar la descarga

## 🔧 Requisitos

- Python 3.8+
- Acceso a Odoo vía XML-RPC
- Credenciales válidas de Odoo

## 📝 Licencia

Este proyecto es de uso interno.

