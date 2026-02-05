# Guía de Diseño y Paleta de Colores - Documentación Finanzas AGV

Este documento resume los estándares visuales utilizados en la documentación del proyecto Finanzas AGV, diseñado para servir como referencia en la creación de nuevos proyectos con una identidad visual coherente.

## 1. Concepto de Diseño
El diseño está orientado a un entorno **Corporativo y Profesional**, priorizando la legibilidad técnica y una presentación impecable para niveles ejecutivos.

- **Layout:** Estructura de dos columnas con barra lateral (TOC) fija a la izquierda (280px) y área de contenido central (máximo 1100px).
- **Tipografía:**
  - **Cuerpo y Títulos:** `Poppins` (Sans-serif) - Proporciona modernidad y claridad.
  - **Código:** `Fira Code` o `Courier New` (Monospace) - Para bloques técnicos.
- **Componentes:** Uso intensivo de bordes redondeados (12px a 24px) y sombras suaves (`box-shadow`) para crear jerarquía y profundidad.

## 2. Paleta de Colores

| Elemento | Variable CSS | Hexadecimal | Uso sugerido |
| :--- | :--- | :--- | :--- |
| **Púrpura Primario** | `--agv-purple` | `#714B67` | Color de marca, títulos (H1, H2), botones y elementos activos. |
| **Púrpura Oscuro** | `--agv-purple-dark` | `#5A3C52` | Estados hover, degradados de fondo y énfasis fuerte. |
| **Púrpura Claro** | `--agv-purple-light` | `#875A7B` | Bordes laterales, acentos y fondos de badges. |
| **Texto Primario** | `--text-primary` | `#1A1A1A` | Títulos principales y texto de alto contraste. |
| **Texto Secundario** | `--text-secondary` | `#555555` | Cuerpo de texto general y descripciones. |
| **Fondo de Contraste** | `--bg-light` | `#F8F9FA` | Fondo de la barra lateral, tablas y secciones diferenciadas. |
| **Bordes y Divisiones** | `--border-color` | `#E2E8F0` | Líneas divisorias, bordes de cards y tablas. |

## 3. Estilos de Código y Bloques de Información

- **Bloques de Código (Pre/Code):**
  - Fondo: `#1E293B` (Slate Dark)
  - Texto: `#F8FAFC`
  - Estilo: Bordes redondeados 12px, padding 20px, y sombra sutil.
- **Código Inline:**
  - Fondo: `#F1F5F9`
  - Color: `#E11D48` (Carmesí para resaltar sobre el texto).
- **Notas y Avisos (Alerts):**
  - Fondo: `#F0F9FF` (Azul suave)
  - Borde destacado: 6px sólido `#0EA5E9` (Izquierda)
  - Radio de borde: `0 12px 12px 0`

## 4. Elementos de Interfaz (UI) Destacados

- **Secciones Hero:** Uso de degradados lineales: `linear-gradient(135deg, #714B67 0%, #5A3C52 100%)` con texto en blanco.
- **Cards Informativas:**
  - Padding: 30px.
  - Transición: `all 0.3s ease`.
  - Efecto Hover: Elevación con `translateY(-8px)` y sombra profunda.
- **Tablas:**
  - Estilo: `border-collapse: separate` con `border-spacing: 0`.
  - Encabezados: Fondo `#F8FAF6` con texto púrpura en negrita y mayúsculas.
  - Filas: Efecto hover con fondo `#F1F5F9`.

---
*Referencia generada a partir de los estilos definidos en `docs/style.css` del proyecto Finanzas AGV.*
