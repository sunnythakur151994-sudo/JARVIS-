#!/bin/bash
# Build the JARVIS Music Shorts Factory desktop apps (Windows / Linux / macOS).
# Node runtimes come from the nodejs-wheel-binaries wheel (extracted in tools/).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools/ext"
APP="$ROOT/apps/desktop"
DIST="$ROOT/dist"
VER="1.0.0"

echo "== installing app dependencies (exact package-lock) =="
cp "$APP/package.json" "$APP/package-lock.json" /tmp/ 2>/dev/null || true
( cd "$APP" && npm ci --no-audit --no-fund )

build_one () {
  local plat="$1" nodebin="$2" launcher="$3"
  local out="$DIST/JARVIS-MusicShortsFactory-$plat"
  echo "== assembling $plat =="
  rm -rf "$out"; mkdir -p "$out/node/bin"
  cp -r "$APP/node_modules" "$out/node_modules"
  cp "$APP/package.json" "$APP/index.js" "$APP/README-DESKTOP.txt" "$APP/.env.example" "$out/"
  cp -r "$APP/ui" "$out/ui"
  cp "$nodebin" "$out/node/bin/"
  chmod +x "$out/node/bin/"* 2>/dev/null || true
  cp "$APP/$launcher" "$out/"
  chmod +x "$out/$launcher" 2>/dev/null || true
  echo "JARVIS Music Shorts Factory desktop v$VER ($plat) built $(date -u +%Y-%m-%d)" > "$out/BUILD-INFO.txt"
}

build_one "win64"   "$TOOLS/node-win/nodejs_wheel/node.exe"                "JARVIS-ShortsFactory.bat"
build_one "linux64" "$TOOLS/node-linux/nodejs_wheel/bin/node"              "JARVIS-ShortsFactory.sh"
build_one "mac-x64" "$TOOLS/node-mac/nodejs_wheel/bin/node"                "JARVIS-ShortsFactory.command"

echo "== zipping =="
cd "$DIST"
for d in JARVIS-MusicShortsFactory-win64 JARVIS-MusicShortsFactory-linux64 JARVIS-MusicShortsFactory-mac-x64; do
  rm -f "$d.zip"
  if command -v zip >/dev/null 2>&1; then
    zip -qr "$d.zip" "$d"
  else
    python3 -c "
import shutil, sys
shutil.make_archive('$d', 'zip', '.', '$d')
"
  fi
  ls -la "$d.zip"
done
echo "== desktop builds done =="
