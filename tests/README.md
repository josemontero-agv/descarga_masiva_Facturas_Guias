# 🧪 Tests y Pruebas

## 📋 Descripción

Esta carpeta contiene scripts de prueba para validar la funcionalidad de los scripts principales.

## 📁 Estructura

```
tests/
├── README.md                    # Este archivo
├── test_conexion_odoo.py       # Pruebas de conexión
├── test_descarga_facturas.py   # Pruebas de descarga de facturas
├── test_descarga_guias_xml.py  # Pruebas de descarga de XMLs de guías
└── test_web_scraping_guias.py  # Pruebas de web scraping (futuro)
```

## 🚀 Uso

Ejecutar pruebas individuales:

```bash
# Probar conexión
python tests/test_conexion_odoo.py

# Probar descarga de facturas
python tests/test_descarga_facturas.py

# Probar descarga de XMLs de guías
python tests/test_descarga_guias_xml.py
```

## 📝 Notas

- Los tests deben usar el archivo `.env.desarrollo` para no afectar producción
- Cada test debe ser independiente y poder ejecutarse por separado
- Los tests deben limpiar archivos temporales después de ejecutarse

