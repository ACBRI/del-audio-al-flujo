# Del relato al modelo intermedio

Instrucciones para la IA que lee el relato de un proceso y escribe `proceso.json`.
El modelo intermedio es lo único que la IA escribe: `dibujar.py` lo revisa, lo
acomoda en carriles y columnas y lo dibuja. La forma exacta está en
`esquemas/proceso.schema.json`; un ejemplo completo, en
`ejemplos/pedido-a-despacho/`.

El dibujo muestra cómo funciona el proceso hoy, según quien lo cuenta. No es una
propuesta de mejora ni una opinión sobre el proceso.

## Las cinco reglas

1. **Solo lo que el relato dice.** No agregue pasos, roles, herramientas, tiempos
   ni problemas que la persona no mencionó, aunque parezcan obvios o probables.
   Un proceso de ventas «siempre tiene» una factura: si el relato no la nombra, el
   modelo tampoco.
2. **Una cita por paso.** En `cita` va la frase del relato que respalda el paso,
   copiada tal cual: mismas palabras, mismo orden. Puede recortarla a lo esencial y
   saltarse una parte con puntos suspensivos (`...`), pero no reescribirla.
   `dibujar.py` busca cada cita en `relato.md` y avisa si no la encuentra.
3. **Lo que falta se pregunta.** Si el relato no dice quién hace algo, qué pasa en
   el otro caso de una decisión o qué sigue después de un paso, no lo complete:
   escríbalo en `preguntas_abiertas`.
4. **El idioma del relato.** Si la persona habló en español, todo va en español
   (`"idioma": "es"`); si habló en inglés, en inglés (`"en"`). Los `id` van siempre
   en minúsculas, sin tildes ni espacios: `envia_pedido`, `cartera`.
5. **Las palabras de la persona.** Use los nombres que ella usa para las áreas, los
   documentos y los problemas. Si dice «la planilla», es la planilla, no «el
   formulario de control».

## Carriles: quién hace cada cosa

- Un carril por cada rol o área que el relato nombra. «La vendedora» es el carril
  «Ventas»; «el muchacho de bodega», «Bodega».
- Use roles, no nombres de personas. Si el relato solo da un nombre («luego Juan lo
  revisa»), use el rol si el relato lo deja claro; si no, pregúntelo.
- Quien es de fuera de la empresa (cliente, proveedor, banco, transportista,
  entidad del Estado) lleva `"externo": true`.
- En el orden en que aparecen en el relato: normalmente, primero quien inicia.
- Con tres a cinco carriles el dibujo se lee mejor; el máximo es ocho. No junte
  dos roles que el relato distingue para ahorrar carriles.

## Fases: las etapas grandes

- Dos a cuatro etapas, nombradas con uno o dos verbos: «Pedir», «Aprobar el
  crédito», «Despachar». Hasta 24 caracteres.
- En orden. Cada paso va en la fase en que ocurre (`"fase": "aprobar"`).
- Si el proceso es corto o no tiene etapas claras, deje `"fases": []` y
  `"fase": null` en cada paso.

## Pasos

Un paso es una acción con un responsable. En la lista van en el orden en que
ocurren; las ramas de una decisión, después de la decisión.

| Campo | Qué lleva |
| --- | --- |
| `titulo` | Verbo en presente y objeto: «Envía el pedido», «Revisa el cupo». En una decisión, la pregunta: «¿Tiene cupo?». Hasta 32 caracteres; lo ideal, dos a cuatro palabras. |
| `detalle` | Un complemento corto que se lee debajo del título: «por WhatsApp», «producto por producto». Hasta 36 caracteres. `null` si no hace falta. |
| `tipo` | `inicio`, `tarea`, `sistema`, `decision` o `fin` (ver abajo). |
| `carril` | El `id` del carril de quien lo hace. |
| `herramienta` | Con qué se hace, si el relato lo dice: «WhatsApp», «hoja de cálculo», «papel». Hasta 32 caracteres. |
| `dolor` | Lo que la persona dijo que molesta, demora o falla en ese paso, con sus palabras y corto: «se digita dos veces». Hasta 32 caracteres. `null` si no lo dijo. |
| `cita` | La frase del relato que lo respalda (regla 2). |

Los tipos:

- `inicio`: lo que dispara el proceso. Normalmente uno.
- `tarea`: trabajo de una persona fuera de un sistema: papel, teléfono, correo,
  WhatsApp, hoja de cálculo.
- `sistema`: trabajo hecho dentro de un sistema: el ERP, el programa contable, el
  inventario, un portal. Lo haga una persona o lo haga el sistema solo.
