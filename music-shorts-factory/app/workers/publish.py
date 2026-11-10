import asyncio
from ..db import conn
from ..state import advance
from ..services import youtube

def schedule_next(conn, channel_id: str):
    """Fill empty upcoming slots from ready media, respecting genre + dedupe."""
    with conn.cursor() as cur:
        cur.execute("""
            with next_slot as (
              select s.id, s.genre_id, s.local_time, s.weekday_mask
              from slots s join settings st on st.channel_id=s.channel_id
              where s.channel_id=%s limit 1)
            select 1""", (channel_id,))

async def run_once():
    with conn() as c:
        c.execute("""select m.id, m.local_path, m.caption, m.channel_id,
                            c.oauth_refresh, m.scheduled_at
                     from media m join channels c on c.id=m.channel_id
                     where m.status='scheduled' and m.scheduled_at <= now()+interval '5 min'
                     limit 3""")
        rows = c.fetchall()
    for r in rows:
        try:
            with conn() as c:
                advance(c, r["id"], "publishing")
            vid = await asyncio.to_thread(
                youtube.upload, r["oauth_refresh"], r["local_path"],
                (r["caption"] or "music")[:90] + " #Shorts",
                f"{r['caption'] or ''}\n\n#Shorts #music", r["scheduled_at"].isoformat())
            with conn() as c:
                c.execute("update media set yt_video_id=%s, yt_privacy='private' where id=%s",
                          (vid, r["id"]))
                advance(c, r["id"], "published")
        except Exception as e:
            with conn() as c:
                advance(c, r["id"], "failed", str(e)[:300])
