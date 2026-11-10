/**
 * JARVIS — Music Shorts Factory · Desktop app server
 * Serves the control-center UI and proxies /api to the Shorts Factory engine.
 * Runs on the exact dependency set declared in package.json (express, socket.io,
 * node-fetch, dotenv). The engine code (music-shorts-factory) is used unmodified.
 */
'use strict';

require('dotenv').config();

const path = require('path');
const http = require('http');
const { spawn } = require('child_process');
const express = require('express');
const { Server } = require('socket.io');

const PORT = parseInt(process.env.PORT || '8787', 10);
const FACTORY_URL = (process.env.FACTORY_URL || 'http://localhost:8000').replace(/\/+$/, '');
const OPEN_BROWSER = process.env.NO_BROWSER !== '1';

const app = express();
const server = http.createServer(app);
const io = new Server(server);

let lastStatus = { online: false, factory: FACTORY_URL, at: null };

/* ---------------------------------------------------------------- *
 * Proxy /api -> FACTORY_URL/api  (node-fetch keeps streaming simple)
 * ---------------------------------------------------------------- */
app.use('/api', async (req, res) => {
  const target = FACTORY_URL + req.originalUrl;
  try {
    const fetch = (await import('node-fetch')).default;
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
 * Static UI + live status channel
 * ---------------------------------------------------------------- */
app.use(express.static(path.join(__dirname, 'ui')));

async function pingFactory() {
  try {
    const fetch = (await import('node-fetch')).default;
    const r = await fetch(FACTORY_URL + '/api/media/summary?channel_id=00000000-0000-0000-0000-000000000000', {
      method: 'GET',
      signal: AbortSignal.timeout ? AbortSignal.timeout(6000) : undefined,
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
