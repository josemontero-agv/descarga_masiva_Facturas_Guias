# 🌐 Web Scraping para PDFs de Guías de Remisión

## 📋 Descripción

Este módulo implementa web scraping para descargar los PDFs de guías de remisión directamente desde la interfaz web de Odoo.

## 🎯 Objetivo

Descargar los PDFs originales generados por Odoo para las guías de remisión, evitando las limitaciones de XML-RPC.

## 📝 Notas

- **XMLs**: Se descargan usando `scripts/documentos/09_descarga_guias_xml.py` (funcional)
- **PDFs**: Se descargarán usando web scraping (este módulo - en desarrollo)

## 🚧 Estado

**En desarrollo** - Pendiente de implementación

## 🔄 Estrategia Propuesta

1. Autenticación en la interfaz web de Odoo
2. Navegación a las guías de remisión
3. Descarga de PDFs usando los reportes identificados:
   - `agr_shiping_guide.report_edi_gre` (ID: 871) - Guías normales
   - `agr_shiping_guide.report_edi_gre_ti` (ID: 1024) - Traslados internos
   - `agr_shiping_guide.report_edi_gre_esp` (ID: 1175) - Guías especiales

## 📚 Referencias

- Reportes identificados: Ver `utils/analizar_reportes.py`
- XMLs funcionales: `scripts/documentos/09_descarga_guias_xml.py`

