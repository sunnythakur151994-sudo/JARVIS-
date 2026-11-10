"""
JARVIS engine boot — starts the Shorts Factory engine (music-shorts-factory,
code unmodified) with a self-contained PostgreSQL server (pgserver):

  1. starts an embedded Postgres in ./factory-data/pg
  2. writes .env (auto-generated Fernet key; YouTube credentials preserved)
  3. applies db/schema.sql on first run
  4. serves the FastAPI app on 0.0.0.0:8000
  5. exits cleanly when the desktop app closes (stdin EOF)
"""
import os
import sys
import time
import threading
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
DATA = ENGINE / "factory-data"
DATA.mkdir(exist_ok=True)
(ENGINE / "storage").mkdir(exist_ok=True)
(ENGINE / "cookies").mkdir(exist_ok=True)

print("[boot] starting embedded PostgreSQL ...")
try:
    import pgserver  # noqa: E402
except ImportError:
    print("[boot] installing engine components (first run, needs internet) ...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--target", str(ENGINE / "site-packages"),
        "-r", str(ENGINE / "requirements-engine.txt"),
    ])
    sys.path.insert(0, str(ENGINE / "site-packages"))
    import pgserver  # noqa: E402

pg = pgserver.get_server(str(DATA / "pg"), cleanup_mode="stop")
uri = pg.get_uri()
print("[boot] database:", uri)

# ---- environment for the unmodified engine ----
os.environ["DATABASE_URL"] = uri
os.environ["STORAGE_ROOT"] = str(ENGINE / "storage")
os.environ["COOKIE_ROOT"] = str(ENGINE / "cookies")

env_path = ENGINE / ".env"
existing = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            existing[k.strip()] = v.strip()

if not existing.get("FERNET_KEY"):
    try:
        from cryptography.fernet import Fernet
        existing["FERNET_KEY"] = Fernet.generate_key().decode()
    except Exception:
        import base64, os as _os
        existing["FERNET_KEY"] = base64.urlsafe_b64encode(_os.urandom(32)).decode()

values = {
    "DATABASE_URL": uri,
    "STORAGE_ROOT": os.environ["STORAGE_ROOT"],
    "COOKIE_ROOT": os.environ["COOKIE_ROOT"],
    "FERNET_KEY": existing.get("FERNET_KEY", ""),
    "YT_CLIENT_ID": existing.get("YT_CLIENT_ID", ""),
    "YT_CLIENT_SECRET": existing.get("YT_CLIENT_SECRET", ""),
    "YT_REDIRECT_URI": existing.get("YT_REDIRECT_URI", "http://localhost:8787/jarvis/callback"),
}
env_path.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
for k, v in values.items():
    if v:
        os.environ[k] = v
# the engine requires these even when empty
os.environ.setdefault("YT_CLIENT_ID", values["YT_CLIENT_ID"])
os.environ.setdefault("YT_CLIENT_SECRET", values["YT_CLIENT_SECRET"])

# ---- compatibility shim (engine code unmodified) ----
# The engine calls fetchall()/fetchone() on psycopg connections; psycopg3
# cursors have those methods but connections don't. Bridge them here so the
# original code runs without any change.
import psycopg  # noqa: E402

_psycopg_execute = psycopg.Connection.execute
def _execute(self, query, params=None, **kw):
    cur = _psycopg_execute(self, query, params, **kw)
    self._last_cur = cur
    return cur
psycopg.Connection.execute = _execute
psycopg.Connection.fetchall = lambda self: self._last_cur.fetchall()
psycopg.Connection.fetchone = lambda self: self._last_cur.fetchone()
psycopg.Connection.fetchmany = lambda self, n=None: self._last_cur.fetchmany(n)

# ---- apply schema.sql on first run (unmodified) ----

with psycopg.connect(uri, autocommit=True) as c:
    has_tables = c.execute("select to_regclass('public.channels')").fetchone()[0]
    if not has_tables:
        print("[boot] applying db/schema.sql ...")
        sql = (ENGINE / "db" / "schema.sql").read_text()
        try:
            c.execute(sql)
        except Exception as e:
            if "pgcrypto" in str(e).lower():
                # pgserver may not ship contrib; gen_random_uuid() is core in PG13+
                print("[boot] pgcrypto unavailable, applying schema without the extension line")
                filtered = "\n".join(
                    l for l in sql.splitlines() if "create extension" not in l.lower()
                )
                c.execute(filtered)
            else:
                raise
        print("[boot] schema ready")

# ---- run the API; exit when the desktop app closes (stdin EOF) ----
import uvicorn  # noqa: E402

# ---- keep genre source-profiles seeded (idempotent, engine code unmodified) ----
import seed_sources  # noqa: E402

def _seed_loop():
    last = None
    while True:
        try:
            stats = seed_sources.apply(uri)
            if stats != last and stats.get("profiles"):
                print(f"[boot] sources seeded for {stats['channels']} channel(s): "
                      f"{stats['genres']} genres, {stats['profiles']} profiles")
            last = stats
        except Exception as e:
            print("[boot] seed error:", e)
        time.sleep(20)

threading.Thread(target=_seed_loop, daemon=True).start()

port = int(os.environ.get("ENGINE_PORT", "8000"))
config = uvicorn.Config("app.main:app", host="0.0.0.0", port=port, log_level="warning")
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
print(f"[boot] Shorts Factory API ready on http://0.0.0.0:{port}")

try:
    sys.stdin.read()  # blocks until the parent app closes the pipe
except Exception:
    while thread.is_alive():
        time.sleep(2)
print("[boot] shutting down ...")
server.should_exit = True
try:
    pg.cleanup()
except Exception:
    pass
