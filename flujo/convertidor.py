# -*- coding: utf-8 -*-
"""Del modelo intermedio a la especificación `workflow` v2 de Archify.

Archify dibuja carriles horizontales y seis columnas lógicas (0 a 5). El modelo
intermedio no sabe de columnas: solo tiene pasos en orden y conexiones. Aquí se
decide dónde va cada paso:

1. Columna por rango. Cada paso va una columna a la derecha del paso más tardío
   que lo precede. Las conexiones que vuelven hacia atrás (un reproceso, una
   segunda revisión) no cuentan para el rango: se dibujan como vueltas.
2. Un paso por celda. Si dos pasos caen en el mismo carril y la misma columna,
   el segundo se corre a la derecha.
3. Compresión. Si hacen falta más de seis columnas, se juntan dos columnas
   vecinas cuyos pasos están en carriles distintos: el traspaso entre ellos
   queda vertical, de un carril al otro. No se juntan si la línea vertical
   tendría que atravesar otro paso, y se prefiere juntar dentro de una misma
   fase para que los encabezados de fase no se encimen.
4. Partes. Si aun así no cabe, el proceso se parte en dos o más diagramas, y
   después se comprime cada parte. Cada corte lleva un enlace: «Sigue en la
   parte 2» al final de una y «Viene de la parte 1» al principio de la
   siguiente. Un reproceso nunca queda partido en dos si se puede evitar.

Los tipos de nodo de Archify son tipos de componente (frontend, backend...). Aquí
se leen como se leen en `marca.py`: fuera del sistema, dentro del sistema, donde
duele y quien espera el resultado. Las decisiones usan `database`, que la piel
de la marca dibuja con un rombo y el color de la noche.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from .textos import textos

MAX_COLUMNAS = 6


# ------------------------------------------------------------------ tipos

def tipo_de_nodo(paso: dict, carril_externo: bool) -> str:
    """El tipo de Archify que corresponde a un paso, en orden de prioridad."""
    if paso["tipo"] == "decision":
        return "database"          # decisión: rombo, color noche
    if paso["dolor"]:
        return "security"          # donde duele: candela
    if carril_externo:
        return "external"          # quien espera el resultado: tierra suave
    if paso["tipo"] == "sistema":
        return "backend"           # dentro del sistema: morichal
    return "frontend"              # fuera del sistema: sabana


def _limpio(texto):
    texto = (texto or "").strip()
    return texto or None


def textos_de_nodo(paso: dict):
    """Título, subtítulo y marca inferior del nodo.

    La marca inferior dice con qué se hace el paso; si el paso duele, dice qué
    duele, con el color de la candela.
    """
    titulo = paso["titulo"].strip()
    detalle = _limpio(paso["detalle"])
    herramienta = _limpio(paso["herramienta"])
    dolor = _limpio(paso["dolor"])
    if dolor:
        marca = dolor
        if not detalle and herramienta:
            detalle = herramienta
    else:
        marca = herramienta
        if marca and detalle and marca.casefold() in detalle.casefold():
            marca = None
    if marca and marca.casefold() == titulo.casefold():
        marca = None
    return titulo, detalle, marca


def unidades(texto: str) -> int:
    """Ancho relativo de un texto, como lo mide Archify: los caracteres anchos
    (chino, japonés, coreano) cuentan doble."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in texto or "")


