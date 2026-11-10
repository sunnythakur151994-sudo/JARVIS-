import asyncio
from ..db import conn
from ..services import ytdlp, scoring
from ..config import settings

async def run(channel_id: str):
    """One pass per genre per day. Costs 1 YouTube search unit per query."""
    with conn() as c:
        c.execute("select id, slug, seed_queries, hashtags from genres "
                  "where channel_id=%s and weight>0", (channel_id,))
        genres = c.fetchall()

    for g in genres:
        for q in g["seed_queries"][:3]:
            try:
                dump = await ytdlp.profile_dump(
                    f"https://www.youtube.com/results?search_query={q}&sp=EgIYAQ%253D%253D",
                    None, limit=15)
            except Exception:
                continue
            for e in dump.get("entries") or []:
                url = e.get("url") or ""
                if "/@" not in url:
                    continue
                handle = url.split("/@")[1].split("/")[0]
                try:
                    prof = await ytdlp.profile_dump(
                        f"https://www.youtube.com/@{handle}/shorts", None, limit=10)
                except Exception:
                    continue
                total, _ = scoring.score_profile(prof, g["hashtags"] + [g["slug"]])
                with conn() as c:
                    c.execute("""
                        insert into source_profiles
                          (genre_id, platform, handle, profile_url, followers,
                           avg_views, score, status)
                        values (%s,'youtube',%s,%s,%s,%s,%s,%s)
                        on conflict (genre_id, platform, handle) do update
                        set followers=excluded.followers, avg_views=excluded.avg_views,
                            score=excluded.score""",
                        (g["id"], handle, f"https://www.youtube.com/@{handle}",
                         prof.get("channel_follower_count"),
                         scoring.statistics.mean([e.get("view_count") or 0
                           for e in prof.get("entries") or []]) if prof.get("entries") else 0,
                         total, scoring.verdict(total)))
                await asyncio.sleep(settings.sleep_requests)
