#!/bin/bash
# Assemble the self-contained Shorts Factory engine into the desktop bundles.
#   Windows: embeddable CPython 3.12 (pypi python-embed) + site-packages (win wheels)
#   Linux/macOS: engine source + first-run pip installer (run.sh)
# The engine code (music-shorts-factory/) is copied UNMODIFIED.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
SRC="$ROOT/music-shorts-factory"
WRAP="$ROOT/apps/engine"
REQ="$WRAP/requirements-engine.txt"

fill_engine_common () {
  local ENG="$1"
  mkdir -p "$ENG"
  cp -r "$SRC/app" "$SRC/db" "$ENG/"
  cp "$WRAP/boot.py" "$WRAP/run.sh" "$WRAP/seed_sources.py" "$REQ" "$ENG/"
  chmod +x "$ENG/run.sh"
  rm -rf "$ENG/__pycache__"
}

echo "== engine (linux64: first-run pip installer) =="
fill_engine_common "$DIST/JARVIS-MusicShortsFactory-linux64/engine"
cp "$WRAP/run.sh" "$DIST/JARVIS-MusicShortsFactory-linux64/engine/"

echo "== engine (mac-x64: first-run pip installer) =="
fill_engine_common "$DIST/JARVIS-MusicShortsFactory-mac-x64/engine"

echo "== engine (win64: bundled python + site-packages) =="
ENG="$DIST/JARVIS-MusicShortsFactory-win64/engine"
fill_engine_common "$ENG"
cp "$WRAP/start-factory.bat" "$ENG/"

# embeddable Windows CPython 3.12 from pypi 'python-embed'
if [ ! -d "$ENG/python" ]; then
  echo "   fetching embeddable python 3.12 ..."
  mkdir -p /tmp/pyembed && cd /tmp/pyembed
  curl -sS -o py.tgz "$(curl -sS https://pypi.org/pypi/python-embed/json | python3 -c "
import json,sys
d=json.load(sys.stdin)
best=[v for v in d['releases'] if v.startswith('3.12')]
best.sort()
for f in d['releases'][best[-1]]:
    if f['filename'].endswith('.tar.gz'):
        print(f['url']); break
")"
  tar xzf py.tgz
  DZ=$(find . -name data.zip | head -1)
  mkdir -p "$ENG/python" /tmp/pyembed/out
  python3 -c "
import zipfile, shutil, glob, os
zipfile.ZipFile('$DZ').extractall('/tmp/pyembed/out')
src = glob.glob('/tmp/pyembed/out/cp312*')[0]
for f in os.listdir(src):
    shutil.move(os.path.join(src, f), '$ENG/python/')
"
  printf 'python312.zip\n.\n../site-packages\nimport site\n' > "$ENG/python/python312._pth"
fi

echo "   installing engine dependencies (win_amd64 / cp312 wheels) ..."
python3 -m pip install -q --target "$ENG/site-packages" \
  --platform win_amd64 --python-version 3.12 --only-binary=:all: \
  -r "$WRAP/requirements-win.txt" 2>&1 | tail -2 || true

echo "   slimming site-packages ..."
rm -rf "$ENG/site-packages/bin" 2>/dev/null || true
# googleapiclient's cached discovery documents are ~70MB and fetched at runtime if absent
rm -rf "$ENG/site-packages/googleapiclient/discovery_cache" 2>/dev/null || true
find "$ENG/site-packages" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$ENG/site-packages" -name "*.pyc" -delete 2>/dev/null || true
find "$ENG/site-packages" -name "*.pyi" -delete 2>/dev/null || true

echo "== engine bundles done =="
du -sh "$DIST"/*/engine
