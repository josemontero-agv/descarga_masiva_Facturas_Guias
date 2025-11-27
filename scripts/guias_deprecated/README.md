# ⚠️ Scripts de Guías - DEPRECATED

## ⚠️ ADVERTENCIA

Estos scripts **NO se recomiendan usar**. Están aquí solo como referencia histórica.

## 📋 Scripts Incluidos

- `09_descaga_guias.py` - Intento de descarga directa desde Odoo
- `extraccion_reporte_guia_pdf.py` - Generación local de PDFs
- `generar_pdfs_desde_xml.py` - Generación desde XMLs existentes
- `generar_todos_los_pdfs.py` - Versión automatizada

## 🚫 ¿Por qué están deprecated?

1. **Limitaciones de XML-RPC**: Odoo 16 tiene restricciones para generar PDFs vía XML-RPC
2. **Complejidad**: Los scripts requieren mucha configuración y no son confiables
3. **Nueva estrategia**: Se está implementando **web scraping** para descargar PDFs directamente desde la interfaz web

## 🔄 Nueva Solución

Se está trabajando en una solución con **web scraping** que:
- Accede a la interfaz web de Odoo
- Descarga los PDFs originales generados por Odoo
- Es más confiable y no depende de XML-RPC

## 📝 Nota

Si necesitas estos scripts por alguna razón específica, revisa la documentación en `docs/README_EXTRACCION_GUIAS.md`, pero se recomienda esperar la nueva implementación con web scraping.

