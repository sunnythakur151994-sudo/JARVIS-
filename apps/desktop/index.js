/**
 * JARVIS — Music Shorts Factory · Desktop app server
 * - Serves the control-center UI (embedded into the executable)
 * - Proxies /api to the Shorts Factory engine
 * - AUTO-STARTS the bundled engine (boot.py: embedded Postgres + FastAPI)
 * - YouTube OAuth helper: saves client credentials, captures the callback,
 *   auto-fills the Channel ID.
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
let UI_FILES = null;
let SOCKET_IO_CLIENT = null;
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

/* ---- engine location + process management ---- */
function findEngineDir() {
  const candidates = [
    process.env.ENGINE_DIR,
    path.join(path.dirname(process.execPath), 'engine'),
    path.join(__dirname, 'engine'),
    path.join(process.cwd(), 'engine'),
    path.join(__dirname, '..', '..', 'engine'),
  ].filter(Boolean);
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, 'boot.py'))) return c;
  }
  return null;
}
const ENGINE_DIR = findEngineDir();
const engineIsLocal = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(FACTORY_URL);
let engineProc = null;
let engineState = ENGINE_DIR ? 'stopped' : 'not-bundled';

function enginePython() {
  if (ENGINE_DIR) {
    const win = path.join(ENGINE_DIR, 'python', 'python.exe');
    if (process.platform === 'win32' && fs.existsSync(win)) return win;
    const posix = path.join(ENGINE_DIR, 'python', 'bin', 'python3');
    if (fs.existsSync(posix)) return posix;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function startEngine() {
  if (!ENGINE_DIR || !engineIsLocal || process.env.NO_ENGINE === '1') return;
  if (engineProc) { try { engineProc.kill(); } catch (e) {} }
  const env = { ...process.env };
  const sp = path.join(ENGINE_DIR, 'site-packages');
  if (fs.existsSync(sp)) env.PYTHONPATH = sp + (env.PYTHONPATH ? path.delimiter + env.PYTHONPATH : '');
  console.log('  starting engine: ' + ENGINE_DIR);
  engineState = 'starting';
  let cmd, args;
  if (process.platform === 'win32') {
    cmd = enginePython();
    args = [path.join(ENGINE_DIR, 'boot.py')];
  } else {
    cmd = 'sh';
    args = [path.join(ENGINE_DIR, 'run.sh')];
  }
  engineProc = spawn(cmd, args, {
    cwd: ENGINE_DIR, env, stdio: ['pipe', 'pipe', 'pipe'],
  });
  const thisProc = engineProc;
  const tag = (d) => String(d).trim().split('\n').forEach(l => l && console.log('  [engine] ' + l));
  engineProc.stdout.on('data', tag);
  engineProc.stderr.on('data', tag);
  engineProc.on('exit', (code) => {
    if (engineProc !== thisProc) return; // a newer engine instance took over
    engineState = 'stopped';
    engineProc = null;
    console.log('  [engine] exited with code ' + code);
  });
  setTimeout(() => { if (engineProc) engineState = 'running'; }, 2500);
}

const app = express();
app.use(express.json());
const server = http.createServer(app);
const io = new Server(server, { serveClient: false });

let lastStatus = { online: false, factory: FACTORY_URL, at: null, engine: engineState };

/* ---------------------------------------------------------------- *
 * Proxy /api -> FACTORY_URL/api  (follows nothing; forwards redirects)
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
    // forward redirect targets (OAuth!) and content headers
    const loc = r.headers.get('location');
    if (loc) res.set('location', loc);
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
 * YouTube setup + OAuth callback capture
 * ---------------------------------------------------------------- */
function envFile() {
  return ENGINE_DIR ? path.join(ENGINE_DIR, '.env') : null;
}
function readEnvFile() {
  const p = envFile();
  if (!p || !fs.existsSync(p)) return {};
  const out = {};
  for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}
function writeEnvFile(updates) {
  const p = envFile();
  if (!p) throw new Error('bundled engine folder not found');
  const cur = readEnvFile();
  const merged = { ...cur, ...updates };
  const txt = Object.entries(merged).map(([k, v]) => k + '=' + v).join('\n') + '\n';
  fs.writeFileSync(p, txt);
  return merged;
}
function youtubeConfigured() {
  const e = readEnvFile();
  return !!(e.YT_CLIENT_ID && e.YT_CLIENT_ID.trim() && e.YT_CLIENT_ID.trim() !== '""');
}

app.post('/jarvis/setup/youtube', (req, res) => {
  try {
    const { client_id, client_secret } = req.body || {};
    if (!client_id || !client_secret) return res.status(400).json({ error: 'client_id and client_secret required' });
    writeEnvFile({
      YT_CLIENT_ID: client_id.trim(),
      YT_CLIENT_SECRET: client_secret.trim(),
      YT_REDIRECT_URI: 'http://localhost:' + PORT + '/jarvis/callback',
    });
    startEngine(); // restart so the engine picks up the credentials
    res.json({ ok: true, redirect_uri: 'http://localhost:' + PORT + '/jarvis/callback' });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

app.get('/jarvis/status', (req, res) => {
  res.json({
    engine_dir: ENGINE_DIR,
    engine: engineState,
    factory_online: lastStatus.online,
    youtube_configured: youtubeConfigured(),
    redirect_uri: 'http://localhost:' + PORT + '/jarvis/callback',
  });
});

app.get('/jarvis/genres', (req, res) => {
  try {
    const p = ENGINE_DIR ? path.join(ENGINE_DIR, 'genres.json') : null;
    if (!p || !fs.existsSync(p)) return res.json([]);
    res.json(JSON.parse(fs.readFileSync(p, 'utf8')));
  } catch (e) {
    res.json([]);
  }
});

app.get('/jarvis/callback', async (req, res) => {
  const code = req.query.code;
  if (!code) return res.status(400).send('Missing ?code= from Google');
  try {
    const r = await fetch(FACTORY_URL + '/api/channels/callback?code=' + encodeURIComponent(code));
    const text = await r.text();
    let data; try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 500) }; }
    if (!r.ok) return res.status(502).send('Engine error: ' + JSON.stringify(data));
    const channelId = data.channel_id;
    res.set('content-type', 'text/html; charset=utf-8').send(`<!DOCTYPE html><html><head>
<meta charset="utf-8"><title>YouTube connected</title>
<style>body{font-family:system-ui,sans-serif;background:#0b1020;color:#e8ecff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{background:#121a33;border:1px solid #24315c;border-radius:16px;padding:36px;text-align:center;max-width:520px}
h1{color:#22c55e;font-size:22px} code{display:block;background:#182347;border-radius:10px;padding:12px;margin:16px 0;font-size:13px;word-break:break-all}</style>
</head><body><div class="box">
<h1>✅ YouTube channel connected!</h1>
<p>Channel ID (saved automatically in the dashboard):</p>
<code>${channelId}</code>
<p style="color:#94a0c8;font-size:13px">You can close this window.</p>
</div>
<script>
try{ if(window.opener){ window.opener.postMessage({jarvisChannelId:${JSON.stringify(channelId)}}, '*'); } }catch(e){}
setTimeout(function(){ window.close(); }, 2500);
</script></body></html>`);
  } catch (e) {
    res.status(502).send('Could not reach engine: ' + String(e));
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

/* ---------------------------------------------------------------- *
 * Live status channel
 * ---------------------------------------------------------------- */
async function pingFactory() {
  try {
    await fetch(FACTORY_URL + '/api/media/summary?channel_id=00000000-0000-0000-0000-000000000000', {
      method: 'GET',
      signal: AbortSignal.timeout(6000),
    });
    lastStatus = { online: true, factory: FACTORY_URL, at: Date.now(), engine: engineState };
  } catch (e) {
    lastStatus = { online: false, factory: FACTORY_URL, at: Date.now(), engine: engineState };
  }
  return lastStatus;
}

io.on('connection', (socket) => {
  socket.emit('status', lastStatus);
});
setInterval(async () => { io.emit('status', await pingFactory()); }, 10000);

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
  console.log('  Engine folder : ' + (ENGINE_DIR || '(not bundled - set FACTORY_URL to a running engine)'));
  console.log('==========================================================');
  startEngine();
  await pingFactory();
  io.emit('status', lastStatus);
  console.log(lastStatus.online ? '  engine reachable' : '  engine not reachable yet (it may still be starting up)');
  openBrowser();
});
