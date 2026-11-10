from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from ..db import conn

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

@router.post("/fill")
def fill(channel_id: str, days: int = 30):
    """Assign ready media to open slots. Genre-matched first, weighted fallback."""
    with conn() as c:
        c.execute("select local_time, weekday_mask, genre_id from slots where channel_id=%s", (channel_id,))
        slots = c.fetchall()
        c.execute("select coalesce(publish_lead_h,26) h from settings where channel_id=%s", (channel_id,))
        row = c.fetchone()
        lead = (row or {}).get("h", 26)

        placed = 0
        start = datetime.now(timezone.utc) + timedelta(hours=lead)
        for d in range(days):
            day = start + timedelta(days=d)
            for s in slots:
                if not (s["weekday_mask"] >> day.weekday()) & 1:
                    continue
                c.execute("""select id from media where channel_id=%s and status='ready'
                             and genre_id=%s and scheduled_at is null
                             order by created_at limit 1""", (channel_id, s["genre_id"]))
                m = c.fetchone()
                if not m:  # fallback to highest-weight genre with stock
                    c.execute("""select m.id from media m join genres g on g.id=m.genre_id
                                 where m.channel_id=%s and m.status='ready'
                                 and m.scheduled_at is null
                                 order by g.weight desc, m.created_at limit 1""", (channel_id,))
                    m = c.fetchone()
                if not m:
                    continue
                ts = datetime.combine(day.date(), s["local_time"], tzinfo=timezone.utc)
                c.execute("update media set status='scheduled', scheduled_at=%s where id=%s",
                          (ts, m["id"]))
                c.execute("insert into upload_log (media_id,from_state,to_state,note,actor) "
                          "values (%s,'ready','scheduled',%s,'scheduler')",
                          (m["id"], f"slot {s['local_time']}"))
                placed += 1
    return {"placed": placed}
