# 📂 Estructura del Proyecto - Guía Visual

## 🗂️ Organización Actual (Modular)

```
descarga_masiva_Facturas_Guias/
│
├── 📁 core/                       # 🧠 NÚCLEO DEL SISTEMA
│   ├── config.py                  # Configuración central (Ambientes, Rutas)
│   └── odoo_client.py             # Conexión XML-RPC unificada
│
├── 📁 modules/                    # 🛠️ LÓGICA DE NEGOCIO (Reutilizable)
│   ├── documentos_module.py       # Procesamiento de Facturas/Boletas/Notas
│   └── guias_module.py            # Lógica dual (XML + Scraping) para Guías
│
├── 📁 run/                        # 🚀 LANZADORES (Entry Points)
│   ├── descargar_comprobantes.py  # Ejecución diaria de Facturación
│   ├── descargar_guias.py         # Ejecución diaria de Guías de Remisión
│   └── reparar_faltantes.py       # Sistema de rescate para errores de red
│
├── 📁 tools/                      # 🔧 UTILIDADES Y MANTENIMIENTO
│   ├── migrar_documentos_2025.py  # Migración rápida con Robocopy
│   └── test_odoo.py               # Prueba de conexión a la API
│
├── 📁 docs/                       # 📚 DOCUMENTACIÓN
│   └── html/                      # Portal de documentación Web profesional
│
├── 📁 archive/                    # 📦 ARCHIVO HISTÓRICO
│   └── (Scripts antiguos preservados)
│
├── 📄 .env.example                # Plantilla de configuración
└── 📄 README.md                   # Inicio rápido y visión general
```

## 🎯 ¿Dónde está cada cosa?

### ✅ Scripts de Ejecución Diaria
| Qué necesitas | Dónde está | Comando |
|---------------|------------|---------|
| Descargar Facturas/Boletas | `run/descargar_comprobantes.py` | `python run/descargar_comprobantes.py` |
| Descargar Guías (Integral) | `run/descargar_guias.py` | `python run/descargar_guias.py` |
| Recuperar archivos faltantes | `run/reparar_faltantes.py` | `python run/reparar_faltantes.py` |

### 🛠️ Herramientas Técnicas
| Qué es | Ubicación |
|--------|------------|
| Configuración de Rutas y Meses | `core/config.py` |
| Conexión a Odoo | `core/odoo_client.py` |
| Test de comunicación API | `tools/test_odoo.py` |

### 📚 Documentación Profesional
Contamos con un portal web interactivo con manuales detallados:
👉 **[docs/html/index.html](docs/html/index.html)**

## 🚀 Comandos Rápidos

```bash
# 1. Probar que todo esté bien configurado
python tools/test_odoo.py

# 2. Descargar facturas del periodo configurado
python run/descargar_comprobantes.py

# 3. Descargar guías (XML y PDF automáticamente)
python run/descargar_guias.py
```

## 📝 Notas de Optimización
1.  **Validación Previa**: El sistema ahora detecta si un archivo ya existe localmente antes de intentar descargarlo de Odoo.
2.  **Unificación**: No es necesario correr scripts de XML y PDF por separado para las guías; `descargar_guias.py` lo hace todo.
3.  **Seguridad**: Nunca compartas tus archivos `.env.produccion` o `.env.desarrollo`.
