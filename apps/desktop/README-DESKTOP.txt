JARVIS - MUSIC SHORTS FACTORY  (desktop app v1.0)
=================================================

WHAT THIS IS
  The control-center app for the Music Shorts Factory engine
  (music-shorts-factory, used unmodified). One single executable
  contains everything: the dashboard UI, the local server and the
  whole runtime. Nothing to install.

HOW TO RUN
  Windows : double-click  JARVIS-ShortsFactory.exe
  Linux   : run           ./JARVIS-ShortsFactory
  macOS   : double-click  JARVIS-ShortsFactory  (or run it from Terminal)

  The app window opens automatically in your default browser
  (Edge app mode on Windows). If it does not, open:
      http://localhost:8787/

CONFIG (optional .env next to the executable)
  FACTORY_URL  where the Shorts Factory engine runs
               (default http://localhost:8000)
  PORT         dashboard port (default 8787)

THE ENGINE
  The factory engine is the Python project in music-shorts-factory/.
  Start it with docker (docker compose up) or:
      uvicorn app.main:app --host 0.0.0.0 --port 8000
  plus a PostgreSQL database (db/schema.sql) and a .env file
  (see .env.example in that folder).

  Then open the app, set FACTORY_URL + your Channel ID, and press
  "Test & Connect".

PHONE / TABLET
  The Android app (JARVIS-MusicShortsFactory.apk) can point at this
  desktop app (http://<your-ip>:8787) or directly at the engine URL.
