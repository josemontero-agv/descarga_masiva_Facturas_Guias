# 📝 Changelog

## [2026-01-28] - Reorganización Modular y Documentación Profesional

### ✅ Mejoras de Arquitectura
- 🏗️ **Estructura Modular**: Reorganización completa del proyecto en carpetas funcionales:
  - `core/`: Lógica central (configuración, conexión Odoo).
  - `modules/`: Lógica de negocio reutilizable por tipo de documento.
  - `run/`: Puntos de entrada simplificados para ejecución diaria.
  - `tools/`: Herramientas de mantenimiento y migración.
  - `archive/`: Preservación de scripts antiguos.
- ⚙️ **Configuración Centralizada**: Implementación de `core/config.py` para gestionar ambientes (`produccion`/`desarrollo`), rutas de red y constantes globales en un solo lugar.
- 🔐 **Seguridad**: Creación de `.env.example` para guiar la configuración sin exponer credenciales reales en repositorios.

### 🚀 Optimización de Procesos
- ⚡ **Descargas Inteligentes**: Implementación de verificación de existencia de archivos en `descargar_comprobantes.py` y `descargar_guias.py`. El sistema ahora salta automáticamente documentos ya descargados, ahorrando tiempo y peticiones a la API.
- 📦 **Unificación de Guías**: Integración de descarga de XML (vía API) y PDF (vía Selenium) en un único script orquestado: `run/descargar_guias.py`.
- 🛠️ **Herramienta de Reparación**: Creación de `run/reparar_faltantes.py` para rescate masivo de documentos con fallos de descarga.

### 📖 Documentación
- 🌐 **Portal HTML**: Creación de un sistema de documentación profesional en `docs/html/` con estilo visual Odoo (Poppins, Bootstrap Icons).
  - Manual de Usuario actualizado.
  - Manual del Desarrollador con la nueva arquitectura.
  - Bitácora de proyecto integrada.

## [2025-01-XX] - Ejecución Simultánea para Descarga de PDFs de Guías

### ✅ Mejoras Implementadas

#### 1. Soporte para Ejecución Simultánea
- ✅ **Carpeta temporal única por proceso**: Cada proceso usa `temp_downloads_{PID}` para evitar conflictos
- ✅ **Sistema de bloqueo de archivos**: Implementado con `msvcrt.locking()` (Windows) y `fcntl.flock()` (Linux/Mac)
- ✅ **Verificación atómica**: Función `verificar_y_reservar_descarga()` previene race conditions
- ✅ **Manejo robusto de errores**: Liberación automática de bloqueos en bloques `finally`

#### 2. Funcionalidades Técnicas
- ✅ Bloqueo exclusivo por archivo para evitar descargas duplicadas
- ✅ Detección automática de archivos ya procesados por otros procesos
- ✅ Mensajes informativos con PID del proceso y carpeta temporal utilizada
- ✅ Manejo de errores `FileExistsError` y `shutil.Error` al mover archivos

#### 3. Beneficios
- 🚀 **Velocidad**: Múltiples procesos pueden trabajar en paralelo sin interferencias
- 🔒 **Seguridad**: Sin descargas duplicadas ni conflictos de archivos
- ⚡ **Eficiencia**: Cada proceso salta automáticamente archivos ya descargados
- 🛡️ **Robustez**: Manejo completo de errores y liberación garantizada de bloqueos

### 📋 Archivos Modificados
- `scripts/guias_web_scraping/09_descargar_pdfs_guias.py` - Implementación completa de ejecución simultánea

### 🔄 Uso
```bash
# Ejecutar en múltiples terminales simultáneamente
# Terminal 1
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 2 (simultáneamente)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py

# Terminal 3 (simultáneamente)
python scripts/guias_web_scraping/09_descargar_pdfs_guias.py
```

## [2025-11-27] - Reorganización y Preparación para Web Scraping

### ✅ Cambios Realizados

#### 1. Reorganización de Scripts
- ✅ Movido `09_descaga_guias.py` → `scripts/documentos/09_descarga_guias_xml.py`
  - Script funcional para descargar XMLs de guías
  - Rutas actualizadas para buscar `.env` en la raíz del proyecto
  - BASE_PATH actualizado para usar rutas relativas

#### 2. Nueva Estructura para Web Scraping
- ✅ Creada carpeta `scripts/guias_web_scraping/`
  - `descargar_pdfs_guias.py` - Template para implementación futura
  - `README.md` - Documentación del módulo

#### 3. Carpeta de Tests
- ✅ Creada carpeta `tests/`
  - `README.md` - Guía para crear tests

#### 4. Documentación Actualizada
- ✅ `README.md` - Actualizado con nueva estructura
- ✅ `ARCHITECTURA.md` - Refleja cambios en organización
- ✅ Documentación de scripts actualizada

### 📋 Estado Actual

#### Scripts Funcionales
- ✅ `scripts/documentos/01_descarga_Facturas.py` - Facturas, boletas, notas
- ✅ `scripts/documentos/09_descarga_guias_xml.py` - XMLs de guías

#### En Desarrollo
- 🚧 `scripts/guias_web_scraping/descargar_pdfs_guias.py` - PDFs de guías

#### Deprecated
- ⚠️ `scripts/guias_deprecated/` - Scripts antiguos (no usar)

### 🔄 Próximos Pasos

1. Implementar web scraping para PDFs de guías
2. Crear tests en `tests/`
3. Mejorar manejo de errores
4. Agregar logging estructurado

