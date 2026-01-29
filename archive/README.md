# 🌐 Módulo de Web Scraping (Selenium)

Este módulo contiene las soluciones de automatización visual para superar las limitaciones del API XML-RPC de Odoo.

## 🚀 Scripts Incluidos

### 1. `09_descargar_pdfs_guias.py`
Descarga masiva de PDFs de Guías de Remisión.
- **Estrategia**: Navega al reporte técnico `agr_shiping_guide.report_edi_gre`.
- **Rendimiento**: ~3 segundos por documento.

### 2. `11_descargar_pdfs_faltantes.py` ⭐ (NUEVO)
Script de "rescate" para facturas, boletas y notas.
- **Función**: Lee el archivo `FACTURAS_ANALISIS_sin_pdf.txt`.
- **Acción**: Abre el navegador, inicia sesión y fuerza la descarga del reporte `account.report_invoice`.
- **Logging**: Genera un reporte detallado de éxito/error llamado `RESCATE_PDF_LOG_...txt`.

## ⚡ Ejecución Simultánea
Ambos scripts soportan ser ejecutados en **múltiples terminales al mismo tiempo**:
- Cada proceso usa su propio `PID` para carpetas temporales.
- Sistema de **bloqueo atómico** (.lock) evita que dos terminales descarguen el mismo archivo.
- **Recomendación**: Máximo 4-6 terminales simultáneas para no saturar la memoria RAM.

## 📂 Organización
Los archivos se guardan siguiendo la jerarquía:
`V:\{AÑO}\{Mes_Español}\{Diario}\{Tipo_Documento}\pdf\`
