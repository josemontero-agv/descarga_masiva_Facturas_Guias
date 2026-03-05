#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper de compatibilidad.

Este archivo se mantiene por compatibilidad histórica, pero redirige a:
    archive/11_descargar_pdfs_faltantes_V2.py
"""

from pathlib import Path
import runpy

def main():
    print("ℹ️ Redirigiendo a V2 sin Selenium: archive/11_descargar_pdfs_faltantes_V2.py")
    target = Path(__file__).with_name("11_descargar_pdfs_faltantes_V2.py")
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
