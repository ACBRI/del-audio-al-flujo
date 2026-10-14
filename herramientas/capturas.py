#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de punta a punta con capturas, para quien mantiene la herramienta.

Dibuja el ejemplo (ejemplos/pedido-a-despacho) con dibujar.py, lo fotografía con
un Chromium sin ventana (escritorio claro, escritorio oscuro, página completa y
teléfono) y, por último, pulsa «Exportar» en el visor para guardar la imagen PNG
tal como la descargaría una persona (herramientas/exportar.mjs). Las imágenes van
a docs/capturas/ y son las que muestra el README.

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

from flujo.cli import main as dibujar  # noqa: E402

EJEMPLO = RAIZ / "ejemplos" / "pedido-a-despacho" / "proceso.json"
CAPTURAS = RAIZ / "docs" / "capturas"

# nombre, ancho, alto, escala, tema oscuro
TOMAS = (
    ("escritorio", 1440, 900, 1, False),
    ("escritorio-oscuro", 1440, 900, 1, True),
    ("escritorio-completo", 1440, 1400, 1, False),
    ("telefono", 390, 844, 2, False),
)


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


def fotografiar(chrome: Path, html: Path, destino: Path, ancho: int, alto: int, escala: int, oscuro: bool) -> None:
    with tempfile.TemporaryDirectory() as perfil:
        orden = [str(chrome), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                 "--user-data-dir=%s" % perfil, "--window-size=%d,%d" % (ancho, alto),
                 "--force-device-scale-factor=%d" % escala, "--virtual-time-budget=6000",
                 "--screenshot=%s" % destino]
        if oscuro:
            orden.append("--blink-settings=preferredColorScheme=0")
        orden.append(html.resolve().as_uri())
        subprocess.run(orden, capture_output=True, timeout=120, check=False)
    if not destino.is_file():
        raise SystemExit("El navegador no produjo %s." % destino)


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
        return capturar(chrome, Path(args.salida))
    with tempfile.TemporaryDirectory(prefix="flujo-") as carpeta:
        return capturar(chrome, Path(carpeta))


def capturar(chrome: Path, carpeta: Path) -> int:
    codigo = dibujar([str(EJEMPLO), "--salida", str(carpeta), "--no-abrir"])
    if codigo != 0:
        return codigo
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    for nombre, ancho, alto, escala, oscuro in TOMAS:
        destino = CAPTURAS / ("%s.png" % nombre)
        fotografiar(chrome, carpeta / "flujo.html", destino, ancho, alto, escala, oscuro)
        print("Captura: %s" % destino.relative_to(RAIZ))
    return exportar(chrome, carpeta)


def exportar(chrome: Path, carpeta: Path) -> int:
    """Pulsa «Exportar» en el visor y guarda la imagen PNG que descarga una persona."""
    from flujo.archify import buscar_node
    node, _ = buscar_node()
    descargas = carpeta / "descargas"
    r = subprocess.run([str(node), str(RAIZ / "herramientas" / "exportar.mjs"), str(chrome),
                        str(carpeta / "flujo.html"), str(descargas)],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    print(r.stdout.strip())
    imagenes = sorted(descargas.glob("*.png"))
    if r.returncode != 0 or not imagenes or not list(descargas.glob("*.svg")):
        print("La exportación desde el visor falló.")
        return 1
    destino = CAPTURAS / "imagen-exportada.png"
    try:  # la exportación sale a 4x; para el README basta la mitad
        from PIL import Image
        with Image.open(imagenes[0]) as imagen:
            imagen.resize((imagen.width // 2, imagen.height // 2), Image.LANCZOS).save(destino, optimize=True)
    except ImportError:
        shutil.copy(imagenes[0], destino)
    print("Captura: %s" % destino.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