- `decision`: una pregunta con dos o más salidas. Necesita al menos dos conexiones
  de salida, cada una con su respuesta como etiqueta.
- `fin`: donde termina el proceso. Puede haber más de uno.

Cuidados:

- **El dolor es de la persona, no suyo.** Si el relato dice «se digita dos veces»,
  eso es un dolor. Si usted piensa que copiar a mano es ineficiente pero la persona
  no lo dijo, no lo es.
- **Ni microacciones ni pasos dobles.** «Abre el correo, lo lee y lo imprime» es un
  paso. «Ventas arma el pedido y Bodega lo despacha» son dos, porque son dos
  responsables.
- **Lo que se repite no se duplica.** Si algo vuelve a revisarse, no escriba el paso
  dos veces: dibuje una conexión de vuelta hacia el paso anterior.
- **Una decisión a medias no es decisión.** Si el relato solo cuenta un caso («si
  tiene cupo, se despacha»), no invente el otro: deje el paso como tarea («Revisa el
  cupo») y pregunte en `preguntas_abiertas` qué pasa cuando no tiene cupo.

## Conexiones

- `desde` y `hacia` son `id` de pasos, en el sentido en que avanza el trabajo.
- Las que salen de una decisión llevan la respuesta como etiqueta: «Sí» y «No», o
  las palabras del relato: «con cupo», «sin cupo». Hasta 24 caracteres.
- Una vuelta (un reproceso, una segunda revisión) es una conexión hacia un paso
  anterior. Puede llevar etiqueta: «vuelve a revisar».
- En las demás, la etiqueta es `null` o una palabra que agregue algo: «por correo»,
  «al día siguiente».
- Todo paso, salvo el inicio, recibe al menos una conexión. Si el relato no dice qué
  sigue después de un paso, déjelo sin salida y pregúntelo.

## Observaciones

Lo que el relato dice sobre el proceso y no es un paso. Frases cortas, de hasta 140
caracteres, que se entiendan sin leer el relato.

- `tiempo`: dónde se pierde tiempo. «La respuesta de Cartera puede tardar hasta
  medio día».
- `riesgo`: qué puede salir mal: errores, pérdidas, todo en manos de una persona.
- `otra`: cualquier otra nota que valga la pena.

Lleve la `cita` que la respalda, o `null` si resume varias frases. No proponga
soluciones ni recomiende herramientas.

## Preguntas abiertas

Lo que falta saber para que el flujo esté completo: quién decide, qué pasa en el
otro caso, cuánto tarda, con qué se hace. Escritas para la persona, claras y
cortas: «¿Quién decide si se despacha un pedido incompleto?». Hasta diez, las más
importantes primero. Si no falta nada, la lista va vacía.

## Antes de dibujar

- [ ] Cada paso tiene una cita copiada del relato.
- [ ] Ningún paso, rol, herramienta o dolor sale de usted.
- [ ] Cada decisión tiene al menos dos salidas, cada una con su respuesta.
- [ ] Los `id` van en minúsculas, sin tildes ni espacios, y no se repiten.
- [ ] Los títulos no pasan de 32 caracteres.
- [ ] Lo que falta está en `preguntas_abiertas`.

Después corra `dibujar.py`: revisa el esquema, la coherencia y las citas, y dice qué
corregir si algo falla.

## Un fragmento de ejemplo

Del relato: «Después le escribe por correo a Cartera para que revise el crédito, y
ahí el pedido espera; a veces la respuesta llega hasta medio día después. En
Cartera miran si el cliente tiene cupo y si está al día.»

```json
{
  "id": "pide_revision",
  "tipo": "tarea",
  "titulo": "Pide revisar el crédito",
  "detalle": "a Cartera, por correo",
  "carril": "ventas",
  "fase": "aprobar",
  "herramienta": "correo",
  "dolor": "espera hasta medio día",
  "cita": "Después le escribe por correo a Cartera para que revise el crédito, y ahí el pedido espera; a veces la respuesta llega hasta medio día después."
}
```

```json
{
  "id": "tiene_cupo",
  "tipo": "decision",
  "titulo": "¿Tiene cupo y está al día?",
  "detalle": null,
  "carril": "cartera",
  "fase": "aprobar",
  "herramienta": null,
  "dolor": null,
  "cita": "En Cartera miran si el cliente tiene cupo y si está al día."
}
```

El resto del ejemplo, con sus conexiones, observaciones y preguntas, está en
`ejemplos/pedido-a-despacho/proceso.json`.
