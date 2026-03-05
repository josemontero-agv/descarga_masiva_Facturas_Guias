# 📦 Descarga Masiva de Comprobantes Electrónicos desde Odoo

Sistema automatizado para la extracción masiva de documentos fiscales (facturas, boletas, notas y guías) desde Odoo ERP, utilizando una estrategia de **XML-RPC + Sesión HTTP** (sin dependencia de Selenium para reportes PDF críticos).

## 📖 Documentación Profesional
Para guías detalladas, manuales y arquitectura, consulte nuestro portal de documentación:
👉 **[Portal de Documentación (HTML)](docs/index.html)**

---

## 🚀 Flujo de Ejecución Ordenado

Para un correcto funcionamiento, siga este orden de ejecución:

### 1. Configuración de Ambiente
Copie el archivo de ejemplo y configure sus credenciales de Odoo:
```bash
cp .env.example .env.produccion
# Edite .env.produccion con su URL, DB, Usuario y Password
```

### 2. Descarga de Comprobantes (Facturas/Boletas/Notas)
Descarga rápida vía API de todos los archivos XML, PDF y CDR adjuntos.
```bash
python run/descargar_comprobantes.py
```

### 3. Descarga de Guías de Remisión (XML + PDF)
Proceso integral con enfoque robusto para entornos corporativos restringidos:
- Opción recomendada (sin Selenium): `run/descargar_guias.py`
- Opción alternativa: `archive/09_descargar_guias_pdf_v2.py`
```bash
python run/descargar_guias.py
```

### 4. Reparación de Faltantes (Opcional)
Si hubo fallos en la descarga de PDFs de comprobantes:
- Opción recomendada (sin Selenium): `run/reparar_faltantes.py`
- Opción alternativa: `archive/11_descargar_pdfs_faltantes_V2.py`
```bash
python run/reparar_faltantes.py
```

---

## 🧠 ¿Por qué XML-RPC + HTTP en lugar de Selenium?

En ambientes con políticas de seguridad corporativa (SSO, EDR, hardening de navegador), Selenium puede fallar con errores como `invalid session id` o cierre inesperado de Chrome.  
El enfoque nuevo evita esa capa visual:

- **XML-RPC**: lista documentos, obtiene metadatos y estructura de carpetas.
- **HTTP autenticado**: descarga reportes PDF con `/report/pdf/<report_name>/<id>`.
- **Beneficio**: menos fricción con restricciones de TI, mayor estabilidad y mejor trazabilidad.

---

## 📁 Nueva Estructura del Proyecto
- `core/`: Configuración centralizada y cliente Odoo.
- `modules/`: Lógica de negocio reutilizable para cada tipo de documento.
- `run/`: Scripts principales de ejecución diaria.
- `tools/`: Herramientas de migración (Robocopy) y pruebas de conexión.
- `docs/`: Portal de documentación técnica y de usuario.
- `archive/`: Scripts antiguos preservados por seguridad.

## 📋 Requisitos
- Python 3.8+
- Google Chrome (solo si se usan scripts legacy con Selenium)
- Dependencias: `pip install -r requirements.txt`
- Acceso a la unidad de red `V:` (para ambiente de producción)

---
**Autor:** GitHub Proyectos AGV
**Repo Remoto:** [josemontero-agv/descarga_masiva_Facturas_Guias](https://github.com/josemontero-agv/descarga_masiva_Facturas_Guias.git)
