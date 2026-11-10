#!/bin/sh
# JARVIS engine (Linux/macOS) — uses the bundled python if present, else system python3.
# First run installs the engine components into ./site-packages (needs internet once).
cd "$(dirname "$0")"
if [ -x python/bin/python3 ]; then
  PYTHON=python/bin/python3
else
  PYTHON=python3
fi
if [ ! -d site-packages/fastapi ]; then
  echo "[engine] installing components (first run, needs internet) ..."
  "$PYTHON" -m pip install --target site-packages -r requirements-engine.txt || {
    echo "[engine] pip install failed - check your internet connection and try again";
    exit 1;
  }
fi
export PYTHONPATH="$(pwd)/site-packages${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" boot.py
