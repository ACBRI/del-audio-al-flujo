# -*- coding: utf-8 -*-
"""La piel de la marca y el idioma del visor sobre un HTML real de Archify."""
import json
import re

import pytest

from conftest import EJEMPLO, cargar
from flujo import archify, convertidor, idioma, marca


@pytest.fixture(scope="module")
def html_crudo(tmp_path_factory, node):
    carpeta = tmp_path_factory.mktemp("crudo")
    parte = convertidor.convertir(cargar(EJEMPLO))["partes"][0]
    informe = archify.dibujar(node, parte["spec"], carpeta / "f.archify.json", carpeta / "f.html")
    assert informe["ok"]
    return (carpeta / "f.html").read_text(encoding="utf-8")


def _tabla(html):
    return json.loads(idioma.TABLA.search(html).group(2))


def test_traduccion_completa_y_json_valido(html_crudo):
    original = _tabla(html_crudo)
    html = idioma.traducir(html_crudo, "es")
    tabla = _tabla(html)
    assert set(tabla["messages"]) == set(original["messages"])
    sin_traducir = [k for k, v in tabla["messages"].items() if v == original["messages"][k] and k in idioma.ES
                    and idioma.ES[k] != v]
    assert sin_traducir == []
    # Los marcadores que el visor rellena siguen intactos.
    for clave, texto in original["messages"].items():
        assert re.findall(r"\{\w+\}", texto) == re.findall(r"\{\w+\}", tabla["messages"][clave]) or \
            sorted(re.findall(r"\{\w+\}", texto)) == sorted(re.findall(r"\{\w+\}", tabla["messages"][clave]))
    assert '<html lang="es"' in html
    assert "<title>Del pedido al despacho</title>" in html
    assert 'aria-label="Enfocar ' in html


def test_en_ingles_solo_cambian_los_tipos(html_crudo):
    html = idioma.traducir(html_crudo, "en")
    tabla = _tabla(html)
    assert tabla["messages"]["viewer.kind.security"] == "Where it hurts"
    assert tabla["messages"]["viewer.export.button"] == "Export"
    assert '<html lang="en"' in html


def test_vestir_una_sola_vez(html_crudo, tmp_path):
    ruta = tmp_path / "f.html"
    ruta.write_text(html_crudo, encoding="utf-8")
    assert marca.vestir(ruta, "es", pasos=[("Envía el pedido", "El cliente nos escribe")])
    primera = ruta.read_text(encoding="utf-8")
    assert not marca.vestir(ruta, "es")
    assert ruta.read_text(encoding="utf-8") == primera


def test_no_toca_lo_que_no_es_de_archify(tmp_path):
    ruta = tmp_path / "otro.html"
    ruta.write_text("<html><head></head><body><p>hola</p></body></html>", encoding="utf-8")
    assert not marca.vestir(ruta, "es")


def test_fin_del_contenedor(html_crudo):
    pos = marca._fin_del_contenedor(html_crudo)
    assert pos > html_crudo.index('<div class="cards">')
    assert html_crudo[:pos].endswith("</div>")
    assert "<script" in html_crudo[pos:]


def test_las_fuentes_de_la_marca_estan_en_el_repositorio():
    for _, _, _, archivo in marca._TIPOGRAFIAS:
        assert (marca.FUENTES / archivo).is_file()
    assert "OFL" in (marca.FUENTES / "LICENCIA.md").read_text(encoding="utf-8")
