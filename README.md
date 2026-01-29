# 📦 Descarga Masiva de Comprobantes Electrónicos desde Odoo

Sistema automatizado para la extracción masiva de documentos fiscales (facturas, boletas, notas y guías) desde Odoo ERP, utilizando una estrategia híbrida de **XML-RPC** y **Web Scraping** con Selenium.

## 📖 Documentación Profesional
Para guías detalladas, manuales y arquitectura, consulte nuestro portal de documentación:
👉 **[Portal de Documentación (HTML)](docs/html/index.html)**

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
Proceso integral que primero baja el XML oficial y luego utiliza Selenium para generar el PDF gráfico.
```bash
python run/descargar_guias.py
```

### 4. Reparación de Faltantes (Opcional)
Si hubo fallos en la descarga de PDFs por inestabilidad de red:
```bash
python run/reparar_faltantes.py
```

---

## 📁 Nueva Estructura del Proyecto
- `core/`: Configuración centralizada y cliente Odoo.
- `modules/`: Lógica de negocio reutilizable para cada tipo de documento.
- `run/`: Scripts principales de ejecución diaria.
- `tools/`: Herramientas de migración (Robocopy) y pruebas de conexión.
- `docs/html/`: Portal de documentación técnica y de usuario.
- `archive/`: Scripts antiguos preservados por seguridad.

## 📋 Requisitos
- Python 3.8+
- Google Chrome (actualizado)
- Dependencias: `pip install -r requirements.txt`
- Acceso a la unidad de red `V:` (para ambiente de producción)

---
**Autor:** GitHub Proyectos AGV
**Repo Remoto:** [josemontero-agv/descarga_masiva_Facturas_Guias](https://github.com/josemontero-agv/descarga_masiva_Facturas_Guias.git)
