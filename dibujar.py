#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dibuja el flujo de un proceso a partir de su modelo intermedio.

    Windows:        py dibujar.py ruta\\a\\proceso.json
    macOS y Linux:  python3 dibujar.py ruta/a/proceso.json

    Revisar el computador:  py dibujar.py --comprobar   (o python3 ...)

Escribe flujo.html junto al proceso.json y lo abre en el navegador. Ver SKILL.md.
"""
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("Del audio al flujo necesita Python 3.9 o más nuevo; este es %d.%d.\n"
                     "Descárguelo de https://www.python.org/downloads/\n" % sys.version_info[:2])
    sys.exit(2)

from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flujo.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
