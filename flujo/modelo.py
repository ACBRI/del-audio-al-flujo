# -*- coding: utf-8 -*-
"""Lectura y revisión del modelo intermedio (proceso.json).

Tres revisiones, de la más estricta a la más blanda:

1. El esquema (esquemas/proceso.schema.json): campos, tipos y largos.
2. La coherencia: que cada conexión apunte a pasos que existen, que cada paso
   esté en un carril declarado, que las decisiones tengan al menos dos salidas
   con su respuesta. Esto también bloquea el dibujo.
3. Las citas: si junto al modelo está el relato, cada cita tiene que aparecer
   en él tal cual. Si no aparece, es un aviso: puede ser una coma de diferencia,
   o un paso que el relato no respalda. Quien escribió el modelo lo revisa.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from . import esquema

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ESQUEMA = RAIZ / "esquemas" / "proceso.schema.json"


def cargar_esquema() -> dict:
    return json.loads(RUTA_ESQUEMA.read_text(encoding="utf-8"))


def leer(ruta: Path):
    """Lee el JSON. Devuelve (modelo, errores)."""
    try:
        # utf-8-sig: el Bloc de notas de Windows a veces antepone una marca BOM.
        texto = Path(ruta).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None, ["No encontré el archivo %s." % ruta]
    except UnicodeDecodeError:
        return None, ["%s no está guardado en UTF-8. Guárdelo de nuevo con esa codificación." % ruta]
    try:
        return json.loads(texto), []
    except json.JSONDecodeError as error:
        return None, ["%s no es un JSON válido: %s (línea %d, columna %d)."
                      % (ruta, error.msg, error.lineno, error.colno)]


def revisar(modelo: Any):
    """Devuelve (errores, avisos). Con errores no se dibuja."""
    errores = esquema.validar(modelo, cargar_esquema())
    if errores:
        return errores, []
    return _coherencia(modelo)


def _repetidos(ids):
    vistos, repetidos = set(), []
    for i in ids:
        if i in vistos and i not in repetidos:
            repetidos.append(i)
        vistos.add(i)
    return repetidos


def _coherencia(m: dict):
    errores: list = []
    avisos: list = []
    carriles = [c["id"] for c in m["carriles"]]
    fases = [f["id"] for f in m["fases"]]
    pasos = [p["id"] for p in m["pasos"]]
    for nombre, ids in (("carril", carriles), ("fase", fases), ("paso", pasos)):
        for r in _repetidos(ids):
            errores.append("Hay dos elementos de tipo %s con el id «%s». Cada id debe ser único." % (nombre, r))

    por_id = {p["id"]: p for p in m["pasos"]}
    for p in m["pasos"]:
        if p["carril"] not in carriles:
            errores.append("El paso «%s» está en el carril «%s», que no existe en «carriles»."
                           % (p["id"], p["carril"]))
        if p["fase"] is not None and p["fase"] not in fases:
            errores.append("El paso «%s» está en la fase «%s», que no existe en «fases»."
                           % (p["id"], p["fase"]))

    salidas: dict = {i: [] for i in pasos}
    entradas: dict = {i: [] for i in pasos}
    vistas = set()
    for n, c in enumerate(m["conexiones"]):
        d, h = c["desde"], c["hacia"]
        malas = [x for x in (d, h) if x not in por_id]
        for x in malas:
            errores.append("La conexión %d (%s -> %s) nombra el paso «%s», que no existe." % (n, d, h, x))
        if malas:
            continue
        if d == h:
            errores.append("La conexión %d va del paso «%s» a sí mismo. Si el paso se repite, "
                           "dibuje la vuelta hacia el paso anterior." % (n, d))
            continue
        if (d, h) in vistas:
            errores.append("La conexión %s -> %s está repetida." % (d, h))
            continue
        vistas.add((d, h))
        salidas[d].append(c)
        entradas[h].append(c)

    for p in m["pasos"]:
        pid = p["id"]
        if p["tipo"] == "decision":
            sal = salidas[pid]
            if len(sal) < 2:
                errores.append("La decisión «%s» necesita al menos dos salidas (por ejemplo, Sí y No); "
                               "tiene %d. Si el relato no dice qué pasa en el otro caso, agréguelo a "
                               "«preguntas_abiertas» y deje el paso como tarea." % (pid, len(sal)))
            sin = [c["hacia"] for c in sal if not (c["etiqueta"] or "").strip()]
            if sin:
                errores.append("Las salidas de la decisión «%s» necesitan etiqueta (Sí, No...): "
                               "falta en la que va a %s." % (pid, ", ".join("«%s»" % x for x in sin)))
            etiquetas = [(c["etiqueta"] or "").strip().lower() for c in sal if (c["etiqueta"] or "").strip()]
            if len(set(etiquetas)) < len(etiquetas):
                errores.append("Dos salidas de la decisión «%s» tienen la misma etiqueta." % pid)
        if len(pasos) > 1 and not salidas[pid] and not entradas[pid]:
            errores.append("El paso «%s» no tiene conexiones. Conéctelo con el paso anterior o el "
                           "siguiente según el relato, o quítelo." % pid)
        if p["tipo"] == "fin" and salidas[pid]:
            avisos.append("El paso «%s» es de tipo fin pero tiene salidas." % pid)

    if errores:
        return errores, avisos

    usados = {p["carril"] for p in m["pasos"]}
    for c in m["carriles"]:
        if c["id"] not in usados:
            avisos.append("El carril «%s» no tiene pasos; no se dibuja." % c["nombre"])
    usadas = {p["fase"] for p in m["pasos"]}
    for f in m["fases"]:
        if f["id"] not in usadas:
            avisos.append("La fase «%s» no tiene pasos; no se dibuja." % f["nombre"])

    inicios = [p["id"] for p in m["pasos"] if p["tipo"] == "inicio"] or [pasos[0]]
    alcanzados = set(inicios)
    pendientes = list(inicios)
    while pendientes:
        actual = pendientes.pop()
        for c in salidas[actual]:
            if c["hacia"] not in alcanzados:
                alcanzados.add(c["hacia"])
                pendientes.append(c["hacia"])
    perdidos = [x for x in pasos if x not in alcanzados]
    if perdidos:
        avisos.append("No se llega a estos pasos desde el inicio: %s. Revise las conexiones."
                      % ", ".join("«%s»" % x for x in perdidos))
    return errores, avisos


# ---------------------------------------------------------------- citas

_PUNTUACION = re.compile(r"[\.,;:!\?¡¿«»\"“”‘’'\(\)\[\]—–\-…]")


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).casefold()
    texto = _PUNTUACION.sub(" ", texto)
    return " ".join(texto.split())


def esta_en(cita: str, relato_normalizado: str) -> bool:
    """La cita está en el relato si cada uno de sus fragmentos aparece, en orden.

    Se permiten los puntos suspensivos para saltar una parte de la frase.
    """
    fragmentos = [normalizar(f) for f in re.split(r"\.\.\.|…", cita)]
    fragmentos = [f for f in fragmentos if f]
    desde = 0
    for f in fragmentos:
        pos = relato_normalizado.find(f, desde)
        if pos < 0:
            return False
        desde = pos + len(f)
    return bool(fragmentos)


def revisar_citas(modelo: dict, relato: str) -> list:
    normal = normalizar(relato)
    avisos = []
    for p in modelo["pasos"]:
        if not esta_en(p["cita"], normal):
            avisos.append("La cita del paso «%s» no aparece tal cual en el relato: «%s»."
                          % (p["id"], p["cita"]))
    for n, o in enumerate(modelo["observaciones"]):
        if o["cita"] and not esta_en(o["cita"], normal):
            avisos.append("La cita de la observación %d no aparece tal cual en el relato: «%s»."
                          % (n + 1, o["cita"]))
    return avisos


def resumen(modelo: dict) -> str:
    pasos = modelo["pasos"]
    decisiones = sum(1 for p in pasos if p["tipo"] == "decision")
    dolores = sum(1 for p in pasos if p["dolor"])
    partes = ["%d pasos" % len(pasos), "%d carriles" % len({p["carril"] for p in pasos})]
    if decisiones:
        partes.append("%d %s" % (decisiones, "decisión" if decisiones == 1 else "decisiones"))
    if dolores:
        partes.append("%d %s" % (dolores, "punto de dolor" if dolores == 1 else "puntos de dolor"))
    return ", ".join(partes)
