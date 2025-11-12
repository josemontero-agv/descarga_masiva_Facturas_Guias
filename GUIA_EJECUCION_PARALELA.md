# 🚀 GUÍA: Ejecución Paralela de Descargas por Mes

## 📋 ¿Por qué ejecutar en paralelo?

Ejecutar múltiples terminales en paralelo te permite:
- ✅ **Acelerar el proceso** hasta 3-4x más rápido
- ✅ **Descargar varios meses simultáneamente**
- ✅ **Aprovechar mejor la conexión de red**
- ✅ **Procesar grandes volúmenes más eficientemente**

---

## ⚙️ CONFIGURACIÓN INICIAL (Una sola vez)

### Paso 1: Crear archivos de configuración

Renombrar los archivos de ejemplo:

```bash
# En la carpeta del proyecto:
mv env.desarrollo.example .env.desarrollo
mv env.produccion.example .env.produccion
```

O en Windows PowerShell:

```powershell
Rename-Item -Path "env.desarrollo.example" -NewName ".env.desarrollo"
Rename-Item -Path "env.produccion.example" -NewName ".env.produccion"
```

### Paso 2: Configurar credenciales

Editar `.env.produccion` con tus credenciales reales:

```env
ODOO_URL=https://tu-odoo-real.com
ODOO_DB=tu_base_datos
ODOO_USER=tu_usuario
ODOO_PASSWORD=tu_password
```

---

## 🎯 MÉTODO 1: Ejecución Manual en Múltiples Terminales

### Terminal 1: Descargar Octubre 2025

```bash
# Abrir primera terminal
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"

# Editar 01_descarga_Facturas.py
# Cambiar línea 74: MES = 10

python 01_descarga_Facturas.py
```

### Terminal 2: Descargar Noviembre 2025 (en paralelo)

```bash
# Abrir segunda terminal
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"

# Editar 01_descarga_Facturas.py
# Cambiar línea 74: MES = 11

python 01_descarga_Facturas.py
```

### Terminal 3: Descargar Diciembre 2025 (en paralelo)

```bash
# Abrir tercera terminal
cd "C:\Users\jmontero\Desktop\GitHub Proyectos_AGV\descarga_masiva_Facturas_Guias"

# Editar 01_descarga_Facturas.py
# Cambiar línea 74: MES = 12

python 01_descarga_Facturas.py
```

---

## 🚀 MÉTODO 2: Scripts Automatizados por Mes (RECOMENDADO)

He creado scripts individuales para cada mes que puedes ejecutar directamente:

### Ejecutar cada script en una terminal diferente:

```bash
# Terminal 1
python descargar_octubre.py

# Terminal 2
python descargar_noviembre.py

# Terminal 3
python descargar_diciembre.py
```

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. Límites Recomendados

- ✅ **Óptimo:** 2-3 terminales en paralelo
- ⚠️ **Máximo:** 4 terminales (puede saturar red/CPU)
- ❌ **Evitar:** Más de 4 terminales simultáneas

### 2. Orden de Ejecución

```
Prioridad 1: Mes actual (Noviembre 2025)
Prioridad 2: Mes anterior (Octubre 2025)
Prioridad 3: Meses históricos
```

### 3. Monitoreo del Proceso

Cada terminal mostrará:
```
======================================================================
PROCESANDO 1 GUÍAS
======================================================================

[1/450] 📄 F01-00002587
   📅 Fecha: 2025-11-15
   👤 Cliente: EMPRESA XYZ...
   📂 Tipo: Factura
   📎 3 archivos encontrados
      ✅ PDF: F-F01-00002587_pdf.pdf
      ✅ XML: F-F01-00002587_xml.xml
      ✅ CDR: F-F01-00002587_cdr.xml

[50/450] 📄 ...
```

### 4. Verificación de Espacio en Disco

Antes de ejecutar en paralelo:

```powershell
# Verificar espacio disponible en Y:
Get-PSDrive Y | Select-Object Used,Free

# Estimar: ~150 MB por 1000 documentos
# 3 meses en paralelo ≈ 450 MB
```

---

## 📊 ESTRUCTURA DE SALIDA

```
Y:\Finanzas y Contabilidad\...\Descarga_Masiva_FT_GUIA\
├── 2025\
│   ├── 10_Octubre\          # Terminal 1
│   │   ├── 01_Facturas\
│   │   ├── 03_Boletas\
│   │   └── ...
│   │
│   ├── 11_Noviembre\        # Terminal 2
│   │   ├── 01_Facturas\
│   │   └── ...
│   │
│   └── 12_Diciembre\        # Terminal 3
│       ├── 01_Facturas\
│       └── ...
```

---

## 🛠️ TROUBLESHOOTING

### Problema: "No se puede acceder a Y:"

**Solución:**
```powershell
# Verificar mapeo de unidad
net use

# Re-mapear si es necesario
net use Y: "\\servidor\ruta\compartida" /persistent:yes
```

### Problema: Scripts interfieren entre sí

**Solución:**
- ✅ Cada mes tiene su propia carpeta
- ✅ No hay conflicto de archivos
- ✅ Los procesos son independientes

### Problema: Conexión lenta

**Solución:**
- Reducir terminales paralelas (usar solo 2)
- Verificar velocidad de red
- Descargar primero meses más recientes

---

## ✅ CHECKLIST DE EJECUCIÓN

Antes de ejecutar en paralelo:

- [ ] Archivos `.env.desarrollo` y `.env.produccion` configurados
- [ ] Credenciales de producción validadas
- [ ] Unidad Y: mapeada y accesible
- [ ] Espacio suficiente en disco (mínimo 1 GB)
- [ ] Conexión de red estable
- [ ] Scripts editados con mes correcto

Durante la ejecución:

- [ ] Monitorear progreso en cada terminal
- [ ] Verificar que no hay errores masivos
- [ ] Revisar logs de cada proceso

Después de completar:

- [ ] Verificar cantidad de archivos descargados
- [ ] Comparar contra estadísticas de Odoo
- [ ] Crear backup de los datos descargados

---

## 📈 ESTIMACIONES DE TIEMPO

### Descarga Secuencial (1 terminal):
```
Octubre:   450 facturas → ~15 minutos
Noviembre: 420 facturas → ~14 minutos
Diciembre: 500 facturas → ~17 minutos
TOTAL:                     ~46 minutos
```

### Descarga Paralela (3 terminales):
```
Octubre + Noviembre + Diciembre → ~17 minutos
AHORRO DE TIEMPO:                  ~29 minutos (63%)
```

---

## 💡 TIPS ADICIONALES

1. **Usar VS Code con múltiples terminales integradas**
   - Ctrl + Shift + ` para nueva terminal
   - Cada terminal ejecuta un mes diferente

2. **Nombrar las terminales**
   ```bash
   # Terminal 1: echo "📅 OCTUBRE"
   # Terminal 2: echo "📅 NOVIEMBRE"
   # Terminal 3: echo "📅 DICIEMBRE"
   ```

3. **Crear scripts batch para Windows**
   - Doble clic para ejecutar automáticamente
   - Ver archivos: `descargar_octubre.bat`

---

**¡Listo para ejecutar en paralelo!** 🚀

Si tienes dudas, revisa esta guía o contacta al equipo de soporte.

