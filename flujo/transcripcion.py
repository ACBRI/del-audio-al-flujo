# -*- coding: utf-8 -*-
"""La orden `transcribir` (opcional): un audio a texto, en el computador de quien la usa.

    python transcribir.py nota-de-voz.m4a --salida mis-flujos/2026-10-14-pedido/relato.md

Usa faster-whisper con el modelo «small» en el procesador, sin tarjeta gráfica.
No viene instalado: se instala aparte (`pip install faster-whisper`) y la primera
vez descarga el modelo, unos 500 MB, a la caché del usuario. Después funciona
sin internet y el audio no sale del computador.

Lee mp3, m4a, wav, ogg, webm y casi cualquier otro formato de audio: faster-whisper
trae su propio decodificador, así que no hace falta instalar nada más.

Escribe un relato.md con la transcripción en párrafos, listo para que la IA
escriba el modelo intermedio y para que dibujar.py compare las citas.
"""
from __future__ import annotations

import argparse
import datetime
import platform
import sys
from pathlib import Path

FORMATOS = {".mp3", ".m4a", ".mp4", ".wav", ".ogg", ".oga", ".opus", ".webm", ".flac", ".aac", ".wma", ".amr"}
PAUSA_DE_PARRAFO = 1.5  # segundos de silencio que abren un párrafo nuevo
LARGO_DE_PARRAFO = 700  # caracteres; pasado esto, el párrafo se cierra en el siguiente punto


class FaltaFasterWhisper(RuntimeError):
    pass


def como_instalar() -> str:
    orden = "py -m pip install faster-whisper" if platform.system() == "Windows" else \
        "python3 -m pip install faster-whisper"
    return ("Para transcribir en este computador hace falta faster-whisper. Instálelo con:\n"
            "    %s\n"
            "La primera transcripción descarga el modelo «small» (unos 500 MB); después ya no "
            "hace falta internet." % orden)


def _duracion(segundos: float) -> str:
    segundos = int(round(segundos or 0))
    minutos, segundos = divmod(segundos, 60)
    return "%d min %02d s" % (minutos, segundos) if minutos else "%d s" % segundos


def parrafos(segmentos) -> list:
    """Agrupa los segmentos en párrafos: una pausa larga o un párrafo muy largo abren uno nuevo."""
    salida: list = []
    actual: list = []
    fin_anterior = None
    for s in segmentos:
        texto = (s.text or "").strip()
        if not texto:
            continue
        pausa = fin_anterior is not None and s.start - fin_anterior >= PAUSA_DE_PARRAFO
        largo = sum(len(x) + 1 for x in actual) >= LARGO_DE_PARRAFO and actual and actual[-1][-1:] in ".?!"
        if actual and (pausa or largo):
            salida.append(" ".join(actual))
            actual = []
        actual.append(texto)
        fin_anterior = s.end
    if actual:
        salida.append(" ".join(actual))
    return salida


def transcribir(ruta: Path, idioma: str = "es", modelo: str = "small", avance=None):
    """Devuelve (párrafos, información). Lanza FaltaFasterWhisper si no está instalado."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise FaltaFasterWhisper(str(error))
    motor = WhisperModel(modelo, device="cpu", compute_type="int8")
    segmentos, info = motor.transcribe(str(ruta), language=None if idioma == "auto" else idioma,
                                       vad_filter=True, beam_size=5)

    def con_avance(lista):
        siguiente = 60.0
        for s in lista:
            if avance and s.end >= siguiente:
                avance(s.end, getattr(info, "duration", 0) or 0)
                siguiente = s.end + 60.0
            yield s

    return parrafos(con_avance(segmentos)), info


def documento(nombre: str, lista: list, info, modelo: str, hoy=None) -> str:
    hoy = hoy or datetime.date.today()
    idioma = getattr(info, "language", None) or "?"
    cabecera = ("# Relato: %s\n\n"
                "Transcrito en este computador con faster-whisper (modelo %s) el %s. "
                "Duración del audio: %s. Idioma: %s.\n\n"
                "Revise los nombres propios y las cifras antes de dibujar: es donde más se equivoca "
                "una transcripción automática.\n\n---\n\n"
                % (nombre, modelo, hoy.isoformat(), _duracion(getattr(info, "duration", 0)), idioma))
    return cabecera + "\n\n".join(lista) + "\n"


def _destino_libre(ruta: Path) -> Path:
    if not ruta.exists():
        return ruta
    n = 2
    while True:
        candidata = ruta.with_name("%s-%d%s" % (ruta.stem, n, ruta.suffix))
        if not candidata.exists():
            return candidata
        n += 1


def main(argv=None) -> int:
    from .cli import preparar_consola
    preparar_consola()
    parser = argparse.ArgumentParser(
        prog="transcribir.py",
        description="Transcribe un audio en este computador con faster-whisper y lo guarda como relato.md.")
    parser.add_argument("audio", help="archivo de audio: mp3, m4a, wav, ogg, webm...")
    parser.add_argument("--idioma", default="es", help="código del idioma del audio (es, en...) o auto")
    parser.add_argument("--modelo", default="small",
                        help="tamaño del modelo: tiny, base, small (por defecto), medium. Más grande es "
                             "más preciso y más lento.")
    parser.add_argument("--salida", help="archivo .md de salida (por defecto, relato.md junto al audio)")
    args = parser.parse_args(argv)

    audio = Path(args.audio).expanduser()
    if not audio.is_file():
        print("No encontré el audio %s." % audio)
        return 1
    if audio.suffix.lower() not in FORMATOS:
        print("Aviso: %s no parece un audio conocido; lo intento de todas formas." % audio.name)
    destino = Path(args.salida).expanduser() if args.salida else audio.with_name("relato.md")
    if destino.suffix.lower() != ".md":
        destino = destino / "relato.md" if (destino.is_dir() or not destino.suffix) else destino.with_suffix(".md")
    destino = _destino_libre(destino)

    print("Transcribiendo %s con el modelo «%s» en el procesador." % (audio.name, args.modelo))
    print("Si es la primera vez, antes se descarga el modelo (unos 500 MB). Después, un audio de diez "
          "minutos tarda unos minutos; cuántos depende del computador.")

    def avance(van, total):
        if total:
            print("  van %s de %s" % (_duracion(van), _duracion(total)))

    try:
        lista, info = transcribir(audio, args.idioma, args.modelo, avance)
    except FaltaFasterWhisper:
        print(como_instalar())
        return 2
    except Exception as error:  # un audio dañado o un formato que el decodificador no lee
        print("No pude transcribir %s: %s" % (audio.name, error))
        return 1
    if not lista:
        print("La transcripción quedó vacía: ¿el audio tiene voz? Revise el volumen o pruebe otro archivo.")
        return 1
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as salida:
        salida.write(documento(audio.name, lista, info, args.modelo))
    print("Listo: %s (%d párrafos)." % (destino.resolve(), len(lista)))
    return 0
