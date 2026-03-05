# 🌐 Módulo de Rescate y Compatibilidad

Este módulo contiene scripts históricos y scripts V2 de rescate para descargas de PDF.
La estrategia recomendada actualmente es **XML-RPC + Sesión HTTP** (sin Selenium).

## 🚀 Scripts Incluidos

### 1. `09_descargar_guias_pdf_v2.py` ✅ RECOMENDADO
Descarga masiva de PDFs de Guías de Remisión sin Selenium.
- **Estrategia**: XML-RPC para listar guías + HTTP autenticado para `/report/pdf/<report_name>/<id>`.
- **Reporte objetivo**: `e-Guía de Remisión AGR` (técnico: `agr_shiping_guide.report_edi_gre`).
- **Ventaja**: Mayor estabilidad en entornos corporativos con restricciones de navegador.

### 2. `11_descargar_pdfs_faltantes_V2.py` ✅ RECOMENDADO
Script de rescate para facturas, boletas y notas sin Selenium.
- **Función**: Lee el archivo `FACTURAS_ANALISIS_sin_pdf.txt`.
- **Acción**: Autentica sesión web por HTTP y descarga `/report/pdf/<report_name>/<move_id>`.
- **Reporte objetivo**: `Factura AGR` (con fallback técnico controlado).
- **Logging**: Genera `RESCATE_PDF_V2_LOG_...txt`.

### 3. Scripts legacy con Selenium (mantener temporalmente)
- `09_descargar_pdfs_guias.py`
- `11_descargar_pdfs_faltantes.py`

Actualmente estos archivos actúan como **wrappers de compatibilidad** y redirigen a V2.
El histórico legacy se documenta en `archive/legacy/README.md`.

## ⚡ Ejecución Simultánea
Los scripts V2 soportan ejecución en **múltiples terminales**:
- Cada proceso usa su propio `PID` para carpetas temporales.
- Sistema de **bloqueo atómico** (.lock) evita que dos terminales descarguen el mismo archivo.
- **Recomendación**: Máximo 4-6 terminales simultáneas para no saturar la memoria RAM.

## 📂 Organización
Los archivos se guardan siguiendo la jerarquía:
`V:\{AÑO}\{Mes_Español}\{Diario}\{Tipo_Documento}\pdf\`
