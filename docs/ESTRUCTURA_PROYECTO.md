# 📂 Estructura del Proyecto - Guía Visual

## 🗂️ Organización Actual

```
descarga_masiva_Facturas_Guias/
│
├── 📄 README.md                    # Documentación principal
├── 📄 ARCHITECTURA.md              # Arquitectura del proyecto
├── 📄 .gitignore                   # Archivos ignorados por Git
├── 📄 requirements.txt             # Dependencias Python
│
├── 📁 scripts/                     # ⭐ SCRIPTS PRINCIPALES
│   │
│   ├── 📁 documentos/              # ✅ Scripts activos para documentos
│   │   └── 01_descarga_Facturas.py    # Script principal (facturas, boletas, notas)
│   │
│   └── 📁 guias_deprecated/        # ⚠️ Scripts antiguos (NO USAR)
│       ├── README.md                   # Explicación de deprecación
│       ├── 09_descaga_guias.py
│       ├── extraccion_reporte_guia_pdf.py
│       ├── generar_pdfs_desde_xml.py
│       └── generar_todos_los_pdfs.py
│
├── 📁 utils/                       # 🛠️ HERRAMIENTAS Y UTILIDADES
│   ├── analizar_reportes.py           # Analiza reportes disponibles en Odoo
│   └── Prueba_test_odoo_conexion/
│       └── conectar_odoo.py           # Script de prueba de conexión
│
├── 📁 docs/                        # 📚 DOCUMENTACIÓN
│   ├── INSTRUCCIONES_RAPIDAS.md
│   ├── README_EXTRACCION_GUIAS.md
│   └── ESTRUCTURA_PROYECTO.md         # Este archivo
│
├── 📁 config/                      # ⚙️ CONFIGURACIÓN (futuro)
│
└── 📁 Prueba_Octubre/              # 📦 DATOS Y RESULTADOS
    ├── 01_Facturas/
    ├── 03_Boletas/
    ├── 07_Notas_Credito/
    ├── 08_Notas_Debito/
    ├── 09_Guias_Remision/
    └── RESUMEN_EJECUTIVO.md
```

## 🎯 ¿Dónde está cada cosa?

### ✅ Scripts Activos (Usar estos)

| Qué necesitas | Dónde está |
|---------------|------------|
| Descargar facturas, boletas, notas | `scripts/documentos/01_descarga_Facturas.py` |
| Analizar reportes de Odoo | `utils/analizar_reportes.py` |
| Probar conexión a Odoo | `utils/Prueba_test_odoo_conexion/conectar_odoo.py` |

### ⚠️ Scripts Deprecated (NO usar)

| Qué es | Dónde está | Por qué no usar |
|--------|------------|-----------------|
| Scripts de guías | `scripts/guias_deprecated/` | Se está implementando web scraping |

### 📚 Documentación

| Documento | Ubicación | Para qué sirve |
|-----------|-----------|----------------|
| Guía principal | `README.md` | Inicio rápido y visión general |
| Arquitectura | `ARCHITECTURA.md` | Diseño y estructura del proyecto |
| Instrucciones | `docs/INSTRUCCIONES_RAPIDAS.md` | Configuración paso a paso |
| Guías (deprecated) | `docs/README_EXTRACCION_GUIAS.md` | Referencia histórica |

## 🚀 Comandos Rápidos

```bash
# Desde la raíz del proyecto

# Descargar documentos
python scripts/documentos/01_descarga_Facturas.py

# Analizar reportes
python utils/analizar_reportes.py

# Probar conexión
python utils/Prueba_test_odoo_conexion/conectar_odoo.py
```

## 📝 Notas Importantes

1. **Archivo de configuración**: El archivo `.env.desarrollo` debe estar en la **raíz del proyecto**
2. **Scripts de guías**: No usar los scripts en `scripts/guias_deprecated/`
3. **Datos**: Los documentos descargados se guardan en `Prueba_Octubre/`
4. **Utilidades**: Scripts auxiliares están en `utils/`

## 🔄 Cambios Recientes

- ✅ Scripts organizados por tipo (documentos vs guías)
- ✅ Scripts de guías movidos a `guias_deprecated/`
- ✅ Documentación centralizada en `docs/`
- ✅ Utilidades separadas en `utils/`
- ✅ Rutas actualizadas para buscar `.env` en la raíz

