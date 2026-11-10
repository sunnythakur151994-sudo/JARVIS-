/**
 * JARVIS — Music Shorts Factory · Desktop app server
 * Serves the control-center UI and proxies /api to the Shorts Factory engine.
 * Runs on the exact dependency set declared in package.json (express, socket.io,
 * dotenv). The engine code (music-shorts-factory) is used unmodified.
 *
 * This file is also the entry point embedded into the single-file
 * JARVIS-ShortsFactory executable (Node SEA): UI and socket.io client are
 * embedded as strings at build time (gen/embedded.js), with on-disk fallback
 * for development runs.
 */
'use strict';

require('dotenv').config();

const path = require('path');
const http = require('http');
const fs = require('fs');
const { spawn } = require('child_process');
const express = require('express');
const { Server } = require('socket.io');

const PORT = parseInt(process.env.PORT || '8787', 10);
const FACTORY_URL = (process.env.FACTORY_URL || 'http://localhost:8000').replace(/\/+$/, '');
const OPEN_BROWSER = process.env.NO_BROWSER !== '1';

/* ---- embedded assets (build-time), with dev fallbacks ---- */
let UI_FILES = null;          // { 'index.html': '<!DOCTYPE ...', ... }
let SOCKET_IO_CLIENT = null;  // socket.io client bundle source
try { ({ UI_FILES, SOCKET_IO_CLIENT } = require('./gen/embedded.js')); } catch (e) { /* dev mode */ }

function uiFile(name) {
  if (UI_FILES && UI_FILES[name] != null) return UI_FILES[name];
  try { return fs.readFileSync(path.join(__dirname, 'ui', name), 'utf8'); } catch (e) { return null; }
}
function socketIoClientSource() {
  if (SOCKET_IO_CLIENT) return SOCKET_IO_CLIENT;
  try { return fs.readFileSync(require.resolve('socket.io/client-dist/socket.io.js'), 'utf8'); }
  catch (e) { return null; }
}

const app = express();
const server = http.createServer(app);
const io = new Server(server, { serveClient: false });

let lastStatus = { online: false, factory: FACTORY_URL, at: null };

/* ---------------------------------------------------------------- *
 * Proxy /api -> FACTORY_URL/api  (global fetch — Node 18+)
 * ---------------------------------------------------------------- */
app.use('/api', async (req, res) => {
  const target = FACTORY_URL + req.originalUrl;
  try {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);
    const headers = {};
    if (req.headers['content-type']) headers['content-type'] = req.headers['content-type'];
    if (body.length) headers['content-length'] = body.length;

    const r = await fetch(target, {
      method: req.method,
      headers,
      body: body.length ? body : undefined,
      redirect: 'manual',
    });
    res.status(r.status);
    const ct = r.headers.get('content-type');
    if (ct) res.set('content-type', ct);
    const buf = Buffer.from(await r.arrayBuffer());
    lastStatus.online = true;
    res.send(buf);
  } catch (e) {
    lastStatus.online = false;
    res.status(502).json({
      error: 'factory unreachable',
      detail: 'factory unreachable: ' + (e && e.cause && e.cause.message ? e.cause.message : String(e)),
      target,
    });
  }
});

/* ---------------------------------------------------------------- *
 * socket.io client + UI (embedded first, disk fallback)
 * ---------------------------------------------------------------- */
app.get('/jarvis-socketio.js', (req, res) => {
  const src = socketIoClientSource();
  if (!src) return res.status(404).end();
  res.set('content-type', 'application/javascript; charset=utf-8').send(src);
});
app.get('/', (req, res) => {
  const html = uiFile('index.html');
  if (!html) return res.status(404).send('UI not found');
  res.set('content-type', 'text/html; charset=utf-8').send(html);
});
app.get('/app.js', (req, res) => {
  const src = uiFile('app.js');
  if (!src) return res.status(404).end();
  res.set('content-type', 'application/javascript; charset=utf-8').send(src);
});
app.get('/style.css', (req, res) => {
  const src = uiFile('style.css');
  if (!src) return res.status(404).end();
  res.set('content-type', 'text/css; charset=utf-8').send(src);
});

/* ---------------------------------------------------------------- *
 * Live status channel
 * ---------------------------------------------------------------- */
async function pingFactory() {
  try {
    await fetch(FACTORY_URL + '/api/media/summary?channel_id=00000000-0000-0000-0000-000000000000', {
      method: 'GET',
      signal: AbortSignal.timeout(6000),
    });
    lastStatus = { online: true, factory: FACTORY_URL, at: Date.now() };
  } catch (e) {
    lastStatus = { online: false, factory: FACTORY_URL, at: Date.now() };
  }
  return lastStatus;
}

io.on('connection', (socket) => {
  socket.emit('status', lastStatus);
});
setInterval(async () => { io.emit('status', await pingFactory()); }, 15000);

/* ---------------------------------------------------------------- *
 * Start
 * ---------------------------------------------------------------- */
function openBrowser() {
  if (!OPEN_BROWSER) return;
  const url = 'http://localhost:' + PORT + '/';
  const cmds = {
    win32: ['cmd', ['/c', 'start', 'msedge', '--app=' + url]],
    darwin: ['open', [url]],
    linux: ['xdg-open', [url]],
  };
  const pick = cmds[process.platform] || cmds.linux;
  try {
    const child = spawn(pick[0], pick[1], { detached: true, stdio: 'ignore' });
    child.on('error', () => {
      if (process.platform === 'win32') {
        spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' }).on('error', () => {});
      }
    });
    child.unref();
  } catch (e) { /* browser is a convenience only */ }
}

server.listen(PORT, '0.0.0.0', async () => {
  console.log('==========================================================');
  console.log('  JARVIS - Music Shorts Factory (desktop)');
  console.log('  UI      : http://localhost:' + PORT + '/');
  console.log('  Engine  : ' + FACTORY_URL);
  console.log('  Config  : .env  (PORT, FACTORY_URL, NO_BROWSER)');
  console.log('==========================================================');
  await pingFactory();
  io.emit('status', lastStatus);
  console.log(lastStatus.online ? '  engine reachable' : '  engine NOT reachable (start music-shorts-factory / docker compose)');
  openBrowser();
});
