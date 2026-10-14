# -*- coding: utf-8 -*-
import copy
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from flujo import archify  # noqa: E402

PROCESOS = sorted((RAIZ / "tests" / "procesos").glob("*.json"))
EJEMPLO = RAIZ / "ejemplos" / "pedido-a-despacho" / "proceso.json"
RELATO = RAIZ / "ejemplos" / "pedido-a-despacho" / "relato.md"
TODOS = PROCESOS + [EJEMPLO]


def cargar(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


@pytest.fixture
def ejemplo() -> dict:
    return copy.deepcopy(cargar(EJEMPLO))


@pytest.fixture(scope="session")
def node():
    ruta, version = archify.buscar_node()
    if not ruta:
        pytest.skip("Node 18 o más nuevo no está disponible: %s" % version)
    return ruta


@pytest.fixture(autouse=True)
def sin_navegador(monkeypatch):
    """Ninguna prueba abre el navegador."""
    monkeypatch.setenv("FLUJO_NO_ABRIR", "1")
