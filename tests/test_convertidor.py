# -*- coding: utf-8 -*-
"""Del modelo intermedio a la especificación de Archify, sin dibujar."""
from collections import Counter

import pytest

from conftest import RAIZ, TODOS, cargar
from flujo import convertidor
from flujo.convertidor import Grafo, MAX_COLUMNAS


def _partes(ruta_o_modelo):
    m = cargar(ruta_o_modelo) if not isinstance(ruta_o_modelo, dict) else ruta_o_modelo
    return m, convertidor.convertir(m)


def _por_id(spec):
    return {n["id"]: n for n in spec["nodes"]}


# ------------------------------------------------------------- reglas generales

@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_reglas_de_archify_en_cada_parte(ruta):
    m, resultado = _partes(ruta)
    for parte in resultado["partes"]:
        spec = parte["spec"]
        assert spec["schema_version"] == 2 and spec["diagram_type"] == "workflow"
        nodos = _por_id(spec)
        carriles = {c["id"] for c in spec["lanes"]}
        celdas = Counter((n["lane"], n["col"]) for n in spec["nodes"])
        assert max(celdas.values()) == 1, "dos nodos en la misma celda"
        for n in spec["nodes"]:
            assert 0 <= n["col"] < MAX_COLUMNAS
            assert n["lane"] in carriles
            assert n["width"] >= convertidor.ancho_necesario(n)
        for e in spec["edges"]:
            assert e["from"] in nodos and e["to"] in nodos
        anterior = -1
        for f in spec.get("phases", []):
            assert 0 <= f["fromCol"] <= f["toCol"] < MAX_COLUMNAS
            assert f["fromCol"] > anterior, "fases encimadas"
            anterior = f["toCol"]
        camino = spec.get("mainPath", [])
        aristas = {(e["from"], e["to"]) for e in spec["edges"]}
        for a, b in zip(camino, camino[1:]):
            assert (a, b) in aristas
            assert nodos[b]["col"] >= nodos[a]["col"]


@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_cada_paso_aparece_una_sola_vez(ruta):
    m, resultado = _partes(ruta)
    vistos = Counter(pid for parte in resultado["partes"] for pid in parte["pasos"])
    assert set(vistos) == {p["id"] for p in m["pasos"]}
    assert max(vistos.values()) == 1


@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_cada_conexion_se_dibuja_o_se_enlaza(ruta):
    m, resultado = _partes(ruta)
    assert resultado["avisos"] == []
    dibujadas = set()
    for parte in resultado["partes"]:
        for e in parte["spec"]["edges"]:
            dibujadas.add((e["from"], e["to"]))
    for c in m["conexiones"]:
        directa = (c["desde"], c["hacia"]) in dibujadas
        sale = any(d == c["desde"] and h.startswith("x-sigue-") for d, h in dibujadas)
        entra = any(h == c["hacia"] and d.startswith("x-viene-") for d, h in dibujadas)
        assert directa or (sale and entra), "falta la conexión %s -> %s" % (c["desde"], c["hacia"])


# ------------------------------------------------------------- el ejemplo

def test_ejemplo_cabe_en_un_dibujo(ejemplo):
    resultado = convertidor.convertir(ejemplo)
    assert len(resultado["partes"]) == 1
    spec = resultado["partes"][0]["spec"]
    assert spec["meta"]["title"] == "Del pedido al despacho"
    assert [c["label"] for c in spec["lanes"]] == ["Cliente", "Ventas", "Cartera", "Bodega"]
    assert [f["label"] for f in spec["phases"]] == ["Pedir", "Aprobar el crédito", "Despachar"]
    assert len(spec["nodes"]) == 10


def test_tipos_reinterpretados(ejemplo):
    nodos = _por_id(convertidor.convertir(ejemplo)["partes"][0]["spec"])
    assert nodos["tiene_cupo"]["type"] == "database"      # decisión
    assert nodos["copia_pedido"]["type"] == "security"    # donde duele
    assert nodos["envia_pedido"]["type"] == "external"    # quien espera, carril externo
    assert nodos["emite_factura"]["type"] == "backend"    # dentro del sistema
    assert nodos["despacha"]["type"] == "frontend"        # fuera del sistema


