# -*- coding: utf-8 -*-
"""Coherencia del modelo y comprobación de las citas contra el relato."""
import json

import pytest

from conftest import EJEMPLO, RELATO, TODOS, cargar
from flujo import modelo


@pytest.mark.parametrize("ruta", TODOS, ids=lambda r: r.stem)
def test_los_procesos_de_prueba_no_tienen_errores(ruta):
    errores, avisos = modelo.revisar(cargar(ruta))
    assert errores == []
    assert avisos == []


def test_lee_json_con_marca_bom(tmp_path):
    ruta = tmp_path / "proceso.json"
    ruta.write_bytes(b"\xef\xbb\xbf" + EJEMPLO.read_bytes())
    dato, errores = modelo.leer(ruta)
    assert errores == []
    assert dato["titulo"] == "Del pedido al despacho"


def test_json_roto_explica_linea_y_columna(tmp_path):
    ruta = tmp_path / "proceso.json"
    ruta.write_text('{"version": 1,\n "titulo": }', encoding="utf-8")
    dato, errores = modelo.leer(ruta)
    assert dato is None
    assert "línea 2" in errores[0]


def test_archivo_que_no_existe(tmp_path):
    dato, errores = modelo.leer(tmp_path / "no-esta.json")
    assert dato is None and "No encontré" in errores[0]


def _errores(ejemplo, cambio):
    cambio(ejemplo)
    errores, _ = modelo.revisar(ejemplo)
    return " ".join(errores)


def test_carril_que_no_existe(ejemplo):
    texto = _errores(ejemplo, lambda m: m["pasos"][1].update(carril="logistica"))
    assert "carril «logistica»" in texto


def test_fase_que_no_existe(ejemplo):
    assert "fase «cobrar»" in _errores(ejemplo, lambda m: m["pasos"][1].update(fase="cobrar"))


def test_conexion_a_un_paso_que_no_existe(ejemplo):
    texto = _errores(ejemplo, lambda m: m["conexiones"].append({"desde": "recibe", "hacia": "cobra", "etiqueta": None}))
    assert "«cobra», que no existe" in texto


def test_conexion_de_un_paso_a_si_mismo(ejemplo):
    texto = _errores(ejemplo, lambda m: m["conexiones"].append(
        {"desde": "despacha", "hacia": "despacha", "etiqueta": None}))
    assert "a sí mismo" in texto


def test_ids_repetidos(ejemplo):
    texto = _errores(ejemplo, lambda m: m["pasos"][2].update(id="copia_pedido"))
    assert "con el id «copia_pedido»" in texto


def test_conexion_repetida(ejemplo):
    texto = _errores(ejemplo, lambda m: m["conexiones"].append(dict(m["conexiones"][0])))
    assert "repetida" in texto


def test_decision_con_una_sola_salida(ejemplo):
    def quitar_no(m):
        m["conexiones"] = [c for c in m["conexiones"] if c["etiqueta"] != "No"]
    texto = _errores(ejemplo, quitar_no)
    assert "La decisión «tiene_cupo» necesita al menos dos salidas" in texto


def test_decision_sin_etiquetas(ejemplo):
    def sin_etiqueta(m):
        for c in m["conexiones"]:
            if c["desde"] == "tiene_cupo":
                c["etiqueta"] = None
    assert "necesitan etiqueta" in _errores(ejemplo, sin_etiqueta)


def test_decision_con_etiquetas_iguales(ejemplo):
    def iguales(m):
        for c in m["conexiones"]:
            if c["desde"] == "tiene_cupo":
                c["etiqueta"] = "Sí"
    assert "misma etiqueta" in _errores(ejemplo, iguales)


def test_paso_suelto(ejemplo):
    def suelto(m):
        paso = dict(m["pasos"][-1], id="suelto")
        m["pasos"].append(paso)
    assert "«suelto» no tiene conexiones" in _errores(ejemplo, suelto)


def test_avisos_de_carril_vacio_y_paso_inalcanzable(ejemplo):
    ejemplo["carriles"].append({"id": "gerencia", "nombre": "Gerencia", "externo": False})
    ejemplo["pasos"].append(dict(ejemplo["pasos"][-1], id="aparte", tipo="tarea"))
    ejemplo["conexiones"].append({"desde": "aparte", "hacia": "recibe", "etiqueta": None})
    errores, avisos = modelo.revisar(ejemplo)
    assert errores == []
    assert any("Gerencia" in a for a in avisos)
    assert any("«aparte»" in a and "No se llega" in a for a in avisos)


def test_las_citas_del_ejemplo_salen_del_relato(ejemplo):
    assert modelo.revisar_citas(ejemplo, RELATO.read_text(encoding="utf-8")) == []


def test_una_cita_inventada_da_aviso(ejemplo):
    ejemplo["pasos"][3]["cita"] = "Cartera aprueba todo en el sistema en cinco minutos."
    avisos = modelo.revisar_citas(ejemplo, RELATO.read_text(encoding="utf-8"))
    assert len(avisos) == 1 and "«tiene_cupo»" in avisos[0]


def test_la_cita_tolera_mayusculas_puntuacion_y_saltos():
    relato = "El cliente nos escribe por WhatsApp,\ncon lo que necesita."
    assert modelo.esta_en("el cliente nos escribe por whatsapp con lo que necesita", modelo.normalizar(relato))
    assert modelo.esta_en("«El cliente nos escribe... lo que necesita»", modelo.normalizar(relato))
    assert not modelo.esta_en("lo que necesita... el cliente", modelo.normalizar(relato))


def test_resumen(ejemplo):
    assert modelo.resumen(ejemplo) == "10 pasos, 4 carriles, 1 decisión, 3 puntos de dolor"


def test_el_esquema_se_lee_en_utf8():
    texto = modelo.RUTA_ESQUEMA.read_text(encoding="utf-8")
    assert "«Del pedido al despacho»" in texto
    json.loads(texto)
