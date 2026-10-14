---
name: del-audio-al-flujo
description: Dibuja por carriles el flujo de un proceso de empresa a partir de lo que una persona cuenta (texto pegado, transcripción o nota de voz). Úsela cuando alguien quiera ver cómo funciona hoy un proceso de su empresa (ventas, compras, despacho, cobro, cierre de caja, atención) a partir de su relato. La IA escribe un modelo intermedio sin inventar pasos, con la frase del relato que respalda cada uno; dibujar.py lo convierte con Archify en un HTML que se abre en el navegador y se exporta a PNG o SVG. Also use it to draw a swimlane process flow from a transcript or a voice note.
license: MIT
metadata:
  version: "1.0.0"
  author: Andrés Briñez
---

# Del audio al flujo

Convierte el relato de un proceso en un flujo dibujado por carriles. A usted, la IA,
le toca una sola parte: leer el relato y escribir el modelo intermedio. Todo lo
demás lo hace `dibujar.py`, siempre igual: revisa el modelo, lo acomoda en
carriles y columnas, lo dibuja con Archify, le pone la marca y abre el resultado.

Hable con la persona en su idioma y trátela de usted. Corra las órdenes desde la
carpeta de esta habilidad, la que contiene este archivo.

## Paso 0. Revisar el computador

Windows: `py dibujar.py --comprobar` · macOS y Linux: `python3 dibujar.py --comprobar`

Hace falta Python 3.9 o más nuevo y Node 18 o más nuevo. Si falta algo, la orden
dice cómo instalarlo en ese sistema. Explíquele a la persona qué es y pídale permiso
antes de instalar nada. En Windows, si `py` no existe, pruebe `python`.

## Paso 1. Conseguir el relato

Cada proceso va en su propia carpeta: `mis-flujos/AAAA-MM-DD-nombre-corto/`
(la carpeta `mis-flujos/` no se sube a git). Si la persona prefiere otro lugar, úselo.

- **Texto.** La persona lo pega o le da un archivo. Guárdelo tal cual en
  `relato.md` dentro de la carpeta del proceso. No lo corrija, no lo resuma, no lo
  traduzca: las citas se comparan contra ese archivo.
- **Audio, opción A (la recomendada).** Pídale que lo transcriba con lo que ya tiene
  y le pegue el texto: Word en la web (Dictar, Transcribir), el dictado de Windows
  (Win + H), el dictado de macOS o la grabadora del teléfono. Los pasos de cada uno
  están en el README, sección «Con un audio». Después siga como con un texto.
- **Audio, opción B.** Transcribir en este computador con faster-whisper. Antes,
  dígale que hay que instalarlo (`py -m pip install faster-whisper`, o `python3 -m pip
  install faster-whisper`) y que la primera vez descarga un modelo de unos 500 MB.
  Solo si acepta:
  `py transcribir.py ruta/al/audio.m4a --salida mis-flujos/CARPETA/relato.md`

Si el relato no describe un proceso, o es tan corto que no alcanza para cinco
acciones, dígaselo y pídale que cuente más antes de seguir.

## Paso 2. Escribir el modelo intermedio

Lea `prompts/proceso.md` (las reglas, completas) y `esquemas/proceso.schema.json`
(la forma). Mire el ejemplo resuelto en `ejemplos/pedido-a-despacho/`: `relato.md`
y `proceso.json`. Escriba `proceso.json` en la carpeta del proceso.

Lo que no se negocia:

1. Nada que el relato no diga: ni pasos, ni roles, ni herramientas, ni dolores.
2. Cada paso lleva en `cita` una frase copiada tal cual del relato.
3. Lo que falta para completar el flujo va a `preguntas_abiertas`, no se adivina.
4. Se escribe en el idioma del relato (`idioma`: `es` o `en`).

## Paso 3. Dibujar

Windows: `py dibujar.py mis-flujos/CARPETA/proceso.json` · macOS y Linux: `python3 dibujar.py mis-flujos/CARPETA/proceso.json`

| Código | Qué pasó | Qué hacer |
| --- | --- | --- |
| 0 | Dibujado; se abrió en el navegador | Lea los avisos: una cita que no aparece en el relato se corrige y se vuelve a dibujar |
| 1 | El modelo tiene errores | El mensaje dice cuáles y dónde; corrija `proceso.json` y vuelva a correr |
| 2 | Falta Python o Node | Siga las instrucciones del mensaje |
| 3 | Archify no pudo dibujar | Acorte títulos o etiquetas y revise las conexiones |

Opciones: `--no-abrir` no abre el navegador; `--json` imprime el resultado como datos;
`--salida CARPETA` guarda el dibujo en otra parte; `--relato ARCHIVO` compara las citas
con otro archivo.

Si el proceso no cabe en un dibujo, sale en partes enlazadas entre sí
(`flujo-parte-1.html`, `flujo-parte-2.html`...). No hace falta hacer nada.

## Paso 4. Entregar

Dígale a la persona, en pocas líneas:

- dónde quedó el archivo (la ruta completa) y que se abre con cualquier navegador;
- que para guardar una imagen use el botón «Exportar», arriba a la derecha: PNG para
  compartir, SVG para editar;
- las preguntas abiertas, para que las responda; con sus respuestas, actualice el
  modelo y vuelva a dibujar;
- que si algo no quedó como lo contó, le diga qué cambiar.

No le muestre el JSON salvo que lo pida.

## Archivos

| Ruta | Para qué |
| --- | --- |
| `prompts/proceso.md` | Cómo pasar del relato al modelo intermedio |
| `esquemas/proceso.schema.json` | La forma del modelo intermedio |
| `ejemplos/pedido-a-despacho/` | Un relato y su modelo, resueltos |
| `dibujar.py` | Del modelo al dibujo |
| `transcribir.py` | Opción B: del audio al texto, en este computador |
| `flujo/` | El código de las dos órdenes |
| `vendor/archify/` | Archify (MIT, de tt-a1i), el compilador que dibuja |

## Privacidad

La herramienta corre en este computador: el relato, el modelo y el dibujo se quedan
en la carpeta del proceso. Lo único que sale es lo que la persona le comparte a
usted. No suba esos archivos a ningún servicio ni los comparta sin que ella lo pida.
