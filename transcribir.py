#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transcribe un audio en este computador (opcional). Ver SKILL.md, «Opción B».

    Windows:        py transcribir.py nota.m4a --salida mis-flujos\\carpeta\\relato.md
    macOS y Linux:  python3 transcribir.py nota.m4a --salida mis-flujos/carpeta/relato.md

Necesita faster-whisper (`pip install faster-whisper`). La primera vez descarga el
modelo «small», unos 500 MB; después funciona sin internet.
"""
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("Del audio al flujo necesita Python 3.9 o más nuevo; este es %d.%d.\n"
                     "Descárguelo de https://www.python.org/downloads/\n" % sys.version_info[:2])
    sys.exit(2)

from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flujo.transcripcion import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
