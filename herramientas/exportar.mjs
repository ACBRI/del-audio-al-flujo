// Abre un dibujo en un Chromium sin ventana, pulsa «Exportar» > PNG y
// «Exportar» > SVG en el visor, y espera las dos descargas. Sirve para comprobar
// que la imagen exportada sale con la piel de la marca. Solo usa lo que trae
// Node 22 (WebSocket incluido) y el protocolo de depuración del navegador.
//
//   node herramientas/exportar.mjs <chrome> <dibujo.html> <carpeta-de-descargas>
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [chrome, html, destino] = process.argv.slice(2);
if (!chrome || !html || !destino) {
  console.error('Uso: node herramientas/exportar.mjs <chrome> <dibujo.html> <carpeta-de-descargas>');
  process.exit(2);
}
fs.mkdirSync(destino, { recursive: true });
const perfil = fs.mkdtempSync(path.join(path.dirname(path.resolve(destino)), 'perfil-'));
const proceso = spawn(chrome, ['--no-sandbox', '--disable-gpu', '--remote-debugging-port=0',
  `--user-data-dir=${perfil}`, '--window-size=1440,900', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });

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
canal.addEventListener('message', (e) => {
  const mensaje = JSON.parse(e.data);
  if (mensaje.id && pendientes.has(mensaje.id)) {
    pendientes.get(mensaje.id)(mensaje);
    pendientes.delete(mensaje.id);
  }
});
const enviar = (method, params = {}, sessionId) => new Promise((listo) => {
  siguiente += 1;
  pendientes.set(siguiente, listo);
  canal.send(JSON.stringify({ id: siguiente, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const esperar = (ms) => new Promise((listo) => setTimeout(listo, ms));

let fallas = 0;
try {
  await enviar('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: path.resolve(destino) });
  const { result: { targetId } } = await enviar('Target.createTarget', { url: pathToFileURL(path.resolve(html)).href });
  const { result: { sessionId } } = await enviar('Target.attachToTarget', { targetId, flatten: true });
  await esperar(2500);
  for (const formato of ['png', 'svg']) {
    const antes = new Set(fs.readdirSync(destino));
    await enviar('Runtime.evaluate', {
      awaitPromise: true,
      expression: `(async () => {
        document.querySelector('#btn-export').click();
        await new Promise((r) => setTimeout(r, 400));
        document.querySelector('[data-format="${formato}"]').click();
      })()`,
    }, sessionId);
    let nuevo = null;
    for (let i = 0; i < 60 && !nuevo; i += 1) {
      await esperar(250);
      nuevo = fs.readdirSync(destino).find((f) => !antes.has(f) && !f.endsWith('.crdownload'));
    }
    if (nuevo) {
      console.log(`${formato}: ${path.join(destino, nuevo)}`);
    } else {
      console.log(`${formato}: no se descargó nada`);
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
