@echo off
title JARVIS - Music Shorts Factory
cd /d "%~dp0"
if exist ".env" (
  echo Using .env configuration
) else (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example - edit FACTORY_URL if needed.
)
echo Starting JARVIS Music Shorts Factory...
node\bin\node.exe index.js
pause
