# Avisos de terceros

«Del audio al flujo» es de Andrés Briñez y se publica bajo la licencia MIT (ver
`LICENSE`). Incluye trabajo de otros, con sus propias licencias:

## Archify

El compilador que dibuja los flujos. Va copiado en `vendor/archify/`, sin cambios,
para que la herramienta funcione sin instalar nada más que Node.

- Proyecto: https://github.com/tt-a1i/archify
- Versión copiada: 2.17.0-dev.1
- Licencia: MIT. Copyright (c) 2026 tt-a1i (Archify); Copyright (c) 2025 Cocoon AI.
  Texto completo en `vendor/archify/LICENSE`.
- Archify trae a su vez avisos propios (marcas de terceros, la tipografía JetBrains
  Mono bajo la SIL Open Font License 1.1) en `vendor/archify/THIRD_PARTY_NOTICES.md`
  y `vendor/archify/assets/JetBrainsMono-OFL.txt`.

De la copia se dejaron fuera las pruebas de Archify, los ejemplos ya dibujados en
HTML y las instrucciones para agentes de su propia habilidad, que no hacen falta
para dibujar.

La piel de la marca (`flujo/marca.py`) se pone encima del HTML que Archify entrega,
redefiniendo sus variables de color y tipografía; el idioma del visor
(`flujo/idioma.py`) cambia su tabla de textos. Ninguno de los dos modifica el
código de Archify.

## Tipografías

Archivo, Literata e IBM Plex Mono, bajo la SIL Open Font License 1.1. Detalle y
texto de la licencia en `flujo/recursos/fuentes/LICENCIA.md`.

## faster-whisper (opcional)

`transcribir.py` usa faster-whisper (MIT, https://github.com/SYSTRAN/faster-whisper)
si la persona lo instala. No viene incluido en este repositorio, y tampoco el
modelo de reconocimiento de voz, que se descarga en el computador de quien lo usa.
