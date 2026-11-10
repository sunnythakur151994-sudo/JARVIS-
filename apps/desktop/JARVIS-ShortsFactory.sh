#!/bin/sh
# JARVIS - Music Shorts Factory (Linux)
cd "$(dirname "$0")"
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example"; }
exec ./node/bin/node index.js