def test_textos_del_nodo(ejemplo):
    nodos = _por_id(convertidor.convertir(ejemplo)["partes"][0]["spec"])
    # El dolor va abajo, en la marca; la herramienta, cuando no duele.
    assert nodos["copia_pedido"]["tag"] == "se digita dos veces"
    assert nodos["envia_pedido"]["tag"] == "WhatsApp"
    assert nodos["emite_factura"]["tag"] == "sistema contable"
    assert nodos["tiene_cupo"]["label"] == "¿Tiene cupo y está al día?"
    assert "sublabel" not in nodos["tiene_cupo"]


def test_la_herramienta_no_se_repite_si_ya_esta_en_el_detalle():
    paso = {"titulo": "Avisa", "detalle": "por WhatsApp", "herramienta": "WhatsApp", "dolor": None}
    assert convertidor.textos_de_nodo(paso) == ("Avisa", "por WhatsApp", None)
    paso = {"titulo": "Avisa", "detalle": None, "herramienta": "WhatsApp", "dolor": "nadie responde"}
    assert convertidor.textos_de_nodo(paso) == ("Avisa", "WhatsApp", "nadie responde")


def test_decision_con_respuestas_y_vuelta(ejemplo):
    spec = convertidor.convertir(ejemplo)["partes"][0]["spec"]
    aristas = {(e["from"], e["to"]): e for e in spec["edges"]}
    assert aristas[("tiene_cupo", "arma_pedido")]["label"] == "Sí"
    assert aristas[("tiene_cupo", "retiene")]["label"] == "No"
    assert aristas[("tiene_cupo", "retiene")]["role"] == "branch"
    assert aristas[("paga_vencido", "tiene_cupo")]["role"] == "return"
    assert aristas[("paga_vencido", "tiene_cupo")]["variant"] == "dashed"


def test_camino_principal_sigue_la_rama_que_termina(ejemplo):
    camino = Grafo(ejemplo).camino_principal()
    assert camino == ["envia_pedido", "copia_pedido", "pide_revision", "tiene_cupo",
                      "arma_pedido", "emite_factura", "despacha", "recibe"]


def test_observaciones_y_preguntas_en_tarjetas(ejemplo):
    cards = convertidor.convertir(ejemplo)["partes"][0]["spec"]["cards"]
    assert [c["title"] for c in cards] == ["Dónde se pierde tiempo", "Riesgos", "Preguntas abiertas"]
    assert [c["dot"] for c in cards] == ["rose", "amber", "violet"]
    assert len(cards[2]["items"]) == 2


def test_leyenda_con_los_nombres_de_la_casa(ejemplo):
    entradas = convertidor.convertir(ejemplo)["partes"][0]["spec"]["meta"]["legend"]["entries"]
    assert entradas["security"]["label"] == "Donde duele"
    assert entradas["database"]["label"] == "Decisión"
    assert entradas["external"]["label"] == "Quien espera el resultado"


def test_misma_columna_mismo_ancho(ejemplo):
    spec = convertidor.convertir(ejemplo)["partes"][0]["spec"]
    por_col = {}
    for n in spec["nodes"]:
        por_col.setdefault(n["col"], set()).add(n["width"])
    assert all(len(anchos) == 1 for anchos in por_col.values())


def test_mismo_carril_sin_nada_en_medio_va_recto(ejemplo):
    spec = convertidor.convertir(ejemplo)["partes"][0]["spec"]
    aristas = {(e["from"], e["to"]): e for e in spec["edges"]}
    assert aristas[("copia_pedido", "pide_revision")].get("route") == "straight"
    assert "route" not in aristas[("pide_revision", "tiene_cupo")]


# ------------------------------------------------------------- columnas

