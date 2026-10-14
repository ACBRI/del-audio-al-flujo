# -*- coding: utf-8 -*-
"""La transcripción local, con faster-whisper simulado: aquí no se descarga ningún modelo."""
import datetime
import sys
import types

import pytest

from flujo import transcripcion


class Segmento:
    def __init__(self, inicio, fin, texto):
        self.start, self.end, self.text = inicio, fin, texto


class Info:
    language = "es"
    language_probability = 0.98
    duration = 130.0


SEGMENTOS = [
    Segmento(0.0, 4.0, " Bueno, le cuento cómo funciona hoy un pedido."),
    Segmento(4.2, 9.0, " El cliente nos escribe por WhatsApp."),
    Segmento(12.0, 18.0, " Después la vendedora copia el pedido a una hoja."),  # pausa de 3 s
    Segmento(18.1, 70.0, " En Cartera miran si el cliente tiene cupo."),
    Segmento(70.2, 125.0, " Luego bodega despacha."),
]


@pytest.fixture
def falso_whisper(monkeypatch):
    llamadas = {}

    class Modelo:
        def __init__(self, tamano, device, compute_type, **otros):
            llamadas.update(tamano=tamano, device=device, compute_type=compute_type)

        def transcribe(self, ruta, language=None, vad_filter=False, beam_size=1):
            llamadas.update(ruta=ruta, language=language, vad_filter=vad_filter)
            return iter(SEGMENTOS), Info()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Modelo))
    return llamadas


def test_parrafos_por_pausas():
    parrafos = transcripcion.parrafos(SEGMENTOS)
    assert len(parrafos) == 2
    assert parrafos[0] == "Bueno, le cuento cómo funciona hoy un pedido. El cliente nos escribe por WhatsApp."


def test_transcribe_en_el_procesador(falso_whisper, tmp_path):
    audio = tmp_path / "nota.m4a"
    audio.write_bytes(b"\x00")
    avances = []
    parrafos, info = transcripcion.transcribir(audio, "es", "small", lambda van, total: avances.append(van))
    assert falso_whisper["tamano"] == "small"
    assert falso_whisper["device"] == "cpu" and falso_whisper["compute_type"] == "int8"
    assert falso_whisper["language"] == "es" and falso_whisper["vad_filter"] is True
    assert len(parrafos) == 2 and info.duration == 130.0
    assert avances == [70.0, 125.0][:len(avances)] and avances


def test_idioma_automatico(falso_whisper, tmp_path):
    audio = tmp_path / "nota.mp3"
    audio.write_bytes(b"\x00")
    transcripcion.transcribir(audio, "auto")
    assert falso_whisper["language"] is None


def test_documento_en_markdown():
    texto = transcripcion.documento("nota.m4a", ["Uno.", "Dos."], Info(), "small", datetime.date(2026, 10, 14))
    assert texto.startswith("# Relato: nota.m4a\n")
    assert "faster-whisper (modelo small) el 2026-10-14" in texto
    assert "Duración del audio: 2 min 10 s" in texto
    assert texto.endswith("Uno.\n\nDos.\n")


def test_orden_completa_no_pisa_un_relato_existente(falso_whisper, tmp_path, capsys):
    audio = tmp_path / "nota.webm"
    audio.write_bytes(b"\x00")
    (tmp_path / "relato.md").write_text("anterior", encoding="utf-8")
    codigo = transcripcion.main([str(audio)])
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    assert (tmp_path / "relato.md").read_text(encoding="utf-8") == "anterior"
    nuevo = (tmp_path / "relato-2.md").read_text(encoding="utf-8")
    assert "El cliente nos escribe por WhatsApp." in nuevo
    assert "500 MB" in salida


def test_salida_en_una_carpeta(falso_whisper, tmp_path, capsys):
    audio = tmp_path / "nota.wav"
    audio.write_bytes(b"\x00")
    destino = tmp_path / "mis-flujos" / "pedido"
    destino.mkdir(parents=True)
    assert transcripcion.main([str(audio), "--salida", str(destino)]) == 0
    assert (destino / "relato.md").is_file()


def test_sin_faster_whisper_explica_como_instalarlo(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)   # import falla
    audio = tmp_path / "nota.ogg"
    audio.write_bytes(b"\x00")
    assert transcripcion.main([str(audio)]) == 2
    salida = capsys.readouterr().out
    assert "pip install faster-whisper" in salida


def test_audio_que_no_existe(tmp_path, capsys):
    assert transcripcion.main([str(tmp_path / "no-esta.mp3")]) == 1
