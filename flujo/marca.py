# -*- coding: utf-8 -*-
"""La piel de la marca sobre el HTML que entrega Archify.

Archify no expone paleta: trae cuatro presentaciones cerradas y un interruptor de
claro y oscuro. Pero todo su color sale de variables CSS declaradas en un solo
sitio, y la licencia es MIT, así que la piel se pone encima sin tocar el dibujo:
se añade un bloque de estilos después del suyo que redefine esas variables con
la paleta «Sabana y candela» y las tres tipografías de la casa.

Dos detalles de cascada. El bloque va justo antes de `</head>`, después de todos
los estilos del visor, para ganar por orden de aparición. Y los selectores llevan
`:root[data-preset]` para ganar también a las presentaciones alternativas, que el
lector puede elegir desde el visor.

A diferencia del sitio, aquí las tipografías van dentro del archivo, en base64:
el HTML se descarga y se comparte, y tiene que verse igual sin conexión.

Los tipos de nodo se leen así (ver convertidor.py):
    frontend    fuera del sistema            sabana
    backend     dentro del sistema           morichal
    security    donde duele                  candela
    external    quien espera el resultado    tierra suave
    database    decisión (con rombo)         noche
    messagebus  enlace entre partes          bruma, punteado

Además de la paleta, la piel hace cuatro cosas que el visor no trae:
- muestra la línea inferior de cada nodo (la herramienta o el dolor) sin tener
  que acercar el dibujo;
- cambia el símbolo de las decisiones por un rombo y marca el inicio y el fin;
- agrega a cada nodo, al pasar el cursor, la frase del relato que lo respalda,
  y al pie del dibujo la lista completa de esas frases;
- firma el archivo con un pie discreto.

Adaptado del código del sitio andresbrinez.com, del mismo autor.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from xml.sax.saxutils import escape

from . import idioma
from .textos import textos

RECURSOS = Path(__file__).resolve().parent / "recursos"
FUENTES = RECURSOS / "fuentes"
SELLO = 'data-piel="brinez"'

# (familia, estilo, pesos que cubre, archivo). Archivo y Literata son variables.
# Las de peso fijo declaran un rango para que el navegador no invente una
# negrita: los títulos de carril y de leyenda piden 600 y 650.
#
# Las del dibujo (Archivo y Plex Mono) van dentro del bloque `archify-fonts`
# del visor: es el que Archify copia en cada SVG y PNG que exporta, así que la
# imagen descargada lleva las mismas letras que la pantalla. Literata solo se
# usa en la página, fuera del dibujo.
_DEL_DIBUJO = (
    ("Archivo", "normal", "100 900", "archivo-latin.woff2"),
    ("IBM Plex Mono", "normal", "300 450", "plex-mono-400-latin.woff2"),
    ("IBM Plex Mono", "normal", "451 800", "plex-mono-500-latin.woff2"),
)
_DE_LA_PAGINA = (
    ("Literata", "normal", "400 900", "literata-400-latin.woff2"),
    ("Literata", "italic", "400 700", "literata-400-cursiva-latin.woff2"),
)
_TIPOGRAFIAS = _DEL_DIBUJO + _DE_LA_PAGINA
_BLOQUE_FUENTES = re.compile(r'(<style id="archify-fonts">)([\s\S]*?)(</style>)')


def _fuentes_css(tipografias=_TIPOGRAFIAS) -> str:
    reglas = []
    for familia, estilo, peso, archivo in tipografias:
        datos = base64.b64encode((FUENTES / archivo).read_bytes()).decode("ascii")
        reglas.append("@font-face { font-family: '%s'; font-style: %s; font-weight: %s; font-display: swap;\n"
                      "  src: url(data:font/woff2;base64,%s) format('woff2'); }" % (familia, estilo, peso, datos))
    return "\n".join(reglas)


PALETA = """
/* ---- claro: el papel de la casa ---- */
:root,
:root[data-theme="light"],
:root[data-preset][data-theme="light"] {
  --bg: #F3EFE2;
  --grid: #E6DFD0;
  --text: #27201B;
  --text-muted: #6E6156;
  --text-dim: #9A9086;
  --text-faint: #B4A99B;
  --panel: rgba(250, 248, 241, .72);
  --panel-border: #DED7C8;
  --lane-fill: rgba(250, 248, 241, .55);
  --lane-stroke: #DED7C8;
  --arrow: #8C8073;
  --arrow-emphasis: #B5430F;
  --mask: #F3EFE2;

  --frontend-fill: rgba(195, 154, 63, .14);   --frontend-stroke: #7A5E1F;
  --backend-fill: rgba(47, 95, 58, .12);      --backend-stroke: #2F5F3A;
  --security-fill: rgba(212, 88, 27, .13);    --security-stroke: #B5430F;
  --external-fill: rgba(110, 97, 86, .10);    --external-stroke: #6E6156;
  --cloud-fill: rgba(195, 154, 63, .18);      --cloud-stroke: #A8802C;
  --database-fill: rgba(28, 26, 46, .08);     --database-stroke: #3F3A61;
  --messagebus-fill: rgba(110, 97, 86, .04);  --messagebus-stroke: #9A9086;

  --toolbar-bg: rgba(250, 248, 241, .88);
  --toolbar-border: #DED7C8;
  --toolbar-text: #27201B;
  --toolbar-hover: rgba(243, 239, 226, .96);
  --toolbar-menu-bg: #FAF8F1;

  --ab-noche: #1C1A2E;
  --ab-sobre-noche: #EFE9DC;
  --ab-candela-tinta: #B5430F;
}
/* ---- oscuro: la noche llanera ---- */
:root[data-theme="dark"],
:root[data-preset][data-theme="dark"] {
  --bg: #1C1A2E;
  --grid: #292640;
  --text: #EFE9DC;
  --text-muted: rgba(239, 233, 220, .68);
  --text-dim: rgba(239, 233, 220, .44);
  --text-faint: rgba(239, 233, 220, .55);
  --panel: rgba(35, 33, 58, .72);
  --panel-border: #35314F;
  --lane-fill: rgba(239, 233, 220, .045);
  --lane-stroke: #3A3558;
  --arrow: rgba(239, 233, 220, .5);
  --arrow-emphasis: #F07A3B;
  --mask: #1C1A2E;

  --frontend-fill: rgba(195, 154, 63, .18);   --frontend-stroke: #D8B25C;
  --backend-fill: rgba(47, 95, 58, .24);      --backend-stroke: #7FBA8D;
  --security-fill: rgba(212, 88, 27, .20);    --security-stroke: #F07A3B;
  --external-fill: rgba(239, 233, 220, .07);  --external-stroke: rgba(239, 233, 220, .6);
  --cloud-fill: rgba(195, 154, 63, .20);      --cloud-stroke: #E0C078;
  --database-fill: rgba(122, 114, 175, .18);  --database-stroke: #9990D8;
  --messagebus-fill: rgba(239, 233, 220, .03); --messagebus-stroke: rgba(239, 233, 220, .45);

  --toolbar-bg: rgba(28, 26, 46, .86);
  --toolbar-border: #3A3558;
  --toolbar-text: #EFE9DC;
  --toolbar-hover: rgba(28, 26, 46, .96);
  --toolbar-menu-bg: #232042;

  --ab-noche: #121120;
  --ab-sobre-noche: #EFE9DC;
  --ab-candela-tinta: #F07A3B;
}
"""

ESTILOS = """
/* ---- tipografía: Archivo en titulares, Literata en lectura, Plex Mono en el aparato ---- */
:root body { font-family: 'Literata', Georgia, 'Times New Roman', serif; }
:root h1, :root h2, :root h3, :root [class*="title"] {
  font-family: 'Archivo', 'Helvetica Neue', Arial, sans-serif; letter-spacing: -.01em; }