def test_cada_fase_tiene_su_tramo(ejemplo):
    g = Grafo(ejemplo)
    orden = {f["id"]: i for i, f in enumerate(ejemplo["fases"])}
    col = convertidor.asignar_columnas(g, orden)
    aprobar = [col[p["id"]] for p in ejemplo["pasos"] if p["fase"] == "aprobar"]
    despachar = [col[p["id"]] for p in ejemplo["pasos"] if p["fase"] == "despachar"]
    assert max(aprobar) < min(despachar)


def test_la_compresion_no_pone_una_linea_vertical_sobre_otro_paso():
    # A (carril 0) -> B (carril 2) con C en el carril 1 en la columna de B:
    # juntar las columnas de A y B haría pasar la línea por encima de C.
    m = {
        "idioma": "es", "titulo": "Prueba", "objetivo": None, "fases": [], "observaciones": [],
        "preguntas_abiertas": [],
        "carriles": [{"id": x, "nombre": x, "externo": False} for x in ("a", "b", "c")],
        "pasos": [
            {"id": "p1", "tipo": "inicio", "carril": "a", "fase": None},
            {"id": "p2", "tipo": "tarea", "carril": "c", "fase": None},
            {"id": "p3", "tipo": "tarea", "carril": "b", "fase": None},
        ],
        "conexiones": [{"desde": "p1", "hacia": "p2", "etiqueta": None},
                       {"desde": "p1", "hacia": "p3", "etiqueta": None}],
    }
    g = Grafo(m)
    idx = {"p1": 0, "p2": 2, "p3": 1}
    col = convertidor.comprimir(g, {"p1": 0, "p2": 1, "p3": 1}, idx, max_columnas=1)
    assert col["p1"] != col["p2"], "la compresión dejó la línea p1 -> p2 cruzando p3"


def test_es_afirmativa():
    assert convertidor.es_afirmativa("Sí")
    assert convertidor.es_afirmativa("si, tiene cupo")
    assert convertidor.es_afirmativa("Yes")
    assert not convertidor.es_afirmativa("sin cupo")
    assert not convertidor.es_afirmativa("No")
    assert not convertidor.es_afirmativa(None)


# ------------------------------------------------------------- procesos largos

def test_proceso_largo_con_tres_decisiones_se_parte_con_enlaces():
    m, resultado = _partes(RAIZ / "tests" / "procesos" / "importacion-larga.json")
    partes = resultado["partes"]
    assert len(partes) >= 2
    assert sum(1 for p in m["pasos"] if p["tipo"] == "decision") == 3
    for k, parte in enumerate(partes, start=1):
        spec = parte["spec"]
        ids = [n["id"] for n in spec["nodes"]]
        assert spec["meta"]["title"].endswith("parte %d de %d" % (k, len(partes)))
        if k < len(partes):
            assert any(i.startswith("x-sigue-%d-" % (k + 1)) for i in ids)
        if k > 1:
            assert any(i.startswith("x-viene-%d-" % (k - 1)) for i in ids)
            assert min(n["col"] for n in spec["nodes"] if not n["id"].startswith("x-")) >= 1


def test_un_reproceso_no_queda_partido():
    for nombre in ("cierre-caja.json", "importacion-larga.json"):
        m, resultado = _partes(RAIZ / "tests" / "procesos" / nombre)
        parte_de = {pid: k for k, parte in enumerate(resultado["partes"]) for pid in parte["pasos"]}
        orden = {p["id"]: i for i, p in enumerate(m["pasos"])}
        for c in m["conexiones"]:
            if orden[c["hacia"]] <= orden[c["desde"]]:
                assert parte_de[c["desde"]] == parte_de[c["hacia"]], nombre


def test_un_solo_carril_largo_se_parte():
    m, resultado = _partes(RAIZ / "tests" / "procesos" / "cierre-caja.json")
    assert len(resultado["partes"]) >= 2


def test_proceso_en_ingles():
    m, resultado = _partes(RAIZ / "tests" / "procesos" / "incorporacion-en.json")
    spec = resultado["partes"][0]["spec"]
    assert spec["meta"]["legend"]["entries"]["database"]["label"] == "Decision"
    assert [c["title"] for c in spec["cards"]] == ["Where time is lost", "Open questions"]
