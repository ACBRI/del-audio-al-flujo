# -*- coding: utf-8 -*-
"""La orden `dibujar`: del modelo intermedio a un HTML que se abre en el navegador.

    python dibujar.py mis-flujos/2026-10-14-pedido/proceso.json

Pasos: lee y revisa el modelo, compara las citas con el relato si lo encuentra
junto al modelo (relato.md), convierte a la especificación de Archify, dibuja,
pone la piel de la marca y el idioma, y abre el resultado.

Códigos de salida, para quien lo llame desde un programa o un agente:
    0  dibujado
    1  el modelo tiene errores: corríjalos y vuelva a correr
    2  falta algo en el computador (Python o Node)
    3  Archify no pudo dibujar el modelo
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import webbrowser
from pathlib import Path

from . import __version__, archify, convertidor, marca, modelo

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "ejemplos" / "pedido-a-despacho" / "proceso.json"


def preparar_consola() -> None:
    """Salida en UTF-8 aunque Windows entregue otra codificación a una tubería."""
    for flujo_salida in (sys.stdout, sys.stderr):
        try:
            if (flujo_salida.encoding or "").lower().replace("-", "") != "utf8":
                flujo_salida.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def _lista(titulo: str, elementos: list) -> None:
    if elementos:
        print(titulo)
        for e in elementos:
            print("  - %s" % e)


def comprobar() -> int:
    """Revisa que el computador tenga lo necesario y dibuja el ejemplo en una carpeta temporal."""
    listo = True
    v = sys.version_info
    print("Del audio al flujo %s, en %s %s." % (__version__, platform.system() or "un sistema desconocido",
                                               platform.release()))
    if v >= (3, 9):
        print("[ok] Python %d.%d.%d (se necesita 3.9 o más nuevo)." % (v[0], v[1], v[2]))
    else:
        print("[falta] Python %d.%d: se necesita 3.9 o más nuevo." % (v[0], v[1]))
        listo = False
    node, version = archify.buscar_node()
    if node:
        print("[ok] Node %s en %s (se necesita %d o más nuevo)." % (".".join(map(str, version)), node,
                                                                 archify.NODE_MINIMO))
    else:
        print("[falta] %s" % version)
        print("        %s" % archify.como_instalar_node())
        listo = False
    if archify.CLI.is_file():
        print("[ok] Archify %s en %s." % (archify.version_archify(), archify.ARCHIFY))
    else:
        print("[falta] No encuentro vendor/archify. Descargue el repositorio completo otra vez.")
        listo = False
    if listo and EJEMPLO.is_file():
        m, _ = modelo.leer(EJEMPLO)
        parte = convertidor.convertir(m)["partes"][0]
        with tempfile.TemporaryDirectory() as carpeta:
            resultado = archify.dibujar(node, parte["spec"], Path(carpeta) / "prueba.archify.json",
                                        Path(carpeta) / "prueba.html")
        if resultado["ok"]:
            print("[ok] Prueba de dibujo con el ejemplo: Archify la aceptó en calidad %s." % resultado["calidad"])
        else:
            print("[falla] La prueba de dibujo no pasó:")
            for e in resultado["errores"][:10]:
                print("        %s" % e)
            listo = False
    print("Todo listo." if listo else "Falta algo: revise las líneas marcadas arriba.")
    return 0 if listo else 2


def _abrir(ruta: Path) -> None:
    if os.environ.get("FLUJO_NO_ABRIR"):
        return
    try:
        webbrowser.open(ruta.resolve().as_uri())
    except Exception:  # sin navegador (un servidor, una prueba): no es un error
        pass


def _salir(codigo: int, como_json: bool, **datos) -> int:
    if como_json:
        datos["ok"] = codigo == 0
        datos["codigo"] = codigo
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    return codigo


def main(argv=None) -> int:
    preparar_consola()
    parser = argparse.ArgumentParser(
        prog="dibujar.py",
        description="Dibuja el flujo de un proceso a partir de su modelo intermedio (proceso.json).")
    parser.add_argument("proceso", nargs="?", help="ruta al proceso.json")
    parser.add_argument("--relato", help="relato o transcripción para comprobar las citas "
                                         "(por defecto, relato.md junto al proceso)")
    parser.add_argument("--salida", help="carpeta donde guardar el dibujo (por defecto, la del proceso)")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador al terminar")
    parser.add_argument("--comprobar", action="store_true",
                        help="revisar que Python, Node y Archify estén listos")
    parser.add_argument("--json", action="store_true", help="imprimir el resultado en JSON")
    args = parser.parse_args(argv)

    if args.comprobar:
        return comprobar()
    if not args.proceso:
        parser.print_help()
        return 1
    como_json = args.json  # con --json solo se imprime el informe final
    ruta = Path(args.proceso).expanduser()
    datos, errores = modelo.leer(ruta)
    if not errores:
        errores, avisos = modelo.revisar(datos)
    else:
        avisos = []
    if errores:
        if not como_json:
            print("El modelo tiene %d %s; corríjalo y vuelva a correr la orden:"
                  % (len(errores), "error" if len(errores) == 1 else "errores"))
            for e in errores:
                print("  - %s" % e)
        return _salir(1, como_json, errores=errores, avisos=avisos)

    ruta_relato = Path(args.relato).expanduser() if args.relato else ruta.parent / "relato.md"
    if ruta_relato.is_file():
        avisos += modelo.revisar_citas(datos, ruta_relato.read_text(encoding="utf-8-sig", errors="replace"))
    else:
        avisos.append("No encontré %s: no pude comprobar que las citas salgan del relato." % ruta_relato)

    node, version = archify.buscar_node()
    if not node:
        if not como_json:
            print(version)
            print(archify.como_instalar_node())
        return _salir(2, como_json, errores=[version, archify.como_instalar_node()], avisos=avisos)

    resultado = convertidor.convertir(datos)
    avisos += resultado["avisos"]
    partes = resultado["partes"]
    total = len(partes)
    nombres = ["flujo"] if total == 1 else ["flujo-parte-%d" % p["numero"] for p in partes]
    carpeta = Path(args.salida).expanduser() if args.salida else ruta.parent
    carpeta.mkdir(parents=True, exist_ok=True)
    por_id = {p["id"]: p for p in datos["pasos"]}

    archivos, calidades = [], []
    for parte, nombre in zip(partes, nombres):
        html = carpeta / (nombre + ".html")
        informe = archify.dibujar(node, parte["spec"], carpeta / (nombre + ".archify.json"), html)
        if not informe["ok"]:
            if not como_json:
                print("Archify no pudo dibujar %s. Esto dijo el compilador:" % html.name)
                for e in informe["errores"][:20]:
                    print("  - %s" % e)
                print("Suele resolverse acortando títulos o etiquetas, o revisando las conexiones.")
            return _salir(3, como_json, errores=informe["errores"], avisos=avisos)
        navegacion = None
        if total > 1:
            navegacion = {"numero": parte["numero"], "total": total,
                          "otras": [(n + 1, nombres[n] + ".html") for n in range(total) if n + 1 != parte["numero"]]}
        marca.vestir(html, datos["idioma"],
                     pasos=[(por_id[i]["titulo"], por_id[i]["cita"]) for i in parte["pasos"]],
                     citas=parte["citas"], inicios=parte["inicios"], fines=parte["fines"],
                     navegacion=navegacion)
        archivos.append(html)
        calidades.append(informe["calidad"])

    if not como_json:
        print("Listo: %s (%s)." % (datos["titulo"], modelo.resumen(datos)))
        for html, calidad in zip(archivos, calidades):
            print("  Dibujo: %s" % html.resolve())
            print("          validado por Archify en calidad %s." % calidad)
        if total > 1:
            print("  El proceso no cabía en un solo dibujo: va en %d partes enlazadas entre sí." % total)
        _lista("Preguntas abiertas que conviene responder:", datos["preguntas_abiertas"])
        _lista("Avisos:", avisos)
        print("Para guardar una imagen: abra el dibujo en el navegador y use el botón «Exportar», "
              "arriba a la derecha (PNG o SVG).")
    if not args.no_abrir:
        _abrir(archivos[0])
    return _salir(0, como_json, archivos=[str(a.resolve()) for a in archivos], calidad=calidades,
                  avisos=avisos, preguntas_abiertas=datos["preguntas_abiertas"])
