from fastapi import APIRouter
from ..db import conn
from ..state import advance

router = APIRouter(prefix="/api/media", tags=["media"])

@router.get("/ledger")
def ledger(channel_id: str, status: str | None = None, limit: int = 100):
    q = ("select m.*, s.handle, g.slug genre from media m "
         "join source_profiles s on s.id=m.source_profile_id "
         "join genres g on g.id=m.genre_id where m.channel_id=%s")
    args = [channel_id]
    if status:
        q += " and m.status=%s"; args.append(status)
    q += " order by m.created_at desc limit %s"; args.append(limit)
    with conn() as c:
        c.execute(q, args)
        return c.fetchall()

@router.get("/summary")
def summary(channel_id: str):
    """The counter you actually look at: posted vs pending vs dead."""
    with conn() as c:
        c.execute("""select status, count(*) from media
                     where channel_id=%s group by status""", (channel_id,))
        rows = {r["status"]: r["count"] for r in c.fetchall()}
    posted = rows.get("published", 0)
    pending = sum(v for k, v in rows.items()
                  if k in {"queued","downloaded","ready","scheduled","transforming"})
    return {"published": posted, "pending": pending,
            "dead": rows.get("rejected", 0) + rows.get("duplicate", 0),
            "failed": rows.get("failed", 0), "raw": rows}

@router.post("/{media_id}/skip")
def skip(media_id: str):
    with conn() as c:
        advance(c, media_id, "skipped", "manual", "api")
    return {"ok": True}