/* Cada regla del dibujo va dos veces: con :root gana en la página; sin él se
   aplica también en el SVG exportado, donde la raíz es el propio <svg>. */
:root svg text, svg text { font-family: 'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace; }
/* El nombre de cada paso es un titular: Archivo. Es más angosta que la letra
   monoespaciada con que Archify mide, así que siempre cabe con aire. */
:root svg text[data-node-label], svg text[data-node-label] {
  font-family: 'Archivo', 'Helvetica Neue', Arial, sans-serif; font-weight: 600; letter-spacing: 0; }
:root [class*="toolbar"], :root [class*="legend"], :root [class*="tag"], :root [class*="badge"],
:root .subtitle {
  font-family: 'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace; }
:root .card { border-radius: 2px; box-shadow: none; background: var(--panel); }
:root .card h3 { font-size: .95rem; }
:root .card ul { font-family: 'Literata', Georgia, serif; font-size: .9rem; line-height: 1.5; }

/* La línea inferior de cada nodo dice con qué se hace el paso o qué duele en
   él. El visor la guarda para cuando se acerca el dibujo; aquí se lee siempre. */
.diagram-container[data-detail-level="read"] svg [data-detail="fine"] { opacity: 1; pointer-events: auto; }

/* Enlaces entre partes: punteados, sin peso. */
:root svg .c-messagebus { stroke-dasharray: 4 3; }

/* ---- anexo: las citas, la navegación entre partes y el pie ---- */
.ab-parte { margin-left: .75rem; font: 500 .72rem/1 'IBM Plex Mono', Consolas, monospace;
  color: var(--ab-candela-tinta); text-decoration: none; border: 1px solid currentColor;
  border-radius: 2px; padding: .35rem .55rem; white-space: nowrap; }
.ab-parte:hover { text-decoration: underline; }
.ab-anexo { width: 100%; max-width: var(--archify-reader-width, 1440px); margin: 1.5rem auto 0;
  color: var(--text); }
.ab-partes { margin: 0 0 1rem; font: 400 .78rem/2 'IBM Plex Mono', Consolas, monospace; color: var(--text-muted); }
.ab-partes .ab-parte { margin-left: .5rem; }
.ab-citas { border: 1px solid var(--panel-border); border-radius: 2px; background: var(--panel);
  padding: .9rem 1.1rem; }
.ab-citas summary { cursor: pointer; font: 600 .95rem/1.4 'Archivo', 'Helvetica Neue', Arial, sans-serif; }
.ab-citas p { margin: .6rem 0 .9rem; color: var(--text-muted); font-size: .9rem; line-height: 1.55; max-width: 60rem; }
.ab-citas ol { margin: 0; padding: 0; list-style: none; counter-reset: paso; }
.ab-citas li { counter-increment: paso; display: grid; grid-template-columns: 2.4rem minmax(9rem, 16rem) 1fr;
  gap: .25rem 1rem; padding: .55rem 0; border-top: 1px solid var(--panel-border); }
.ab-citas li::before { content: counter(paso, decimal-leading-zero) " /";
  font: 400 .75rem/1.5 'IBM Plex Mono', Consolas, monospace; color: var(--text-dim); }
.ab-citas .ab-paso { font: 500 .8rem/1.5 'IBM Plex Mono', Consolas, monospace; color: var(--text); }
.ab-citas q { font: italic 400 .92rem/1.55 'Literata', Georgia, serif; color: var(--text-muted); quotes: "«" "»"; }
.ab-pie { width: 100%; max-width: var(--archify-reader-width, 1440px); margin: 1.5rem auto 0;
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .5rem 1.5rem;
  background: var(--ab-noche); color: var(--ab-sobre-noche); border-radius: 2px; padding: .85rem 1.1rem;
  font: 400 .72rem/1.5 'IBM Plex Mono', Consolas, monospace; }
.ab-pie a { color: inherit; text-decoration: none; display: inline-flex; align-items: center; gap: .6rem; }
.ab-pie a:hover span { text-decoration: underline; }
/* El visor da a todo svg y a todo span reglas propias (ancho mínimo, bloques):
   en el pie se anulan. */
.ab-pie svg { width: 22px; height: 22px; min-width: 22px; max-width: 22px; flex: none; transform: none; }
.ab-pie span { display: inline; width: auto; height: auto; background: none; box-shadow: none;
  transform: none; white-space: normal; }
.ab-pie .ab-pie-herramienta { opacity: .62; }
@media (max-width: 720px) {
  .ab-citas li { grid-template-columns: 2.2rem 1fr; }
  .ab-citas q { grid-column: 2; }
}
/* En el teléfono la barra del visor no cabe en una línea: se queda con el tema
   y la exportación, y puede bajar a una segunda línea. */
@media (max-width: 600px) {
  :root .toolbar { flex-wrap: wrap; justify-content: flex-end; width: auto; max-width: 100%; row-gap: .4rem; }
  :root #btn-present, :root .preset-wrap { display: none; }
}
@media print { .ab-pie, .ab-parte { display: none; } .ab-citas { border: 0; } }
"""

# Símbolos de 16 x 16 que reemplazan al del tipo de componente.
ROMBO = ('<path d="M8 1.8 14.2 8 8 14.2 1.8 8Z"/>\n'
         '            <circle cx="8" cy="8" r="1.2" class="sigil-fill"/>')
INICIO = ('<circle cx="8" cy="8" r="5.3"/>\n'
          '            <path d="m6.9 5.3 3.7 2.7-3.7 2.7Z" class="sigil-fill"/>')
FIN = ('<circle cx="8" cy="8" r="5.3"/>\n'
       '            <circle cx="8" cy="8" r="2.5" class="sigil-fill"/>')

_SIMBOLO = re.compile(
    r'(<g aria-hidden="true" data-semantic-sigil="[^"]+" class="semantic-sigil s-[^"]+"[^>]*>)([\s\S]*?)(</g>)')
_TITULO_NODO = '<g id="node-%s" '


def _cambiar_simbolos(html: str, inicios, fines) -> str:
    # Las decisiones: todo símbolo de `database` pasa a ser un rombo.
    html = re.sub(
        r'(<g aria-hidden="true" data-semantic-sigil="database" class="semantic-sigil s-database"[^>]*>)([\s\S]*?)(</g>)',
        lambda m: m.group(1) + "\n            " + ROMBO + "\n          " + m.group(3), html)
    for ids, forma in ((inicios, INICIO), (fines, FIN)):
        for nid in ids:
            pos = html.find(_TITULO_NODO % nid)
            if pos < 0:
                continue
            m = _SIMBOLO.search(html, pos)
            if not m or "data-semantic-sigil=\"database\"" in m.group(1):
                continue
            html = html[:m.start()] + m.group(1) + "\n            " + forma + "\n          " + m.group(3) + html[m.end():]
    return html


def _citas_en_titulos(html: str, citas: dict, etiqueta: str) -> str:
    """Agrega la cita al <title> del nodo: se lee al pasar el cursor."""
    for nid, cita in citas.items():
        pos = html.find(_TITULO_NODO % nid)
        if pos < 0:
            continue
        ini = html.find("<title>", pos)
        fin = html.find("</title>", ini)
        if ini < 0 or fin < 0:
            continue
        agregado = "&#10;%s: «%s»" % (escape(etiqueta), escape(cita.strip()))
        html = html[:fin] + agregado + html[fin:]
    return html


def _logo() -> str:
    svg = (RECURSOS / "logo-noche.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<!--[\s\S]*?-->", "", svg)
    svg = re.sub(r'\s*role="img" aria-label="[^"]*"', ' aria-hidden="true" focusable="false"', svg, count=1)
    return " ".join(svg.split())


def _anexo(lengua: str, pasos: list, navegacion) -> str:
    t = textos(lengua)
    filas = "\n".join(
        '      <li><span class="ab-paso">%s</span><q>%s</q></li>' % (escape(titulo), escape(cita.strip()))
        for titulo, cita in pasos)
    partes = ""
    if navegacion and navegacion.get("otras"):
        enlaces = " ".join('<a class="ab-parte" href="%s">%s</a>' % (escape(archivo, {'"': "&quot;"}),
                                                                   escape(t["ir_a_parte"].format(n=n)))
                           for n, archivo in navegacion["otras"])
        partes = '\n  <p class="ab-partes">%s %s</p>' % (
            escape(t["parte_de"].format(k=navegacion["numero"], n=navegacion["total"])), enlaces)
    return """
<section class="ab-anexo" aria-label="%(titulo)s">%(partes)s
  <details class="ab-citas">
    <summary>%(titulo)s</summary>
    <p>%(nota)s</p>
    <ol>
%(filas)s
    </ol>
  </details>
</section>
<footer class="ab-pie">
  <a href="https://andresbrinez.com" target="_blank" rel="noopener">%(logo)s<span>%(autor)s · andresbrinez.com</span></a>
  <span class="ab-pie-herramienta">%(herramienta)s</span>
</footer>
""" % {"titulo": escape(t["evidencia_titulo"]), "nota": escape(t["evidencia_nota"]), "filas": filas,
       "partes": partes, "logo": _logo(), "autor": escape(t["pie_autor"]),
       "herramienta": escape(t["pie_herramienta"])}


def _fin_del_contenedor(html: str) -> int:
    """Posición justo después del `<div class="container">` del visor.

    Cuenta divs y salta los bloques <script>, donde un `<div` podría aparecer
    como texto. Devuelve -1 si no lo encuentra.
    """
    inicio = html.find('<div class="container">')
    if inicio < 0:
        return -1
    profundidad = 0
    pos = inicio
    etiqueta = re.compile(r"<script\b|<div\b|</div>")
    while True:
        m = etiqueta.search(html, pos)
        if not m:
            return -1
        if m.group(0) == "<script":
            cierre = html.find("</script>", m.end())
            if cierre < 0:
                return -1
            pos = cierre + len("</script>")
            continue
        profundidad += 1 if m.group(0) == "<div" else -1
        pos = m.end()
        if profundidad == 0:
            return pos


def vestir(ruta: Path, lengua: str = "es", pasos=None, citas=None, inicios=(), fines=(),
           navegacion=None) -> bool:
    """Pone la piel de la marca en un HTML ya entregado por Archify.

    pasos: lista de (título, cita) para el anexo.
    citas: {id de nodo: cita} para el texto al pasar el cursor.
    navegacion: {"numero", "total", "otras": [(n, archivo)]} si el proceso va en partes.
    Devuelve False si el archivo ya tenía la piel o no parece un HTML de Archify.
    """
    ruta = Path(ruta)
    html = ruta.read_text(encoding="utf-8")
    if SELLO in html:
        return False
    corte = html.rfind("</head>")
    if corte < 0 or '<div class="container">' not in html:
        return False
    t = textos(lengua)

    # Primero el idioma del visor: el reemplazo de textos se hace sobre el
    # marcado de Archify y no debe tocar lo que se agrega después.
    html = idioma.traducir(html, lengua)

    bloque = _BLOQUE_FUENTES.search(html)
    if bloque:
        propias = _fuentes_css(_DE_LA_PAGINA)
        html = (html[:bloque.end(2)] + "\n/* Tipografías de la marca, para la página y las exportaciones. */\n"
                + _fuentes_css(_DEL_DIBUJO) + "\n" + html[bloque.end(2):])
    else:
        propias = _fuentes_css()
    piel = "\n<style %s>\n/* Sabana y candela sobre Archify. Generado por flujo/marca.py */\n%s\n%s\n%s\n</style>\n" % (
        SELLO, propias, PALETA, ESTILOS)
    corte = html.rfind("</head>")
    html = html[:corte] + piel + html[corte:]

    html = _cambiar_simbolos(html, list(inicios), list(fines))
    if citas:
        html = _citas_en_titulos(html, citas, t["del_relato"])

    if navegacion and navegacion.get("otras"):
        enlaces = "".join('<a class="ab-parte" href="%s">%s</a>' % (escape(archivo, {'"': "&quot;"}),
                                                                  escape(t["ir_a_parte"].format(n=n)))
                          for n, archivo in navegacion["otras"])
        html = re.sub(r"(<h1>[\s\S]*?</h1>)", lambda m: m.group(1) + enlaces, html, count=1)

    anexo = _anexo(lengua, pasos or [], navegacion)
    pos = _fin_del_contenedor(html)
    if pos < 0:
        pos = html.rfind("</body>")
    html = html[:pos] + anexo + html[pos:]
    with open(ruta, "w", encoding="utf-8", newline="\n") as salida:
        salida.write(html)
    return True
