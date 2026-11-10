# JARVIS — Music Shorts Factory · App Builds

Installable apps built **from the `music-shorts-factory` project (Google Drive) without
changing its code**. The engine lives untouched in `music-shorts-factory/`; the apps in
`apps/` are thin shells around it (dashboard + launcher), built only from the attached
`jarvis-ai` dependency set (express, socket.io, node-fetch, dotenv).

## Deliverables (in `dist/`)

| File | What it is |
|---|---|
| `JARVIS-MusicShortsFactory.apk` | Android app (mobile) — WebView dashboard, signed v2+v3, min SDK 24 |
| `JARVIS-MusicShortsFactory-win64.zip` | Windows desktop app — unzip, double-click **`JARVIS-ShortsFactory.exe`** |
| `JARVIS-MusicShortsFactory-linux64.zip` | Linux desktop app — unzip, run `./JARVIS-ShortsFactory` |
| `JARVIS-MusicShortsFactory-mac-x64.zip` | macOS desktop app — unzip, run `JARVIS-ShortsFactory` |
| `JARVIS-ShortsFactory-win64.exe` | The bare Windows executable (also inside the win64 zip) |

Each desktop app is a **single-file executable** (Node SEA): the UI, the server and
the whole runtime are baked into one binary — nothing to install, just double-click.
The APK and desktop apps share one UI (`apps/ui/`) and talk to the factory API
(the Python service in `music-shorts-factory/`).

## The engine (unmodified)

`music-shorts-factory/` is exactly the code from `music-shorts-factory.zip` on Google
Drive: FastAPI API + Postgres schema + workers (discover → ingest → transform → publish).
Run it with `docker compose up` (or `uvicorn app.main:app --port 8000` + PostgreSQL
initialized from `db/schema.sql`) and a `.env` (see `.env.example` in that folder).

## Rebuilding

```
./scripts/build-desktop.sh   # Windows / Linux / macOS bundles -> dist/
./scripts/build-apk.sh       # Android APK -> dist/
```

Toolchain (all vendored in `tools/` / `apps/desktop-build/`, downloaded from PyPI/npm):
* `jdk4py` (Temurin JDK) — keytool + runtime for apktool/apksigner
* `apktool 2.9.3` (from npm `@postar/apktool-node`) — APK assembly from smali + resources
* `apksigner` (from npm `@postar/apktool-node`) — v2/v3 signing, debug keystore generated on first build
* `nodejs-wheel-binaries` (PyPI) — Node 24 runtimes bundled into the desktop executables
* `esbuild` + `postject` (npm) — bundle the server and bake it into the single-file executables

## App usage

1. Start the engine (docker compose up in `music-shorts-factory/`).
2. Open the app → set **Factory server URL** (e.g. `http://localhost:8000`, or the
   desktop app's `http://<pc-ip>:8787` from the phone) and your **Channel ID**.
3. Press **Test & Connect** — summary, ledger, scheduling and source scouting appear.

The Android app is signed with a generated debug-style keystore for sideloading
(enable "Install unknown apps" for your browser/file manager). For Play Store
distribution, re-sign `dist/JARVIS-MusicShortsFactory-unsigned.apk` with your own key
(`scripts/build-apk.sh` shows the exact apksigner command).
