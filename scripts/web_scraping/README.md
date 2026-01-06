# 🌐 Web Scraping para PDFs de Guías de Remisión

## 📋 Descripción

Este módulo implementa web scraping para descargar los PDFs de guías de remisión directamente desde la interfaz web de Odoo usando Selenium.

## 🎯 Objetivo

Descargar los PDFs originales generados por Odoo para las guías de remisión, evitando las limitaciones de XML-RPC.

## ✅ Estado

**✅ FUNCIONAL** - Implementado y listo para producción

## 🚀 Características Principales

### 1. Descarga Optimizada
- **XML-RPC**: Obtiene lista de guías rápidamente
- **Selenium**: Navega directamente a URLs de reportes PDF
- **Velocidad**: ~3 segundos por guía (1000 guías en ~50 minutos)

### 2. ⚡ Ejecución Simultánea
- ✅ **Soporta múltiples terminales simultáneas**
- ✅ **Sistema de bloqueo de archivos** para evitar descargas duplicadas
- ✅ **Carpeta temporal única por proceso** (`temp_downloads_{PID}`)
- ✅ **Verificación atómica** previene race conditions
- ✅ **Manejo robusto de errores** con liberación automática de bloqueos

### 3. Estrategia Implementada
1. **XML-RPC**: Obtiene lista de guías del período configurado
2. **Selenium + Chrome**: Inicia sesión automáticamente en Odoo
3. **Descarga directa**: Navega a `/report/pdf/{report_name}/{doc_id}` para cada guía
4. **Organización**: Guarda PDFs con nombre `Txxx-xxxxxx.pdf` en carpeta estructurada

## 📝 Uso

### Configuración
1. Editar `09_descargar_pdfs_guias.py`:
   - **AMBIENTE**: `"desarrollo"` o `"produccion"`
   - **AÑO / MES**: Período a descargar

### Ejecución Simple
```bash
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
```

### Ejecución Simultánea (Múltiples Terminales)
```bash
# Terminal 1
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 2 (simultáneamente)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 3 (simultáneamente)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
```

Cada proceso trabajará en paralelo sin interferencias, acelerando significativamente la descarga.

## 🔧 Requisitos Técnicos

- **Google Chrome** instalado en Windows
- **Selenium** y **webdriver-manager** (instalados vía `requirements.txt`)
- **Credenciales Odoo** en `.env.desarrollo` o `.env.produccion`

## 📊 Reportes Utilizados

- `agr_shiping_guide.report_edi_gre` - e-Guía de Remisión AGR (principal)

## 📚 Referencias

- **XMLs funcionales**: `scripts/documentos/09_descarga_guias_xml.py`
- **Reportes identificados**: Ver `utils/analizar_reportes.py`
- **Documentación principal**: Ver `README.md` en la raíz del proyecto

