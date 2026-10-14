#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de punta a punta con capturas, para quien mantiene la herramienta.

Dibuja el ejemplo (ejemplos/pedido-a-despacho) con dibujar.py y lo abre en un
Chromium sin ventana (herramientas/navegador.mjs): lo fotografía en escritorio
claro, escritorio oscuro, página completa y teléfono, y pulsa «Exportar» para
guardar la imagen PNG tal como la descargaría una persona. Las imágenes van a
docs/capturas/ y son las que muestra el README.

    python herramientas/capturas.py [--chrome RUTA] [--salida CARPETA]

Busca el navegador en este orden: --chrome, la variable CHROME, el Chromium sin
ventana que instala Playwright y, por último, chromium o google-chrome en el PATH.
No hace falta para usar la herramienta.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from flujo.archify import buscar_node  # noqa: E402
from flujo.cli import main as dibujar  # noqa: E402

EJEMPLO = RAIZ / "ejemplos" / "pedido-a-despacho" / "proceso.json"
CAPTURAS = RAIZ / "docs" / "capturas"
TOMAS = ("escritorio", "escritorio-oscuro", "escritorio-completo", "telefono")


def buscar_chrome(propio: str | None) -> Path | None:
    candidatos = [propio, os.environ.get("CHROME")]
    cache = Path.home() / ".cache" / "ms-playwright"
    candidatos += sorted((str(p) for p in cache.glob("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell")),
                         reverse=True)
    candidatos += [shutil.which(n) for n in ("chromium", "chromium-browser", "google-chrome", "chrome")]
    for c in candidatos:
        if c and Path(c).is_file():
            return Path(c)
    return None


def capturar(chrome: Path, carpeta: Path) -> int:
    codigo = dibujar([str(EJEMPLO), "--salida", str(carpeta), "--no-abrir"])
    if codigo != 0:
        return codigo
    node, motivo = buscar_node()
    if not node:
        print(motivo)
        return 2
    fotos = carpeta / "fotos"
    r = subprocess.run([str(node), str(RAIZ / "herramientas" / "navegador.mjs"), str(chrome),
                        str(carpeta / "flujo.html"), str(fotos)],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    print(r.stdout.strip())
    exportada = sorted((fotos / "descargas").glob("*.png"))
    if r.returncode != 0 or not exportada or not list((fotos / "descargas").glob("*.svg")):
        print("Las capturas o la exportación desde el visor fallaron.")
        print(r.stderr.strip()[-2000:])
        return 1
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    for nombre in TOMAS:
        shutil.copy(fotos / ("%s.png" % nombre), CAPTURAS / ("%s.png" % nombre))
        print("Captura: docs/capturas/%s.png" % nombre)
    destino = CAPTURAS / "imagen-exportada.png"
    try:  # la exportación sale a 4x; para el README basta la mitad
        from PIL import Image
        with Image.open(exportada[0]) as imagen:
            imagen.resize((imagen.width // 2, imagen.height // 2), Image.LANCZOS).save(destino, optimize=True)
    except ImportError:
        shutil.copy(exportada[0], destino)
    print("Captura: docs/capturas/%s" % destino.name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chrome", help="ruta a un Chromium o Chrome sin ventana")
    parser.add_argument("--salida", help="carpeta para el dibujo (por defecto, una temporal)")
    args = parser.parse_args()
    chrome = buscar_chrome(args.chrome)
    if not chrome:
        print("No encontré un Chromium sin ventana. Indique uno con --chrome.")
        return 2
    if args.salida:
        return capturar(chrome, Path(args.salida).resolve())
    with tempfile.TemporaryDirectory(prefix="flujo-") as carpeta:
        return capturar(chrome, Path(carpeta))


if __name__ == "__main__":
    sys.exit(main())
