from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from ..db import conn
from ..services import ytdlp

router = APIRouter(prefix="/api/sources", tags=["sources"])

@router.get("/candidates")
def candidates(genre_id: str):
    with conn() as c:
        c.execute("select * from source_profiles where genre_id=%s "
                  "and status='candidate' order by score desc", (genre_id,))
        return c.fetchall()

@router.post("/{profile_id}/approve")
def approve(profile_id: str):
    with conn() as c:
        c.execute("update source_profiles set status='approved' where id=%s", (profile_id,))
    return {"ok": True}

class ViewerReq(BaseModel):
    url: HttpUrl
    profile_id: str | None = None

@router.post("/view")
async def view(req: ViewerReq):
    """Paste a channel ID or URL. Returns the live profile page plus your ledger."""
    cookie = None
    if req.profile_id:
        with conn() as c:
            c.execute("select cookie_path from source_profiles where id=%s",
                      (req.profile_id,))
            r = c.fetchone()
            cookie = r["cookie_path"] if r else None
    try:
        dump = await ytdlp.profile_dump(str(req.url), cookie, limit=24)
    except Exception as e:
        raise HTTPException(502, str(e))

    ids = [e.get("id") for e in dump.get("entries") or [] if e.get("id")]
    ledger = {}
    if ids:
        with conn() as c:
            c.execute("""select source_video_id, status, scheduled_at, yt_video_id
                         from media where source_video_id = any(%s)""", (ids,))
            ledger = {r["source_video_id"]: r for r in c.fetchall()}

    return {
        "handle": dump.get("uploader") or dump.get("id"),
        "avatar": dump.get("thumbnail"),
        "bio": dump.get("description"),
        "followers": dump.get("channel_follower_count"),
        "verified": dump.get("channel_is_verified", False),
        "items": [{
            "id": e.get("id"),
            "title": e.get("title"),
            "thumb": e.get("thumbnail"),
            "views": e.get("view_count"),
            "duration": e.get("duration"),
            "url": e.get("url") or e.get("webpage_url"),
            "state": (ledger.get(e.get("id")) or {}).get("status", "not-uploaded"),
            "scheduled_at": (ledger.get(e.get("id")) or {}).get("scheduled_at"),
            "yt_video_id": (ledger.get(e.get("id")) or {}).get("yt_video_id"),
        } for e in dump.get("entries") or []],
    }
