# 🏗️ Arquitectura del Proyecto

## 📂 Estructura de Directorios

```
descarga_masiva_Facturas_Guias/
│
├── 📁 scripts/                    # Scripts principales del proyecto
│   ├── documentos/                # Scripts para documentos electrónicos
│   │   ├── 01_descarga_Facturas.py    # Script principal para facturas, boletas, notas
│   │   └── 09_descarga_guias_xml.py   # Descarga XMLs de guías (funcional)
│   │
│   ├── guias_web_scraping/        # Web scraping para PDFs de guías (en desarrollo)
│   │   ├── README.md
│   │   └── descargar_pdfs_guias.py
│   │
│   └── guias_deprecated/          # Scripts antiguos de guías (NO USAR)
│       ├── README.md              # Explicación de por qué están deprecated
│       ├── extraccion_reporte_guia_pdf.py
│       ├── generar_pdfs_desde_xml.py
│       └── generar_todos_los_pdfs.py
│
├── 📁 utils/                      # Utilidades y herramientas auxiliares
│   ├── analizar_reportes.py      # Analiza reportes PDF disponibles en Odoo
│   └── Prueba_test_odoo_conexion/
│       └── conectar_odoo.py       # Script de prueba de conexión a Odoo
│
├── 📁 tests/                      # Scripts de prueba
│   └── README.md
│
├── 📁 docs/                       # Documentación del proyecto
│   ├── INSTRUCCIONES_RAPIDAS.md
│   └── README_EXTRACCION_GUIAS.md
│
├── 📁 config/                     # Archivos de configuración (futuro)
│
├── 📁 Prueba_Octubre/            # Datos de prueba y resultados
│   ├── 01_Facturas/              # Facturas descargadas
│   ├── 03_Boletas/               # Boletas descargadas
│   ├── 07_Notas_Credito/         # Notas de crédito
│   ├── 08_Notas_Debito/          # Notas de débito
│   ├── 09_Guias_Remision/        # Guías (datos históricos)
│   └── RESUMEN_EJECUTIVO.md      # Resumen de pruebas
│
├── 📄 README.md                   # Documentación principal
├── 📄 ARCHITECTURA.md             # Este archivo
├── 📄 requirements.txt            # Dependencias Python
└── 📄 .gitignore                  # Archivos ignorados por Git
```

## 🔄 Flujo de Trabajo

### Para Documentos (Facturas, Boletas, Notas)

1. **Configuración**: Crear `.env.desarrollo` o `.env.produccion` en la raíz
2. **Ejecución**: `python scripts/documentos/01_descarga_Facturas.py`
3. **Resultado**: Documentos descargados en `Prueba_Octubre/`

### Para Guías (Futuro - Web Scraping)

1. **Estrategia**: Web scraping desde la interfaz web de Odoo
2. **Estado**: En desarrollo
3. **Scripts antiguos**: En `scripts/guias_deprecated/` (no usar)

## 🔧 Configuración de Rutas

Todos los scripts buscan el archivo `.env.desarrollo` o `.env.produccion` en la **raíz del proyecto**, independientemente de dónde estén ubicados.

### Ejemplo de búsqueda:

```python
# Desde scripts/documentos/01_descarga_Facturas.py
project_root = Path(__file__).parent.parent.parent  # Sube 3 niveles
env_path = project_root / '.env.desarrollo'

# Desde utils/analizar_reportes.py
project_root = Path(__file__).parent.parent  # Sube 2 niveles
env_path = project_root / '.env.desarrollo'
```

## 📦 Tipos de Documentos

| Código | Tipo | Estado | Script |
|--------|------|--------|--------|
| 01 | Facturas | ✅ Funcional | `scripts/documentos/01_descarga_Facturas.py` |
| 03 | Boletas | ✅ Funcional | `scripts/documentos/01_descarga_Facturas.py` |
| 07 | Notas de Crédito | ✅ Funcional | `scripts/documentos/01_descarga_Facturas.py` |
| 08 | Notas de Débito | ✅ Funcional | `scripts/documentos/01_descarga_Facturas.py` |
| 09 | Guías de Remisión - XMLs | ✅ Funcional | `scripts/documentos/09_descarga_guias_xml.py` |
| 09 | Guías de Remisión - PDFs | ✅ Funcional | `scripts/guias_web_scraping/descargar_pdfs_guias.py` |

## 🎯 Principios de Diseño

1. **Separación de responsabilidades**: Scripts de documentos vs guías
2. **Reutilización**: Utilidades compartidas en `utils/`
3. **Documentación**: Toda la documentación en `docs/`
4. **Configuración centralizada**: Archivos `.env` en la raíz
5. **Deprecación clara**: Scripts antiguos marcados como deprecated

## 🔮 Futuro

- [x] Implementar estructura para web scraping de guías
- [x] Implementar descarga masiva de PDFs de guías vía web scraping (Completado)
- [ ] Crear módulo común para conexión a Odoo
- [ ] Agregar tests unitarios en `tests/`
- [ ] Mejorar manejo de errores
- [ ] Agregar logging estructurado

