# -*- coding: utf-8 -*-
"""Los textos que la herramienta pone en el dibujo, en español y en inglés.

Lo que dice el relato lo escribe la IA en el modelo; aquí solo está lo que la
herramienta agrega por su cuenta: la leyenda, los títulos de las tarjetas, los
enlaces entre partes y el pie.
"""
from __future__ import annotations

TEXTOS = {
    "es": {
        # Los tipos de nodo de Archify, leídos como se leen en un proceso.
        "leyenda": {
            "frontend": "Fuera del sistema",
            "backend": "Dentro del sistema",
            "security": "Donde duele",
            "external": "Quien espera el resultado",
            "database": "Decisión",
            "messagebus": "Enlace entre partes",
        },
        "tarjeta_tiempo": "Dónde se pierde tiempo",
        "tarjeta_riesgo": "Riesgos",
        "tarjeta_otra": "Otras observaciones",
        "tarjeta_preguntas": "Preguntas abiertas",
        "titulo_parte": "{titulo} · parte {k} de {n}",
        "sigue": "Sigue en la parte {n}",
        "viene": "Viene de la parte {n}",
        "varios_pasos": "{n} pasos",
        "parte_de": "Parte {k} de {n}",
        "ir_a_parte": "Ver la parte {n}",
        "evidencia_titulo": "De dónde sale cada paso",
        "evidencia_nota": "Cada paso del dibujo se apoya en una frase del relato. Si alguna no dice lo que el dibujo muestra, corrija el modelo y vuelva a dibujar.",
        "evidencia_paso": "Paso",
        "evidencia_cita": "Lo que se dijo",
        "del_relato": "Del relato",
        "pie_autor": "Hecho por Andrés Briñez",
        "pie_herramienta": "Dibujado con «Del audio al flujo» y Archify (licencia MIT)",
    },
    "en": {
        "leyenda": {
            "frontend": "Outside any system",
            "backend": "Inside a system",
            "security": "Where it hurts",
            "external": "Waiting on the result",
            "database": "Decision",
            "messagebus": "Link between parts",
        },
        "tarjeta_tiempo": "Where time is lost",
        "tarjeta_riesgo": "Risks",
        "tarjeta_otra": "Other notes",
        "tarjeta_preguntas": "Open questions",
        "titulo_parte": "{titulo} · part {k} of {n}",
        "sigue": "Continues in part {n}",
        "viene": "Comes from part {n}",
        "varios_pasos": "{n} steps",
        "parte_de": "Part {k} of {n}",
        "ir_a_parte": "See part {n}",
        "evidencia_titulo": "Where each step comes from",
        "evidencia_nota": "Every step in the drawing rests on a sentence from the account. If one does not say what the drawing shows, fix the model and draw again.",
        "evidencia_paso": "Step",
        "evidencia_cita": "What was said",
        "del_relato": "From the account",
        "pie_autor": "Made by Andrés Briñez",
        "pie_herramienta": "Drawn with «Del audio al flujo» and Archify (MIT license)",
    },
}


def textos(idioma: str) -> dict:
    return TEXTOS.get(idioma, TEXTOS["es"])
