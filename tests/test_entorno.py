# -*- coding: utf-8 -*-
"""Dónde se busca Node en Windows, macOS y Linux, sin depender del computador que corre la prueba."""
from pathlib import Path

from flujo import archify


def test_la_variable_flujo_node_va_primero(monkeypatch, tmp_path):
    propio = tmp_path / "node"
    monkeypatch.setenv("FLUJO_NODE", str(propio))
    assert archify.candidatos_node()[0] == propio


def test_rutas_de_windows(monkeypatch):
    monkeypatch.setattr(archify.platform, "system", lambda: "Windows")
    monkeypatch.setattr(archify.shutil, "which", lambda nombre: None)
    monkeypatch.delenv("FLUJO_NODE", raising=False)
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\ana\AppData\Local")
    rutas = [str(r).replace("\\", "/") for r in archify.candidatos_node()]
    assert any(r.endswith("Program Files/nodejs/node.exe") for r in rutas)
    assert any(r.endswith("AppData/Local/Programs/nodejs/node.exe") for r in rutas)


def test_rutas_de_macos(monkeypatch):
    monkeypatch.setattr(archify.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(archify.shutil, "which", lambda nombre: None)
    monkeypatch.delenv("FLUJO_NODE", raising=False)
    rutas = archify.candidatos_node()
    assert Path("/opt/homebrew/bin/node") in rutas
    assert Path("/usr/local/bin/node") in rutas


def test_node_viejo_no_sirve(monkeypatch, tmp_path):
    viejo = tmp_path / "node"
    viejo.write_text("")
    monkeypatch.setattr(archify, "candidatos_node", lambda: [viejo])
    monkeypatch.setattr(archify, "version_de_node", lambda ruta: (16, 20, 2))
    ruta, motivo = archify.buscar_node()
    assert ruta is None
    assert "16.20.2" in motivo and "18" in motivo


def test_sin_node(monkeypatch):
    monkeypatch.setattr(archify, "candidatos_node", lambda: [])
    ruta, motivo = archify.buscar_node()
    assert ruta is None and "No encontré Node.js" in motivo


def test_instrucciones_por_sistema(monkeypatch):
    for sistema, esperado in (("Windows", "winget"), ("Darwin", "brew install node"), ("Linux", "gestor de paquetes")):
        monkeypatch.setattr(archify.platform, "system", lambda s=sistema: s)
        assert esperado in archify.como_instalar_node()


def test_lee_la_version():
    assert archify._version("v22.16.0\n") == (22, 16, 0)
    assert archify._version("basura") is None
