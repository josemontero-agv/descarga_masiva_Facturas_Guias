#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper de compatibilidad.

Este archivo se mantiene por compatibilidad con ejecuciones antiguas, pero
redirige al flujo V2 sin Selenium:
    archive/09_descargar_guias_pdf_v2.py
"""

from pathlib import Path
import runpy

def main():
    print("ℹ️ Redirigiendo a V2 sin Selenium: archive/09_descargar_guias_pdf_v2.py")
    target = Path(__file__).with_name("09_descargar_guias_pdf_v2.py")
    runpy.run_path(str(target), run_name="__main__")

if __name__ == "__main__":
    main()
