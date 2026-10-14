// Fotografía un dibujo en un Chromium sin ventana y prueba su exportación.
//
//   node herramientas/navegador.mjs <chrome> <dibujo.html> <carpeta-de-salida>
//
// Deja en la carpeta: escritorio.png, escritorio-oscuro.png,
// escritorio-completo.png y telefono.png, más descargas/ con el PNG y el SVG que
// entrega el botón «Exportar» del visor. Cada captura espera a que las
// tipografías terminen de cargar (document.fonts.ready): el visor acomoda la
// leyenda con las letras ya puestas, y una foto tomada antes la mostraría a
// medio acomodar. Solo usa lo que trae Node 22 y el protocolo de depuración del
// navegador.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [chrome, html, salida] = process.argv.slice(2);
if (!chrome || !html || !salida) {
  console.error('Uso: node herramientas/navegador.mjs <chrome> <dibujo.html> <carpeta-de-salida>');
  process.exit(2);
}
const TOMAS = [
  // nombre, ancho, alto, escala, oscuro, teléfono
  ['escritorio', 1440, 900, 1, false, false],
  ['escritorio-oscuro', 1440, 900, 1, true, false],
  ['escritorio-completo', 1440, 1400, 1, false, false],
  ['telefono', 390, 844, 2, false, true],
];

fs.mkdirSync(salida, { recursive: true });
const descargas = path.join(path.resolve(salida), 'descargas');
fs.mkdirSync(descargas, { recursive: true });
const perfil = fs.mkdtempSync(path.join(path.resolve(salida), 'perfil-'));
const proceso = spawn(chrome, ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--remote-debugging-port=0',
  `--user-data-dir=${perfil}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });

const direccion = await new Promise((listo, falla) => {
  let texto = '';
  proceso.stderr.on('data', (d) => {
    texto += d;
    const m = texto.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) listo(m[1]);
  });
  setTimeout(() => falla(new Error('El navegador no abrió el puerto de depuración.')), 20000);
});

const canal = new WebSocket(direccion);
await new Promise((listo) => canal.addEventListener('open', listo));
let siguiente = 0;
const pendientes = new Map();
const oyentes = [];
canal.addEventListener('message', (e) => {
  const mensaje = JSON.parse(e.data);
  if (mensaje.id && pendientes.has(mensaje.id)) {
    pendientes.get(mensaje.id)(mensaje);
    pendientes.delete(mensaje.id);
  } else {
    oyentes.forEach((oyente) => oyente(mensaje));
  }
});
const enviar = (method, params = {}, sessionId) => new Promise((listo) => {
  siguiente += 1;
  pendientes.set(siguiente, listo);
  canal.send(JSON.stringify({ id: siguiente, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const esperar = (ms) => new Promise((listo) => setTimeout(listo, ms));
const direccionDibujo = pathToFileURL(path.resolve(html)).href;

let fallas = 0;
try {
  await enviar('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: descargas });
  const { result: { targetId } } = await enviar('Target.createTarget', { url: 'about:blank' });
  const { result: { sessionId } } = await enviar('Target.attachToTarget', { targetId, flatten: true });
  await enviar('Page.enable', {}, sessionId);
  const evaluar = (expression) => enviar('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);

  async function abrir(ancho, alto, escala, oscuro, telefono) {
    await enviar('Emulation.setDeviceMetricsOverride',
      { width: ancho, height: alto, deviceScaleFactor: escala, mobile: telefono }, sessionId);
    await enviar('Emulation.setEmulatedMedia',
      { features: [{ name: 'prefers-color-scheme', value: oscuro ? 'dark' : 'light' }] }, sessionId);
    const cargo = new Promise((listo) => {
      const oyente = (m) => {
        if (m.method === 'Page.loadEventFired' && m.sessionId === sessionId) {
          oyentes.splice(oyentes.indexOf(oyente), 1);
          listo();
        }
      };
      oyentes.push(oyente);
    });
    await enviar('Page.navigate', { url: direccionDibujo }, sessionId);
    await cargo;
    await evaluar('document.fonts.ready.then(() => new Promise((r) => setTimeout(r, 800)))');
  }

  for (const [nombre, ancho, alto, escala, oscuro, telefono] of TOMAS) {
    await abrir(ancho, alto, escala, oscuro, telefono);
    const { result } = await enviar('Page.captureScreenshot', { format: 'png' }, sessionId);
    const destino = path.join(salida, `${nombre}.png`);
    fs.writeFileSync(destino, Buffer.from(result.data, 'base64'));
    console.log(`captura: ${destino}`);
  }

  await abrir(1440, 900, 1, false, false);
  for (const formato of ['png', 'svg']) {
    const antes = new Set(fs.readdirSync(descargas));
    await evaluar(`(async () => {
      document.querySelector('#btn-export').click();
      await new Promise((r) => setTimeout(r, 400));
      document.querySelector('[data-format="${formato}"]').click();
    })()`);
    let nuevo = null;
    for (let i = 0; i < 60 && !nuevo; i += 1) {
      await esperar(250);
      nuevo = fs.readdirSync(descargas).find((f) => !antes.has(f) && !f.endsWith('.crdownload'));
    }
    if (nuevo) {
      console.log(`exportado ${formato}: ${path.join(descargas, nuevo)}`);
    } else {
      console.log(`exportado ${formato}: no se descargó nada`);
      fallas += 1;
    }
    await esperar(300);
  }
} finally {
  canal.close();
  const salio = new Promise((listo) => proceso.on('exit', listo));
  proceso.kill();
  await salio;
  fs.rmSync(perfil, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
}
process.exit(fallas ? 1 : 0);
