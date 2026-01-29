# 🏗️ Arquitectura del Proyecto

## 📂 Estructura de Directorios

El proyecto sigue un diseño modular y orientado a dominios para garantizar la escalabilidad y mantenibilidad.

```
descarga_masiva_Facturas_Guias/
│
├── 📁 core/                       # Lógica central compartida
│   ├── config.py                  # Configuración central (env, rutas, constantes)
│   └── odoo_client.py             # Cliente unificado XML-RPC para Odoo
│
├── 📁 modules/                    # Lógica de negocio (reutilizable)
│   ├── documentos_module.py       # Procesamiento de Facturas, Boletas, Notas
│   └── guias_module.py            # Lógica dual XML-RPC + Selenium para Guías
│
├── 📁 run/                        # Scripts de ejecución (Entry Points)
│   ├── descargar_comprobantes.py  # Descarga diaria de facturas/boletas
│   ├── descargar_guias.py         # Descarga integral de guías (XML + PDF)
│   └── reparar_faltantes.py       # Script de rescate para descargas incompletas
│
├── 📁 tools/                      # Herramientas de mantenimiento
│   ├── migrar_documentos_2025.py  # Consolidación de archivos con Robocopy
│   └── test_odoo.py               # Prueba rápida de conexión
│
├── 📁 docs/                       # Documentación técnica
│   └── html/                      # Portal web de documentación profesional
│       ├── index.html             # Índice central
│       ├── manual_usuario.html    # Guía para el usuario final
│       └── manual_desarrollador.html # Detalles técnicos de la arquitectura
│
├── 📁 archive/                    # Preservación de scripts obsoletos/antiguos
│
├── 📁 Prueba_Octubre/             # Almacenamiento local para desarrollo
│
├── 📄 .env.example                # Plantilla de configuración segura
├── 📄 requirements.txt            # Dependencias de Python
└── 📄 README.md                   # Guía de inicio rápido
```

## 🔄 Flujo de Trabajo

### 1. Configuración de Ambiente
El sistema utiliza archivos `.env.produccion` o `.env.desarrollo` ubicados en la raíz. La carga se centraliza en `core/config.py`, lo que permite que cualquier script acceda a las rutas y credenciales correctas sin código duplicado.

### 2. Ejecución Diaria
Los scripts en la carpeta `run/` son los únicos que el usuario debe ejecutar directamente. Estos importan los módulos necesarios y orquestan el flujo de descarga.

### 3. Optimización de Descargas
Todos los scripts implementan una **capa de verificación de existencia**. Antes de realizar una petición a la API o abrir el navegador, el sistema verifica si el archivo ya existe en el destino final (`Path.exists()`). Si el archivo está presente, se salta automáticamente, reduciendo drásticamente el tiempo de ejecución en re-procesamientos.

## 🔧 Componentes Clave

### core/config.py
*   Gestiona el mapeo de meses a español.
*   Define las rutas de red dinámicamente según el año y mes.
*   Controla el cambio de ambiente mediante la variable `APP_AMBIENTE`.

### modules/guias_module.py
*   Implementa una estrategia híbrida: descarga el XML oficial vía XML-RPC y utiliza Selenium para generar la representación gráfica (PDF) desde la interfaz de Odoo.

## 📦 Tipos de Documentos Soporte

| Documento | Tecnología Principal | Módulo | Script de Ejecución |
|-----------|----------------------|--------|----------------------|
| Facturas  | XML-RPC              | `documentos_module` | `run/descargar_comprobantes.py` |
| Boletas   | XML-RPC              | `documentos_module` | `run/descargar_comprobantes.py` |
| Notas     | XML-RPC              | `documentos_module` | `run/descargar_comprobantes.py` |
| Guías     | XML-RPC + Selenium   | `guias_module`      | `run/descargar_guias.py` |

## 🎯 Principios de Diseño

1.  **DRY (Don't Repeat Yourself)**: La lógica de conexión y configuración reside en un solo lugar (`core/`).
2.  **SoC (Separation of Concerns)**: Se separa la ejecución (`run/`) de la lógica de negocio (`modules/`).
3.  **Seguridad**: Las credenciales sensibles nunca se suben al código; se gestionan mediante variables de entorno protegidas por `.gitignore`.
4.  **Optimización**: El sistema prioriza la velocidad mediante verificaciones locales antes de cualquier operación de red.
