# -*- coding: utf-8 -*-
"""La orden `dibujar` de punta a punta: modelo -> Archify -> marca -> idioma -> HTML."""
import json
import re
import shutil
from html import unescape

import pytest

from conftest import EJEMPLO, RAIZ, RELATO, cargar
from flujo import archify, cli


@pytest.fixture
def carpeta(tmp_path):
    """El ejemplo copiado a una carpeta temporal, con su relato."""
    shutil.copy(EJEMPLO, tmp_path / "proceso.json")
    shutil.copy(RELATO, tmp_path / "relato.md")
    return tmp_path


def _correr(capsys, *argumentos):
    codigo = cli.main([str(a) for a in argumentos])
    return codigo, capsys.readouterr().out


def test_ejemplo_de_punta_a_punta(node, carpeta, capsys):
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir")
    assert codigo == 0, salida
    assert "Listo: Del pedido al despacho" in salida
    assert "calidad showcase" in salida
    assert "Avisos:" not in salida   # todas las citas salen del relato
    html = (carpeta / "flujo.html").read_text(encoding="utf-8")
    assert (carpeta / "flujo.archify.json").is_file()

    # La piel de la marca, con sus tipografías dentro del archivo.
    assert 'data-piel="brinez"' in html
    piel = re.search(r'<style data-piel="brinez">([\s\S]*?)</style>', html).group(1)
    assert piel.count("@font-face { font-family: 'Literata'") == 2
    # Las del dibujo van en el bloque que Archify copia en cada exportación.
    fuentes = re.search(r'<style id="archify-fonts">([\s\S]*?)</style>', html).group(1)
    assert fuentes.count("@font-face { font-family: 'Archivo'") == 1
    assert fuentes.count("@font-face { font-family: 'IBM Plex Mono'") == 2
    assert "#1C1A2E" in html and "#B5430F" in html
    assert "fonts.googleapis" not in html

    # El visor en español.
    assert '<html lang="es"' in html
    assert ">Leyenda<" in html and ">Legend<" not in html
    assert "Exportar" in html and "Claro" in html

    # Decisión con rombo; inicio y fin con su símbolo.
    assert html.count('d="M8 1.8 14.2 8 8 14.2 1.8 8Z"') == 1
    assert 'd="m6.9 5.3 3.7 2.7-3.7 2.7Z"' in html

    # Cada paso con su cita: en el texto al pasar el cursor y en el anexo.
    texto = unescape(html)
    for paso in cargar(EJEMPLO)["pasos"]:
        assert "Del relato: «%s»" % paso["cita"] in texto
        assert "<q>%s</q>" % paso["cita"] in texto
    assert "De dónde sale cada paso" in texto
    assert "Hecho por Andrés Briñez · andresbrinez.com" in texto
    # El anexo queda fuera del contenedor del visor, antes de su programa.
    assert html.index('class="ab-anexo"') > html.index('<div class="cards">')


def test_salida_en_json_para_agentes(node, carpeta, capsys):
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir", "--json")
    assert codigo == 0
    informe = json.loads(salida)
    assert informe["ok"] and informe["calidad"] == ["showcase"]
    assert informe["archivos"][0].endswith("flujo.html")
    assert len(informe["preguntas_abiertas"]) == 2


def test_modelo_con_errores_no_dibuja(carpeta, capsys):
    m = cargar(carpeta / "proceso.json")
    m["pasos"][0]["carril"] = "nadie"
    (carpeta / "proceso.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir")
    assert codigo == 1
    assert "carril «nadie»" in salida
    assert not (carpeta / "flujo.html").exists()


def test_sin_relato_avisa_que_no_comprobo_las_citas(node, carpeta, capsys):
    (carpeta / "relato.md").unlink()
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir")
    assert codigo == 0
    assert "no pude comprobar que las citas salgan del relato" in salida


def test_cita_que_no_esta_en_el_relato(node, carpeta, capsys):
    m = cargar(carpeta / "proceso.json")
    m["pasos"][3]["cita"] = "Cartera aprueba en cinco minutos."
    (carpeta / "proceso.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir")
    assert codigo == 0
    assert "La cita del paso «tiene_cupo» no aparece tal cual en el relato" in salida


def test_sin_node_explica_como_instalarlo(carpeta, capsys, monkeypatch):
    monkeypatch.setattr(archify, "buscar_node", lambda: (None, "No encontré Node.js en este computador."))
    codigo, salida = _correr(capsys, carpeta / "proceso.json", "--no-abrir")
    assert codigo == 2
    assert "No encontré Node.js" in salida and "nodejs.org" in salida


def test_proceso_en_ingles(node, tmp_path, capsys):
    ruta = RAIZ / "tests" / "procesos" / "incorporacion-en.json"
    codigo, _ = _correr(capsys, ruta, "--salida", tmp_path, "--no-abrir")
    assert codigo == 0
    html = (tmp_path / "flujo.html").read_text(encoding="utf-8")
    assert '<html lang="en"' in html
    assert ">Legend<" in html and "Export" in html
    assert "Where it hurts" in html or "Waiting on the result" in html
    assert "Where each step comes from" in html
    assert "Made by Andrés Briñez" in unescape(html)


def test_proceso_largo_en_partes_enlazadas(node, tmp_path, capsys):
    ruta = RAIZ / "tests" / "procesos" / "cierre-caja.json"
    codigo, salida = _correr(capsys, ruta, "--salida", tmp_path, "--no-abrir")
    assert codigo == 0
    archivos = sorted(tmp_path.glob("flujo-parte-*.html"))
    assert len(archivos) >= 2
    assert "partes enlazadas" in salida
    for i, archivo in enumerate(archivos, start=1):
        html = archivo.read_text(encoding="utf-8")
        otros = {a.name for a in archivos if a != archivo}
        enlaces = set(re.findall(r'class="ab-parte" href="([^"]+)"', html))
        assert otros <= enlaces, "la parte %d no enlaza con las demás" % i


def test_comprobar(node, capsys):
    codigo, salida = _correr(capsys, "--comprobar")
    assert codigo == 0
    assert "[ok] Python" in salida and "[ok] Node" in salida and "Todo listo." in salida


def test_sin_argumentos_muestra_la_ayuda(capsys):
    codigo, salida = _correr(capsys)
    assert codigo == 1
    assert "proceso.json" in salida
