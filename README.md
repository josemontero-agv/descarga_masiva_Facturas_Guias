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
│   ├── guias_web_scraping/      # Web scraping para PDFs de guías (en desarrollo)
│   │   ├── README.md
│   │   └── descargar_pdfs_guias.py
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

# Web scraping para PDFs de guías (en desarrollo)
python scripts/guias_web_scraping/descargar_pdfs_guias.py
```

## 📋 Documentos Soportados

- ✅ **Facturas** (01) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Boletas** (03) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Notas de Crédito** (07) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Notas de Débito** (08) - `scripts/documentos/01_descarga_Facturas.py`
- ✅ **Guías de Remisión - XMLs** (09) - `scripts/documentos/09_descarga_guias_xml.py` (funcional)
- 🚧 **Guías de Remisión - PDFs** (09) - `scripts/guias_web_scraping/` (en desarrollo)

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

- [Instrucciones Rápidas](docs/INSTRUCCIONES_RAPIDAS.md) - Guía de configuración y uso
- [Extracción de Guías](docs/README_EXTRACCION_GUIAS.md) - Documentación sobre guías (deprecated)

## ⚠️ Notas Importantes

- **XMLs de Guías**: Usar `scripts/documentos/09_descarga_guias_xml.py` (funcional)
- **PDFs de Guías**: En desarrollo con web scraping en `scripts/guias_web_scraping/`
- Los scripts antiguos están en `scripts/guias_deprecated/` y **no se recomiendan usar**
- Asegúrate de tener las credenciales correctas en el archivo `.env.desarrollo` o `.env.produccion`
- Los documentos descargados se guardan en `Prueba_Octubre/` organizados por tipo

## 🔧 Requisitos

- Python 3.8+
- Acceso a Odoo vía XML-RPC
- Credenciales válidas de Odoo

## 📝 Licencia

Este proyecto es de uso interno.

