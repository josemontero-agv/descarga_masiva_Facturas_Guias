# 📦 Descarga Masiva de Comprobantes Electrónicos desde Odoo

Sistema automatizado para la extracción masiva de documentos fiscales (facturas, boletas, notas y guías) desde Odoo ERP, utilizando una estrategia híbrida de XML-RPC y Web Scraping con Selenium.

## 🚀 Características Recientes
- **Nueva Unidad de Red**: Migración completa de almacenamiento a la unidad `V:\2025`.
- **Localización**: Organización de carpetas con nombres de meses en español (ej. `01_Enero`).
- **Sistema de Rescate**: Nuevo script especializado para recuperar PDFs que no están adjuntos en Odoo mediante navegación automatizada.
- **Ejecución Paralela**: Soporte para múltiples terminales simultáneas con sistema de bloqueo de archivos.

## 📁 Estructura del Proyecto
```
descarga_masiva_Facturas_Guias/
├── scripts/
│   ├── xml-rpc/                 # Scripts basados en API (Rápidos)
│   │   ├── 01_descarga_Facturas.py    # Facturas, boletas y notas
│   │   ├── 09_descarga_guias_xml.py   # XMLs oficiales SUNAT
│   │   └── 10_migrar_documentos.py    # Transferencia y traducción de meses
│   │
│   ├── web_scraping/            # Scripts basados en Selenium (Rescate)
│   │   ├── 09_descargar_pdfs_guias.py # PDFs de guías via navegador
│   │   └── 11_descargar_pdfs_faltantes.py # Rescate de facturas sin PDF
│   │
│   └── utils/                   # Herramientas de diagnóstico
│
├── Prueba_Octubre/              # Almacenamiento local (Modo Desarrollo)
└── docs/                        # Documentación técnica y bitácoras
```

## 🛠️ Guía de Uso Rápido

### 1. Descarga Inicial (XML-RPC)
Ejecuta el script principal para descargar todo lo que ya tiene adjuntos en Odoo:
```bash
python scripts/xml-rpc/01_descarga_Facturas.py
```
*Esto generará un log en `Resumen de errores/FACTURAS_ANALISIS_sin_pdf.txt` con lo que falte.*

### 2. Rescate de Faltantes (Web Scraping)
Para aquellos documentos que no tenían el PDF adjunto, usa el script de rescate:
```bash
python scripts/web_scraping/11_descargar_pdfs_faltantes.py
```
*Este script leerá el log del paso anterior y "forzará" la generación del PDF via navegador.*

### 3. Migración y Consolidación
Para mover guías antiguas o consolidar meses entre unidades (`Y:` a `V:`):
```bash
python scripts/xml-rpc/10_migrar_documentos.py
```

## 📋 Requisitos
- Python 3.8+
- Google Chrome instalado
- Unidad `V:` mapeada (para producción)
