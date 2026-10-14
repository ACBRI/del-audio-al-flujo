# -*- coding: utf-8 -*-
"""Validador de JSON Schema reducido a lo que usa esquemas/proceso.schema.json.

La herramienta tiene que correr con un Python recién instalado, sin `pip install`.
Por eso no usa la biblioteca jsonschema: valida aquí las palabras clave que el
esquema emplea (type, const, enum, required, properties, additionalProperties,
items, minItems, maxItems, minLength, maxLength, pattern y $ref locales) y
devuelve los errores en español, con la ruta del dato: `pasos[3].titulo`.

Las pruebas comparan este validador con jsonschema para que no se separen.
"""
from __future__ import annotations

import re
from typing import Any

PATRON_ID = "^[a-z][a-z0-9_]{0,39}$"

_NOMBRES = {
    "string": "texto",
    "boolean": "true o false",
    "array": "una lista",
    "object": "un objeto",
    "null": "null",
    "integer": "un número entero",
    "number": "un número",
}


def _nombre_de(valor: Any) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true o false"
    if isinstance(valor, (int, float)):
        return "un número"
    if isinstance(valor, str):
        return "texto"
    if isinstance(valor, list):
        return "una lista"
    if isinstance(valor, dict):
        return "un objeto"
    return type(valor).__name__


def _es_tipo(valor: Any, tipo: str) -> bool:
    if tipo == "string":
        return isinstance(valor, str)
    if tipo == "boolean":
        return isinstance(valor, bool)
    if tipo == "array":
        return isinstance(valor, list)
    if tipo == "object":
        return isinstance(valor, dict)
    if tipo == "null":
        return valor is None
    if tipo == "integer":
        return isinstance(valor, int) and not isinstance(valor, bool)
    if tipo == "number":
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    raise ValueError("tipo de JSON Schema no previsto: %s" % tipo)


def _resolver(raiz: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError("solo se admiten referencias locales: %s" % ref)
    nodo: Any = raiz
    for parte in ref[2:].split("/"):
        nodo = nodo[parte]
    return nodo


def _ruta(base: str, clave: Any) -> str:
    if isinstance(clave, int):
        return "%s[%d]" % (base, clave)
    return "%s.%s" % (base, clave) if base else str(clave)


def _citar(valor: Any) -> str:
    texto = str(valor)
    if len(texto) > 40:
        texto = texto[:37] + "..."
    return "«%s»" % texto


def validar(dato: Any, esquema: dict) -> list:
    """Devuelve la lista de errores; vacía si el dato cumple el esquema."""
    errores: list = []
    _validar(dato, esquema, esquema, "", errores)
    return errores


def _validar(dato: Any, esq: dict, raiz: dict, ruta: str, errores: list) -> None:
    donde = ruta or "el documento"
    if "$ref" in esq:
        esq = _resolver(raiz, esq["$ref"])

    if "type" in esq:
        tipos = esq["type"] if isinstance(esq["type"], list) else [esq["type"]]
        if not any(_es_tipo(dato, t) for t in tipos):
            esperado = " o ".join(_NOMBRES.get(t, t) for t in tipos)
            errores.append("%s: debe ser %s y llegó %s." % (donde, esperado, _nombre_de(dato)))
            return

    if "const" in esq and dato != esq["const"]:
        errores.append("%s: debe valer %s." % (donde, esq["const"]))

    if "enum" in esq and dato not in esq["enum"]:
        opciones = ", ".join(str(x) for x in esq["enum"])
        errores.append("%s: %s no es válido; use uno de: %s." % (donde, _citar(dato), opciones))

    if isinstance(dato, str):
        if "minLength" in esq and len(dato) < esq["minLength"]:
            errores.append("%s: es demasiado corto (mínimo %d caracteres)." % (donde, esq["minLength"]))
        if "maxLength" in esq and len(dato) > esq["maxLength"]:
            errores.append("%s: tiene %d caracteres y el máximo es %d. Acórtelo."
                           % (donde, len(dato), esq["maxLength"]))
        if "pattern" in esq and not re.search(esq["pattern"], dato):
            if esq["pattern"] == PATRON_ID:
                errores.append("%s: %s no sirve como id: use minúsculas, números y guion bajo, "
                               "sin espacios ni tildes, empezando por una letra." % (donde, _citar(dato)))
            else:
                errores.append("%s: %s no tiene el formato esperado." % (donde, _citar(dato)))

    if isinstance(dato, list):
        if "minItems" in esq and len(dato) < esq["minItems"]:
            errores.append("%s: necesita al menos %d elementos." % (donde, esq["minItems"]))
        if "maxItems" in esq and len(dato) > esq["maxItems"]:
            errores.append("%s: tiene %d elementos y el máximo es %d."
                           % (donde, len(dato), esq["maxItems"]))
        if "items" in esq:
            for i, elemento in enumerate(dato):
                _validar(elemento, esq["items"], raiz, _ruta(ruta, i), errores)

    if isinstance(dato, dict):
        propiedades = esq.get("properties", {})
        for clave in esq.get("required", []):
            if clave not in dato:
                errores.append("%s: falta el campo «%s»." % (donde, clave))
        if esq.get("additionalProperties") is False:
            for clave in dato:
                if clave not in propiedades:
                    errores.append("%s: el campo «%s» no existe en el esquema." % (donde, clave))
        for clave, sub in propiedades.items():
            if clave in dato:
                _validar(dato[clave], sub, raiz, _ruta(ruta, clave), errores)
