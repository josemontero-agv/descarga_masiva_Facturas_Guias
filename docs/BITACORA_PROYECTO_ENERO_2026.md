# 📓 BITÁCORA DE PROYECTO - ENERO 2026

### 🗓️ 06 de Enero, 2026: Reestructuración y Sistema de Rescate

#### 🛠️ Cambios Realizados:
1.  **Infraestructura**:
    -   Se actualizó la ruta de producción en todos los scripts de `Y:\` a `V:\2025`.
    -   Se implementó el mapeo automático de meses a español en todos los generadores de rutas.

2.  **Desarrollo de Software**:
    -   **Optimización del Script 11**: Se transformó en una herramienta de rescate avanzada que lee logs de errores y navega automáticamente en Odoo para generar PDFs faltantes.
    -   **Logging**: Se añadió la función `guardar_log_revision` para generar reportes de éxito/fallo con marca de tiempo.
    -   **Script de Migración**: Se reescribió `10_migrar_documentos.py` para facilitar la transferencia de Guías de Remisión entre unidades, eliminando la jerarquía de diarios y traduciendo carpetas al vuelo.

3.  **Rendimiento**:
    -   Se validó la ejecución simultánea en 4 terminales, confirmando la estabilidad del sistema de bloqueos de archivos.

#### 📌 Notas Técnicas:
-   El reporte estándar de Odoo utilizado para el rescate es `account.report_invoice`.
-   Se aumentó el timeout de descarga a 15 segundos para compensar la generación dinámica de PDFs en el servidor.

---
**Responsable:** J. Montero
