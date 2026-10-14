# -*- coding: utf-8 -*-
"""Archify, el compilador que dibuja: dónde está Node, cómo se llama y cómo se
corrige lo que el compilador rechaza.

Archify (MIT, de tt-a1i) va copiado en vendor/archify para no depender de nada
instalado aparte; solo pide Node 18 o más nuevo. Funciona igual en Windows,
macOS y Linux: todas las rutas pasan por pathlib y Archify se llama con una
lista de argumentos, sin intérprete de órdenes de por medio.

El ciclo de dibujo viene del generador de los flujos del sitio andresbrinez.com,
del mismo autor: se valida, se corrige lo que el diagnóstico permite corregir
(un ancho que no alcanza) y se vuelve a validar; la entrega final la hace
`archify deliver`, que vuelve a revisar el resultado antes de escribirlo.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIFY = RAIZ / "vendor" / "archify"
CLI = ARCHIFY / "bin" / "archify.mjs"
NODE_MINIMO = 18
ESPERA = 180  # segundos; un dibujo normal tarda menos de uno


# ------------------------------------------------------------------ Node

def _version(texto: str):
    m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", texto or "")
    return tuple(int(x) for x in m.groups()) if m else None


def candidatos_node() -> list:
    """Rutas donde suele quedar Node en cada sistema, de la más a la menos probable."""
    lista = []
    propia = os.environ.get("FLUJO_NODE")
    if propia:
        lista.append(Path(propia))
    en_path = shutil.which("node")
    if en_path:
        lista.append(Path(en_path))
    casa = Path.home()
    if platform.system() == "Windows":
        for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            base = os.environ.get(variable)
            if base:
                lista.append(Path(base) / "nodejs" / "node.exe")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            lista.append(Path(local) / "Programs" / "nodejs" / "node.exe")
            lista.append(Path(local) / "Volta" / "bin" / "node.exe")
        nvm = os.environ.get("NVM_SYMLINK")
        if nvm:
            lista.append(Path(nvm) / "node.exe")
        lista.append(casa / "scoop" / "apps" / "nodejs-lts" / "current" / "node.exe")
        lista.append(casa / "scoop" / "apps" / "nodejs" / "current" / "node.exe")
    else:
        lista += [Path("/opt/homebrew/bin/node"), Path("/usr/local/bin/node"), Path("/usr/bin/node"),
                  casa / ".volta" / "bin" / "node"]
        versiones = list((casa / ".nvm" / "versions" / "node").glob("v*/bin/node"))
        versiones.sort(key=lambda p: _version(p.parent.parent.name) or (0, 0, 0), reverse=True)
        lista += versiones
    vistos, unicos = set(), []
    for ruta in lista:
        clave = str(ruta).lower() if platform.system() == "Windows" else str(ruta)
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(ruta)
    return unicos


def version_de_node(ruta: Path):
    try:
        r = subprocess.run([str(ruta), "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return _version(r.stdout) if r.returncode == 0 else None


def buscar_node():
    """Devuelve (ruta, versión) del primer Node utilizable, o (None, motivo)."""
    viejo = None
    for ruta in candidatos_node():
        if not ruta.is_file():
            continue
        version = version_de_node(ruta)
        if version is None:
            continue
        if version[0] >= NODE_MINIMO:
            return ruta, version
        viejo = (ruta, version)
    if viejo:
        return None, "Encontré Node %s en %s, pero hace falta la versión %d o más nueva." % (
            ".".join(map(str, viejo[1])), viejo[0], NODE_MINIMO)
    return None, "No encontré Node.js en este computador."


def como_instalar_node() -> str:
    sistema = platform.system()
    if sistema == "Windows":
        return ("Instale Node.js LTS desde https://nodejs.org (botón «LTS», instalador .msi, todo con las "
                "opciones por defecto), o en PowerShell: winget install OpenJS.NodeJS.LTS. "
                "Después cierre y vuelva a abrir la terminal.")
    if sistema == "Darwin":
        return ("Instale Node.js LTS desde https://nodejs.org (instalador .pkg), o con Homebrew: "
                "brew install node. Después cierre y vuelva a abrir la Terminal.")
    return ("Instale Node.js 18 o más nuevo con el gestor de paquetes de su distribución "
            "o desde https://nodejs.org.")


# ------------------------------------------------------------------ Archify

def version_archify() -> str:
    try:
        return json.loads((ARCHIFY / "package.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "desconocida"


def _correr(node: Path, argumentos: list) -> dict:
    # Archify corre desde su propia carpeta: toda ruta tiene que ir absoluta.
    argumentos = [str(Path(a).resolve()) if isinstance(a, Path) else str(a) for a in argumentos]
    try:
        r = subprocess.run([str(node), str(CLI)] + argumentos, cwd=str(ARCHIFY),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=ESPERA)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Archify tardó más de %d segundos y se detuvo." % ESPERA}
    except OSError as error:
        return {"ok": False, "error": "No pude ejecutar Node: %s" % error}
    try:
        informe = json.loads(r.stdout)
    except ValueError:
        return {"ok": False, "error": (r.stderr or r.stdout or "Archify no respondió.").strip()[:2000]}
    if r.returncode != 0:
        informe["ok"] = False
    return informe


def validar(node: Path, especificacion: Path, calidad: str = "showcase") -> dict:
    return _correr(node, ["validate", "workflow", especificacion, "--quality", calidad, "--json"])


def entregar(node: Path, especificacion: Path, html: Path, calidad: str = "showcase") -> dict:
    return _correr(node, ["deliver", "workflow", especificacion, html, "--quality", calidad, "--json"])


# ------------------------------------------------------------------ correcciones

_ETIQUETA = re.compile(r'Label "(?P<texto>[^"]*)" \(~(?P<medida>\d+)px\) is wider than node "(?P<nodo>[^"]+)"')
_LINEA = re.compile(r'(?:Sublabel|Tag) "(?P<texto>[^"]*)" needs ~(?P<medida>\d+)px .*? node "(?P<nodo>[^"]+)" '
                    r'provides (?P<hay>\d+)px')
_FASE = re.compile(r'Phase label "(?P<texto>[^"]*)" \(~(?P<medida>\d+)px\) is wider than its (?P<hay>\d+)px span')
_ARISTA = re.compile(r'edge "(?P<desde>[^"]+?)->(?P<hacia>[^"]+)"')


def mensajes(informe: dict) -> list:
    salida = [d.get("message", "") for d in informe.get("diagnostics", []) if d.get("message")]
    for problema in informe.get("composition", {}).get("issues", []) or []:
        salida.append(problema.get("message") or json.dumps(problema, ensure_ascii=False)[:300])
    if not salida and informe.get("error"):
        salida.append(str(informe["error"]))
    return salida


def corregir(especificacion: dict, informe: dict) -> bool:
    """Aplica lo que el diagnóstico permite corregir. Devuelve True si cambió algo.

    El compilador dice cuánto mide cada texto que no cabe: se le hace caso y se
    ensancha la columna entera, para que los nodos de una columna sigan iguales.
    """
    nodos = {n["id"]: n for n in especificacion["nodes"]}
    columnas: dict = {}
    cambio = False
    for d in informe.get("diagnostics", []):
        mensaje = d.get("message", "")
        # Una preferencia de trazado que no se puede cumplir: se quita y el
        # compilador elige la ruta por su cuenta.
        m = _ARISTA.search(mensaje)
        if m:
            for arista in especificacion["edges"]:
                if (arista["from"], arista["to"]) == (m.group("desde"), m.group("hacia")):
                    for clave in ("route", "fromSide", "toSide"):
                        if clave in arista:
                            del arista[clave]
                            cambio = True
            continue
        m = _ETIQUETA.search(mensaje)
        if m and m.group("nodo") in nodos:
            nodo = nodos[m.group("nodo")]
            columnas[nodo["col"]] = max(columnas.get(nodo["col"], 0), int(m.group("medida")) + 10)
            continue
        m = _LINEA.search(mensaje)
        if m and m.group("nodo") in nodos:
            nodo = nodos[m.group("nodo")]
            falta = int(m.group("medida")) - int(m.group("hay")) + 4
            columnas[nodo["col"]] = max(columnas.get(nodo["col"], 0), nodo.get("width", 92) + falta)
            continue
        m = _FASE.search(mensaje)
        if m:
            for fase in especificacion.get("phases", []):
                if fase["label"] == m.group("texto"):
                    tramo = list(range(fase["fromCol"], fase["toCol"] + 1))
                    extra = -(-(int(m.group("medida")) - int(m.group("hay")) + 12) // len(tramo))
                    for c in tramo:
                        actual = max([n.get("width", 92) for n in especificacion["nodes"] if n["col"] == c] or [92])
                        columnas[c] = max(columnas.get(c, 0), actual + extra)
    for n in especificacion["nodes"]:
        ancho = columnas.get(n["col"])
        if ancho and ancho > n.get("width", 92):
            n["width"] = int(ancho)
            cambio = True
    return cambio


_PAR = re.compile(r'"(?P<desde>[^"]+)" -> "(?P<hacia>[^"]+)"')
RUTAS = ("up-channel", "bottom-channel", "return-left", "outside-right", "drop")


def _cuantos_errores(informe: dict) -> int:
    if informe.get("ok"):
        return 0
    return max(1, len(informe.get("diagnostics", []))
               + int(informe.get("composition", {}).get("summary", {}).get("errors", 0) or 0))


def probar_rutas(node: Path, especificacion: dict, ruta: Path, informe: dict, intentos: int = 12) -> bool:
    """Busca otra ruta para las líneas que se enciman.

    Cuando la calidad «showcase» se pierde por dos líneas que comparten un
    tramo o se cruzan, se prueban los trazados que Archify ofrece de fábrica
    (por un canal arriba, por un canal abajo, de vuelta por la izquierda...)
    en las líneas señaladas, empezando por las vueltas y los desvíos, que son
    las que pueden dar un rodeo sin confundir la lectura. Se queda el que más
    errores quite. Devuelve True si mejoró algo.
    """
    implicadas = []
    for texto in mensajes(informe):
        for m in _PAR.finditer(texto):
            par = (m.group("desde"), m.group("hacia"))
            if par not in implicadas:
                implicadas.append(par)
    aristas = [a for a in especificacion["edges"] if (a["from"], a["to"]) in implicadas]
    aristas.sort(key=lambda a: (a.get("role") not in ("return", "branch"), a.get("variant") != "dashed"))
    mejor = _cuantos_errores(informe)
    calidad = especificacion["meta"].get("quality_profile", "showcase")
    for arista in aristas:
        original = arista.get("route")
        elegido = original
        for preset in RUTAS:
            if intentos <= 0 or preset == original:
                continue
            intentos -= 1
            arista["route"] = preset
            _escribir_json(ruta, especificacion)
            errores = _cuantos_errores(validar(node, ruta, calidad))
            if errores < mejor:
                mejor, elegido = errores, preset
                if errores == 0:
                    return True
        if elegido is None:
            arista.pop("route", None)
        else:
            arista["route"] = elegido
        if elegido != original:
            return True
    return False


def _escribir_json(ruta: Path, datos: dict) -> None:
    with open(ruta, "w", encoding="utf-8", newline="\n") as salida:
        json.dump(datos, salida, ensure_ascii=False, indent=2)
        salida.write("\n")


def dibujar(node: Path, especificacion: dict, ruta_especificacion: Path, ruta_html: Path) -> dict:
    """Valida, corrige y entrega. Devuelve un informe con `ok`, `calidad` y `errores`.

    Primero se intenta la calidad «showcase», la más exigente de Archify: sin
    cruces de líneas ni pasillos ambiguos. Si el dibujo no la alcanza después de
    las correcciones, se acepta la calidad «standard», que tolera un cruce como
    advertencia. Si tampoco, se devuelven los mensajes del compilador.
    """
    calidad = "showcase"
    informe: dict = {}
    rondas_de_rutas = 3  # cada ronda valida hasta 12 veces; así el peor caso no pasa de un minuto
    for _ in range(12):
        especificacion["meta"]["quality_profile"] = calidad
        _escribir_json(ruta_especificacion, especificacion)
        informe = validar(node, ruta_especificacion, calidad)
        if informe.get("ok"):
            break
        if corregir(especificacion, informe):
            continue
        if calidad == "showcase" and rondas_de_rutas > 0:
            rondas_de_rutas -= 1
            if probar_rutas(node, especificacion, ruta_especificacion, informe):
                continue
        if calidad == "showcase":
            calidad = "standard"
            continue
        break
    if not informe.get("ok"):
        return {"ok": False, "calidad": calidad, "errores": mensajes(informe)}
    entrega = entregar(node, ruta_especificacion, ruta_html, calidad)
    if not entrega.get("ok"):
        return {"ok": False, "calidad": calidad, "errores": mensajes(entrega)}
    validacion = entrega.get("validation", {})
    return {"ok": True, "calidad": calidad, "errores": [],
            "revisiones": "%s de %s" % (validacion.get("checksPassed", "?"), validacion.get("checkCount", "?")),
            "advertencias": validacion.get("warnings", 0)}