def ancho_necesario(nodo: dict) -> int:
    """El ancho con el que el título se lee a su tamaño normal.

    Son las mismas cuentas con que Archify valida: el título mide 6,8 px por
    carácter; el subtítulo y la marca inferior, unos 4,8 y 4,2 px a su tamaño
    preferido. Se suma un margen para que ningún texto toque el borde.
    Calcularlo de antemano evita que el compilador rechace el dibujo por un
    texto que no cabe.
    """
    ancho = max(92.0, unidades(nodo["label"]) * 6.8 + 12)
    if nodo.get("sublabel"):
        ancho = max(ancho, unidades(nodo["sublabel"]) * 4.8 + 20)
    if nodo.get("tag"):
        ancho = max(ancho, unidades(nodo["tag"]) * 4.2 + 20)
    return int(-(-ancho // 2) * 2)


def igualar_anchos(nodos: list, minimo: int = 112) -> None:
    """Todos los nodos de una columna con el mismo ancho: el de su texto más largo."""
    por_columna = defaultdict(list)
    for n in nodos:
        por_columna[n["col"]].append(n)
    for grupo in por_columna.values():
        ancho = max([minimo] + [ancho_necesario(n) for n in grupo])
        for n in grupo:
            n["width"] = ancho


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def es_afirmativa(etiqueta) -> bool:
    return bool(re.match(r"^(si|yes|ok)\b", _sin_tildes((etiqueta or "").strip().casefold())))


# ------------------------------------------------------------------ grafo

class Grafo:
    """Los pasos en el orden del relato y sus conexiones, separadas en dos:
    las que avanzan (hacia un paso posterior) y las que vuelven."""

    def __init__(self, modelo: dict):
        self.pasos = modelo["pasos"]
        self.por_id = {p["id"]: p for p in self.pasos}
        self.orden = {p["id"]: i for i, p in enumerate(self.pasos)}
        self.adelante: list = []
        self.atras: list = []
        for c in modelo["conexiones"]:
            if self.orden[c["hacia"]] > self.orden[c["desde"]]:
                self.adelante.append(c)
            else:
                self.atras.append(c)
        self.salidas = defaultdict(list)
        self.entradas = defaultdict(list)
        for c in self.adelante:
            self.salidas[c["desde"]].append(c)
            self.entradas[c["hacia"]].append(c)
        self.con_salida = {c["desde"] for c in modelo["conexiones"]}

    def finales(self) -> set:
        fines = {p["id"] for p in self.pasos if p["tipo"] == "fin"}
        if fines:
            return fines
        return {p["id"] for p in self.pasos if p["id"] not in self.con_salida}

    def distancia_al_final(self) -> dict:
        """Cuántos pasos hacia adelante faltan para llegar a un final."""
        dist = {f: 0 for f in self.finales()}
        cola = list(dist)
        while cola:
            actual = cola.pop(0)
            for c in self.entradas[actual]:
                if c["desde"] not in dist:
                    dist[c["desde"]] = dist[actual] + 1
                    cola.append(c["desde"])
        return dist

    def camino_principal(self) -> list:
        """El camino que cuenta la historia completa.

        En cada bifurcación se sigue la salida desde la que se llega antes a un
        final; así una salida que termina en un reproceso no se toma por el
        camino principal. Empates: la respuesta afirmativa y luego el orden del
        relato.
        """
        inicios = [p["id"] for p in self.pasos if p["tipo"] == "inicio"]
        actual = inicios[0] if inicios else self.pasos[0]["id"]
        dist = self.distancia_al_final()
        camino = [actual]
        while self.salidas[actual]:
            def clave(c):
                h = c["hacia"]
                return (h not in dist, dist.get(h, 0), not es_afirmativa(c["etiqueta"]), self.orden[h])
            elegido = min(self.salidas[actual], key=clave)["hacia"]
            camino.append(elegido)
            actual = elegido
        return camino


# ------------------------------------------------------------------ columnas

def asignar_columnas(g: Grafo, orden_fase: dict) -> dict:
    """Columna de cada paso antes de comprimir.

    Un paso va a la derecha de los que lo preceden y de todos los pasos ya
    ubicados de fases anteriores: así cada fase ocupa su propio tramo de
    columnas y los encabezados no se enciman. Un desvío (un reproceso, una
    espera) queda dentro de su fase en vez de colarse bajo la siguiente.
    """
    col: dict = {}
    ocupado = set()
    previo = None
    for p in g.pasos:
        pid = p["id"]
        anteriores = [c["desde"] for c in g.entradas[pid]]
        if anteriores:
            r = max(col[q] for q in anteriores) + 1
        elif previo is None or p["tipo"] == "inicio":
            r = 0
        else:
            r = col[previo]
        fase = orden_fase.get(p["fase"])
        if fase is not None:
            antes = [col[q] for q in col if orden_fase.get(g.por_id[q]["fase"], fase) < fase]
            if antes:
                r = max(r, max(antes) + 1)
        while (p["carril"], r) in ocupado:
            r += 1
        col[pid] = r
        ocupado.add((p["carril"], r))
        previo = pid
    return col


def comprimir(g: Grafo, col: dict, carril_idx: dict, max_columnas: int = MAX_COLUMNAS) -> dict:
    col = dict(col)
    todas = g.adelante + g.atras
    while col and max(col.values()) + 1 > max_columnas:
        n = max(col.values()) + 1
        mejor = None
        for i in range(n - 1):
            a = [x for x in col if col[x] == i]
            b = [x for x in col if col[x] == i + 1]
            if {g.por_id[x]["carril"] for x in a} & {g.por_id[x]["carril"] for x in b}:
                continue
            juntos = set(a) | set(b)
            atraviesa = False
            for c in todas:
                d, h = c["desde"], c["hacia"]
                if d in juntos and h in juntos:
                    bajo, alto = sorted((carril_idx[d], carril_idx[h]))
                    if any(bajo < carril_idx[x] < alto for x in juntos if x not in (d, h)):
                        atraviesa = True
                        break
            if atraviesa:
                continue
            fases_a = {g.por_id[x]["fase"] for x in a}
            fases_b = {g.por_id[x]["fase"] for x in b}
            corta_fase = 0 if (fases_a == fases_b and len(fases_a) == 1) else 1
            # La primera columna se junta de último: el nombre de cada carril
            # está arriba a la izquierda, y una línea vertical que baje a un
            # paso de esa columna tendría que rodearlo.
            puntaje = (corta_fase, i == 0, len(juntos), i)
            if mejor is None or puntaje < mejor[0]:
                mejor = (puntaje, i)
        if mejor is None:
            break
        i = mejor[1]
        for x in col:
            if col[x] > i:
                col[x] -= 1
    return col


def _ancho(col: dict) -> int:
    return max(col.values()) + 1 if col else 0


def _tramo(col: dict, desde: int, hasta: int) -> dict:
    """Los pasos entre dos columnas, con las columnas contadas desde cero."""
    return {pid: c - desde for pid, c in col.items() if desde <= c <= hasta}


def planificar(g: Grafo, col: dict, carril_idx: dict, max_columnas: int = MAX_COLUMNAS) -> list:
    """Reparte los pasos en uno o más dibujos. Devuelve una lista de {paso: columna}.

    Si comprimiendo cabe en seis columnas, es un solo dibujo. Si no, se corta
    primero y se comprime después cada parte con su propia capacidad: la
    primera reserva su última columna para el enlace «Sigue en la parte 2», la
    última reserva la primera para «Viene de la parte 1» y las del medio, ambas.
    Así cada parte se aprieta solo lo necesario y las fases no se enciman.

    Cada parte se estira tanto como quepa. Nunca se corta por en medio de una
    vuelta (un reproceso queda entero en una parte) si hay otro lugar donde
    cortar, y entre los dos cortes más largos se prefiere el que cae donde
    cambia la fase.
    """
    entero = comprimir(g, col, carril_idx, max_columnas)
    if _ancho(entero) <= max_columnas:
        return [entero]
    n = _ancho(col)
    fases_col = defaultdict(set)
    for pid, c in col.items():
        fases_col[c].add(g.por_id[pid]["fase"])
    vueltas = [(min(col[c["desde"]], col[c["hacia"]]), max(col[c["desde"]], col[c["hacia"]])) for c in g.atras]

    def corta_vuelta(fin):
        return any(a <= fin < b for a, b in vueltas)

    def cabe(desde, hasta, capacidad):
        return _ancho(comprimir(g, _tramo(col, desde, hasta), carril_idx, capacidad)) <= capacidad

    partes: list = []
    inicio = 0
    while inicio < n:
        primera = not partes
        capacidad_final = max_columnas - (0 if primera else 1)
        if cabe(inicio, n - 1, capacidad_final):
            partes.append(comprimir(g, _tramo(col, inicio, n - 1), carril_idx, capacidad_final))
            break
        capacidad = capacidad_final - 1
        caben = []
        for fin in range(inicio, n - 1):
            if not cabe(inicio, fin, capacidad):
                break
            caben.append(fin)
        caben.reverse()
        if not caben:  # ni una columna cabe: no debería pasar, pero no se cuelga
            caben = [inicio]
        posibles = [f for f in caben if not corta_vuelta(f)] or caben
        fin = posibles[0]
        for candidato in posibles[:2]:
            if fases_col[candidato].isdisjoint(fases_col[candidato + 1]):
                fin = candidato
                break
        partes.append(comprimir(g, _tramo(col, inicio, fin), carril_idx, capacidad))
        inicio = fin + 1
    return partes


# ------------------------------------------------------------------ fases

def fases_de_parte(modelo: dict, pasos: list, col_local: dict) -> list:
    nombres = {f["id"]: f["nombre"] for f in modelo["fases"]}
    rangos = []
    for f in modelo["fases"]:
        cols = [col_local[p["id"]] for p in pasos if p["fase"] == f["id"]]
        if cols:
            rangos.append([min(cols), max(cols), [f["id"]]])
    rangos.sort(key=lambda r: (r[0], r[1]))
    unidas: list = []
    for r in rangos:
        if unidas and r[0] <= unidas[-1][1]:
            unidas[-1][1] = max(unidas[-1][1], r[1])
            unidas[-1][2].extend(r[2])
        else:
            unidas.append(r)
    return [{"id": "fase-" + ids[0].replace("_", "-"),
             "label": " · ".join(nombres[i] for i in ids),
             "fromCol": desde, "toCol": hasta}
            for desde, hasta, ids in unidas]


# ------------------------------------------------------------------ tarjetas

def tarjetas(modelo: dict, t: dict) -> list:
    grupos = (("tiempo", "rose", t["tarjeta_tiempo"]),
              ("riesgo", "amber", t["tarjeta_riesgo"]),
              ("otra", "emerald", t["tarjeta_otra"]))
    salida = []
    for tipo, punto, titulo in grupos:
        items = [o["texto"].strip() for o in modelo["observaciones"] if o["tipo"] == tipo]
        if items:
            salida.append({"dot": punto, "title": titulo, "items": items})
    if modelo["preguntas_abiertas"]:
        salida.append({"dot": "violet", "title": t["tarjeta_preguntas"],
                       "items": [q.strip() for q in modelo["preguntas_abiertas"]]})
    return salida


# ------------------------------------------------------------------ conversión

def _id_carril(cid: str) -> str:
    return "carril-" + cid.replace("_", "-")


def convertir(modelo: dict) -> dict:
    """Devuelve {"partes": [...], "avisos": [...]}.

    Cada parte trae la especificación de Archify (`spec`) y lo que la piel de la
    marca necesita: la cita de cada paso y qué nodos abren y cierran el proceso.
    """
    idioma = modelo["idioma"]
    t = textos(idioma)
    g = Grafo(modelo)
    carriles = {c["id"]: c for c in modelo["carriles"]}
    orden_carril = {c["id"]: i for i, c in enumerate(modelo["carriles"])}
    carril_idx = {p["id"]: orden_carril[p["carril"]] for p in g.pasos}

    orden_fase = {f["id"]: i for i, f in enumerate(modelo["fases"])}
    plan = planificar(g, asignar_columnas(g, orden_fase), carril_idx)
    total = len(plan)
    parte_de = {pid: k for k, columnas in enumerate(plan) for pid in columnas}

    principal = g.camino_principal()
    aristas_principales = set(zip(principal, principal[1:]))
    cards = tarjetas(modelo, t)
    avisos: list = []

    partes = []
    for k, columnas in enumerate(plan):
        pasos = [p for p in g.pasos if parte_de[p["id"]] == k]
        ids = {p["id"] for p in pasos}
        corrimiento = 1 if k > 0 else 0  # la primera columna es del enlace de entrada
        col_local = {p["id"]: columnas[p["id"]] + corrimiento for p in pasos}
        ultima = max(col_local.values())

        nodos, aristas = [], []
        for p in pasos:
            titulo, detalle, marca = textos_de_nodo(p)
            nodo = {"id": p["id"], "lane": _id_carril(p["carril"]), "col": col_local[p["id"]],
                    "type": tipo_de_nodo(p, carriles[p["carril"]]["externo"]), "label": titulo}
            if detalle:
                nodo["sublabel"] = detalle
            if marca:
                nodo["tag"] = marca
            nodos.append(nodo)

        # Enlaces con otras partes, agrupados por carril y por parte de destino.
        salen = defaultdict(list)
        entran = defaultdict(list)
        for c in g.adelante:
            d, h = c["desde"], c["hacia"]
            if d in ids and h not in ids:
                salen[(g.por_id[d]["carril"], parte_de[h])].append(c)
            elif h in ids and d not in ids:
                entran[(g.por_id[h]["carril"], parte_de[d])].append(c)
        for c in g.atras:
            d, h = c["desde"], c["hacia"]
            if d in ids and h not in ids:
                avisos.append("La vuelta de «%s» a «%s» une dos partes distintas del dibujo y no se "
                              "traza; queda en el modelo." % (d, h))

        conector_salida = {}
        for (carril, destino), conexiones in sorted(salen.items(), key=lambda x: (orden_carril[x[0][0]], x[0][1])):
            cid = "x-sigue-%d-%s" % (destino + 1, carril.replace("_", "-"))
            destinos = list(dict.fromkeys(c["hacia"] for c in conexiones))
            sub = g.por_id[destinos[0]]["titulo"] if len(destinos) == 1 else t["varios_pasos"].format(n=len(destinos))
            nodos.append({"id": cid, "lane": _id_carril(carril), "col": ultima + 1, "type": "messagebus",
                          "label": t["sigue"].format(n=destino + 1), "sublabel": sub})
            for c in conexiones:
                arista = {"from": c["desde"], "to": cid, "variant": "dashed"}
                if c["etiqueta"]:
                    arista["label"] = c["etiqueta"].strip()
                aristas.append(arista)
                conector_salida[(c["desde"], c["hacia"])] = cid
        conector_entrada = {}
        for (carril, origen), conexiones in sorted(entran.items(), key=lambda x: (orden_carril[x[0][0]], x[0][1])):
            cid = "x-viene-%d-%s" % (origen + 1, carril.replace("_", "-"))
            origenes = list(dict.fromkeys(c["desde"] for c in conexiones))
            sub = g.por_id[origenes[0]]["titulo"] if len(origenes) == 1 else t["varios_pasos"].format(n=len(origenes))
            nodos.append({"id": cid, "lane": _id_carril(carril), "col": 0, "type": "messagebus",
                          "label": t["viene"].format(n=origen + 1), "sublabel": sub})
            for h in dict.fromkeys(c["hacia"] for c in conexiones):
                aristas.append({"from": cid, "to": h, "variant": "dashed"})
                for c in conexiones:
                    if c["hacia"] == h:
                        conector_entrada[(c["desde"], c["hacia"])] = cid

        igualar_anchos(nodos)
        decisiones = {p["id"] for p in pasos if p["tipo"] == "decision"}
        celdas = {(n["lane"], n["col"]) for n in nodos}
        for c in g.adelante:
            d, h = c["desde"], c["hacia"]
            if d in ids and h in ids:
                arista = {"from": d, "to": h}
                if c["etiqueta"]:
                    arista["label"] = c["etiqueta"].strip()
                if d in decisiones and (d, h) not in aristas_principales:
                    arista["variant"] = "dashed"
                    arista["role"] = "branch"
                # Dentro de un mismo carril, sin nada en medio, la línea va recta:
                # sin esta preferencia el trazador a veces rodea por debajo.
                carril = _id_carril(g.por_id[d]["carril"])
                if carril == _id_carril(g.por_id[h]["carril"]) and not any(
                        (carril, k_) in celdas for k_ in range(col_local[d] + 1, col_local[h])):
                    arista["route"] = "straight"
                aristas.append(arista)
        for c in g.atras:
            d, h = c["desde"], c["hacia"]
            if d in ids and h in ids:
                arista = {"from": d, "to": h, "variant": "dashed", "role": "return"}
                if c["etiqueta"]:
                    arista["label"] = c["etiqueta"].strip()
                # Un reproceso dentro del mismo carril se lee mejor como un arco
                # por encima de los pasos que como un rodeo por debajo.
                if g.por_id[d]["carril"] == g.por_id[h]["carril"]:
                    arista["route"] = "up-channel"
                aristas.append(arista)

        # Camino principal dentro de la parte, con sus enlaces si cruza.
        camino = [x for x in principal if x in ids]
        if camino:
            previo = principal.index(camino[0]) - 1
            if previo >= 0 and (principal[previo], camino[0]) in conector_entrada:
                camino.insert(0, conector_entrada[(principal[previo], camino[0])])
            siguiente = principal.index(camino[-1]) + 1
            if siguiente < len(principal) and (camino[-1], principal[siguiente]) in conector_salida:
                camino.append(conector_salida[(camino[-1], principal[siguiente])])

        usados = []
        for c in modelo["carriles"]:
            lane = _id_carril(c["id"])
            if any(n["lane"] == lane for n in nodos):
                usados.append({"id": lane, "label": c["nombre"].strip()})

        tipos = {n["type"] for n in nodos}
        entradas_leyenda = {k_: {"label": v} for k_, v in t["leyenda"].items() if k_ in tipos}
        if "messagebus" in entradas_leyenda:
            entradas_leyenda["messagebus"]["visible"] = False

        titulo = modelo["titulo"].strip()
        if total > 1:
            titulo = t["titulo_parte"].format(titulo=titulo, k=k + 1, n=total)
        meta = {"title": titulo, "locale": "en", "quality_profile": "showcase",
                "legend": {"mode": "auto", "entries": entradas_leyenda}}
        if _limpio(modelo["objetivo"]):
            meta["subtitle"] = modelo["objetivo"].strip()

        spec = {"schema_version": 2, "diagram_type": "workflow", "meta": meta,
                "lanes": usados, "nodes": nodos, "edges": aristas}
        fases = fases_de_parte(modelo, pasos, col_local)
        if fases:
            spec["phases"] = fases
        if len(camino) >= 2:
            spec["mainPath"] = camino
        if cards:
            spec["cards"] = cards

        partes.append({
            "spec": spec,
            "numero": k + 1,
            "total": total,
            "pasos": [p["id"] for p in pasos],
            "citas": {p["id"]: p["cita"] for p in pasos},
            "inicios": [p["id"] for p in pasos if p["tipo"] == "inicio"],
            "fines": [p["id"] for p in pasos if p["tipo"] == "fin"],
        })
    return {"partes": partes, "avisos": avisos}
