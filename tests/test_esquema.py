# -*- coding: utf-8 -*-
"""El validador propio y la biblioteca jsonschema tienen que decir lo mismo."""
import copy

import pytest

from conftest import TODOS, cargar
from flujo import esquema, modelo

jsonschema = pytest.importorskip("jsonschema")


@pytest.fixture(scope="module")
def esq():
    return modelo.cargar_esquema()


def test_el_esquema_es_json_schema_valido(esq):
    jsonschema.Draft202012Validator.check_schema(esq)


@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_los_procesos_de_prueba_cumplen_el_esquema(esq, ruta):
    dato = cargar(ruta)
    assert esquema.validar(dato, esq) == []
    assert list(jsonschema.Draft202012Validator(esq).iter_errors(dato)) == []


def _danar(funcion):
    dato = cargar(TODOS[-1])
    funcion(dato)
    return dato


DANOS = {
    "falta_un_campo": lambda d: d["pasos"][0].pop("cita"),
    "tipo_desconocido": lambda d: d["pasos"][0].update(tipo="proceso"),
    "titulo_largo": lambda d: d["pasos"][0].update(titulo="Un título que se pasa de largo para caber"),
    "id_con_mayusculas": lambda d: d["carriles"][0].update(id="Ventas"),
    "id_con_tilde": lambda d: d["pasos"][0].update(id="envía"),
    "campo_que_sobra": lambda d: d["pasos"][0].update(comentario="no va"),
    "texto_en_vez_de_lista": lambda d: d.update(preguntas_abiertas="ninguna"),
    "null_donde_va_texto": lambda d: d["pasos"][0].update(titulo=None),
    "booleano_como_texto": lambda d: d["carriles"][0].update(externo="sí"),
    "version_equivocada": lambda d: d.update(version=2),
    "sin_pasos": lambda d: d.update(pasos=[]),
    "idioma_desconocido": lambda d: d.update(idioma="pt"),
}


@pytest.mark.parametrize("nombre", sorted(DANOS))
def test_ambos_validadores_rechazan_lo_mismo(esq, nombre):
    dato = _danar(DANOS[nombre])
    propios = esquema.validar(dato, esq)
    externos = list(jsonschema.Draft202012Validator(esq).iter_errors(dato))
    assert propios, "el validador propio no vio el error"
    assert externos, "jsonschema no vio el error"


def test_los_errores_dicen_donde_y_que(esq):
    dato = _danar(DANOS["titulo_largo"])
    errores = esquema.validar(dato, esq)
    assert len(errores) == 1
    assert errores[0].startswith("pasos[0].titulo:")
    assert "máximo es 32" in errores[0]

    dato = _danar(DANOS["id_con_tilde"])
    assert any("minúsculas" in e and "pasos[0].id" in e for e in esquema.validar(dato, esq))

    dato = _danar(DANOS["falta_un_campo"])
    assert esquema.validar(dato, esq) == ["pasos[0]: falta el campo «cita»."]


def test_null_permitido_donde_el_esquema_lo_dice(esq):
    dato = copy.deepcopy(cargar(TODOS[-1]))
    dato["pasos"][0]["detalle"] = None
    dato["pasos"][0]["herramienta"] = None
    dato["objetivo"] = None
    assert esquema.validar(dato, esq) == []
