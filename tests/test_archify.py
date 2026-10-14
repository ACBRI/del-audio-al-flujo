# -*- coding: utf-8 -*-
"""Lo que produce el convertidor, validado por el Archify copiado en vendor/."""
import json

import pytest

from conftest import RAIZ, TODOS, cargar
from flujo import archify, convertidor


@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_cada_parte_pasa_la_calidad_showcase(node, tmp_path, ruta):
    resultado = convertidor.convertir(cargar(ruta))
    for parte in resultado["partes"]:
        especificacion = tmp_path / ("parte-%d.archify.json" % parte["numero"])
        html = tmp_path / ("parte-%d.html" % parte["numero"])
        informe = archify.dibujar(node, parte["spec"], especificacion, html)
        assert informe["ok"], informe["errores"]
        assert informe["calidad"] == "showcase", "bajó a standard: %s" % ruta.name
        assert html.is_file() and html.stat().st_size > 100_000
        # La validación independiente de Archify sobre el archivo final.
        assert archify.validar(node, especificacion, "showcase")["ok"]


def test_la_validacion_reporta_textos_que_no_caben(node, tmp_path):
    spec = convertidor.convertir(cargar(TODOS[-1]))["partes"][0]["spec"]
    for n in spec["nodes"]:
        n["width"] = 60
    for e in spec["edges"]:
        e.pop("route", None)   # el compilador avisa de a un problema por vez: aquí, solo los anchos
    ruta = tmp_path / "estrecho.json"
    ruta.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    informe = archify.validar(node, ruta)
    assert not informe["ok"]
    assert archify.corregir(spec, informe), "el diagnóstico de ancho no se aprovechó"
    assert all(n["width"] > 60 for n in spec["nodes"])


def test_una_ruta_imposible_se_quita(node, tmp_path):
    spec = convertidor.convertir(cargar(TODOS[-1]))["partes"][0]["spec"]
    for e in spec["edges"]:
        if (e["from"], e["to"]) == ("tiene_cupo", "arma_pedido"):
            e["route"] = "straight"   # están en carriles distintos: no hay línea recta posible
    informe = archify.dibujar(node, spec, tmp_path / "f.archify.json", tmp_path / "f.html")
    assert informe["ok"]
    arista = next(e for e in spec["edges"] if (e["from"], e["to"]) == ("tiene_cupo", "arma_pedido"))
    assert arista.get("route") != "straight"


def test_especificaciones_escritas_a_mano(node, tmp_path):
    """Los flujos de ejemplo del sitio de Andrés, escritos a mano, siguen compilando."""
    for nombre in ("venta-asis.workflow.json", "venta-tobe-en.workflow.json"):
        ruta = RAIZ / "tests" / "archify" / nombre
        assert archify.validar(node, ruta, "showcase")["ok"], nombre


def test_version_de_archify():
    assert archify.version_archify().startswith("2.")
    assert archify.CLI.is_file()
