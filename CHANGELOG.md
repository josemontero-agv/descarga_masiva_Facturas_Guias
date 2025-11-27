# 📝 Changelog

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

