import hashlib, asyncio
from pathlib import Path
from ..db import conn, claim
from ..state import advance
from ..services import ytdlp
from ..config import settings

WORKER = "ingest-1"

def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

async def run_once():
    with conn() as c:
        ids = claim(c, "media", 5, WORKER)
    for mid in ids:
        with conn() as c:
            c.execute("""select m.*, s.cookie_path, g.slug, m.channel_id ch
                         from media m join source_profiles s on s.id=m.source_profile_id
                         join genres g on g.id=m.genre_id where m.id=%s""", (mid,))
            m = c.fetchone()
        try:
            advance(conn().__enter__(), mid, "downloading") if False else None
            with conn() as c:
                advance(c, mid, "downloading")
            dest = Path(settings.storage_root) / m["ch"] / m["slug"] / "_incoming" / f"{mid}.mp4"
            await ytdlp.download(m["source_url"], m["cookie_path"], dest)
            h = sha256_of(dest)
            with conn() as c:
                c.execute("select id from media where sha256=%s and id<>%s and status<>'rejected'",
                          (h, mid))
                dup = c.fetchone()
                c.execute("update media set sha256=%s, local_path=%s, locked_at=null where id=%s",
                          (h, str(dest), mid))
                if dup:
                    advance(c, mid, "duplicate", f"matches {dup['id']}")
                else:
                    final = dest.parent.parent / f"{h[:8]}.mp4"
                    dest.rename(final)
                    c.execute("update media set local_path=%s where id=%s", (str(final), mid))
                    advance(c, mid, "downloaded")
        except Exception as e:
            with conn() as c:
                c.execute("update media set attempts=attempts+1, locked_at=null where id=%s", (mid,))
                advance(c, mid, "failed", str(e)[:300])
