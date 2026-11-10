"""
Genre-wise source profile seed data for the Shorts Factory engine.

The engine code stays UNMODIFIED: this module only inserts rows into its
database (genres + source_profiles) the same way the discover worker would.
- genres are created for every channel that exists (idempotent)
- source_profiles are seeded as 'candidate' with the FULL profile URL in
  profile_url (yt-dlp needs a complete URL, not a bare handle)
- a profile the user has already approved is never downgraded
"""
import json
from pathlib import Path

ENGINE = Path(__file__).resolve().parent

# genre slug -> (label, seed_queries, hashtags)
GENRES = {
    "gossip":      ("Gossip",      ["celebrity gossip shorts", "pop culture news shorts", "celebrity news today"], ["gossip", "celebrity", "popculture", "news"]),
    "hiphop":      ("Hip-Hop",     ["hip hop shorts", "rap news shorts", "hip hop highlights"], ["hiphop", "rap", "music"]),
    "kpop":        ("K-Pop",       ["kpop shorts", "kpop news shorts", "kpop highlights"], ["kpop", "korean", "music"]),
    "bollywood":   ("Bollywood",   ["bollywood shorts", "bollywood news shorts", "bollywood gossip"], ["bollywood", "india", "music"]),
    "edm":         ("EDM",         ["edm shorts", "edm news shorts", "electronic music highlights"], ["edm", "dance", "music"]),
    "latin":       ("Latin",       ["reggaeton shorts", "latin music shorts", "latin urban"], ["latin", "reggaeton", "music"]),
    "indie":       ("Indie",       ["indie music shorts", "indie news shorts", "indie highlights"], ["indie", "music"]),
    "country":     ("Country",     ["country music shorts", "country news shorts"], ["country", "music"]),
    "charts":      ("Charts",      ["music charts shorts", "billboard hot 100 shorts"], ["charts", "billboard", "music"]),
    "memes":       ("Memes",       ["music memes shorts", "funny music shorts"], ["memes", "funny", "music"]),
    "popculture":  ("Pop Culture", ["pop culture shorts", "music news shorts"], ["popculture", "music", "news"]),
}

# (genre, platform, handle, profile_url) — full URLs, one per source
SOURCES = [
    # gossip
    ("gossip", "instagram", "popbase", "https://www.instagram.com/popbase/"),
    ("gossip", "instagram", "popcrave", "https://www.instagram.com/popcrave/"),
    ("gossip", "instagram", "deuxmoi", "https://www.instagram.com/deuxmoi/"),
    ("gossip", "instagram", "popehive", "https://www.instagram.com/popehive/"),
    ("gossip", "instagram", "chartdata.twt", "https://www.instagram.com/chartdata.twt/"),
    ("gossip", "instagram", "commentsbycelebs", "https://www.instagram.com/commentsbycelebs/"),
    ("gossip", "instagram", "theshaderoom", "https://www.instagram.com/theshaderoom/"),
    ("gossip", "instagram", "sainthoax", "https://www.instagram.com/sainthoax/"),
    ("gossip", "instagram", "hollywoodunlocked", "https://www.instagram.com/hollywoodunlocked/"),
    ("gossip", "instagram", "thepophive", "https://www.instagram.com/thepophive/"),  # official Pop Hive (confirmed)
    ("gossip", "instagram", "popehiveupdates", "https://www.instagram.com/popehiveupdates/"),  # unverified
    # hiphop
    ("hiphop", "instagram", "rap", "https://www.instagram.com/rap/"),
    ("hiphop", "instagram", "records", "https://www.instagram.com/records/"),
    ("hiphop", "instagram", "hiphopdx", "https://www.instagram.com/hiphopdx/"),
    ("hiphop", "instagram", "hiphop.talk", "https://www.instagram.com/hiphop.talk/"),
    ("hiphop", "instagram", "rap.updates_", "https://www.instagram.com/rap.updates_/"),
    ("hiphop", "instagram", "hiphopnewly", "https://www.instagram.com/hiphopnewly/"),
    ("hiphop", "instagram", "bars", "https://www.instagram.com/bars/"),  # unverified
    ("hiphop", "instagram", "concert", "https://www.instagram.com/concert/"),  # unverified
    ("hiphop", "instagram", "worldstar", "https://www.instagram.com/worldstar/"),
    # kpop
    ("kpop", "instagram", "allkpop", "https://www.instagram.com/allkpop/"),
    ("kpop", "instagram", "koreaboo", "https://www.instagram.com/koreaboo/"),
    ("kpop", "instagram", "panncafe", "https://www.instagram.com/panncafe/"),
    ("kpop", "instagram", "kpopnofficial", "https://www.instagram.com/kpopnofficial/"),
    ("kpop", "instagram", "todaykpopnews", "https://www.instagram.com/todaykpopnews/"),
    ("kpop", "instagram", "the.kpedia", "https://www.instagram.com/the.kpedia/"),
    # bollywood
    ("bollywood", "instagram", "instantbollywood", "https://www.instagram.com/instantbollywood/"),
    ("bollywood", "instagram", "bollywoodnow", "https://www.instagram.com/bollywoodnow/"),
    ("bollywood", "instagram", "bollyg0ssip", "https://www.instagram.com/bollyg0ssip/"),
    ("bollywood", "instagram", "bollywood.news.update", "https://www.instagram.com/bollywood.news.update/"),
    ("bollywood", "instagram", "bollywoodgossiip", "https://www.instagram.com/bollywoodgossiip/"),
    ("bollywood", "instagram", "gossip.bollywood", "https://www.instagram.com/gossip.bollywood/"),
    # edm
    ("edm", "instagram", "dancingastro", "https://www.instagram.com/dancingastro/"),
    ("edm", "instagram", "edm", "https://www.instagram.com/edm/"),
    ("edm", "instagram", "edm.us", "https://www.instagram.com/edm.us/"),
    ("edm", "instagram", "dancingastro.latin", "https://www.instagram.com/dancingastro.latin/"),
    ("edm", "instagram", "dancingastro.live", "https://www.instagram.com/dancingastro.live/"),
    # latin
    ("latin", "instagram", "reggaetontv", "https://www.instagram.com/reggaetontv/"),
    ("latin", "instagram", "ilovereggaeton_official", "https://www.instagram.com/ilovereggaeton_official/"),
    ("latin", "instagram", "reggaetonlandia", "https://www.instagram.com/reggaetonlandia/"),
    ("latin", "instagram", "reggaetonconlagata", "https://www.instagram.com/reggaetonconlagata/"),
    ("latin", "instagram", "vibraurbana", "https://www.instagram.com/vibraurbana/"),
    # indie
    ("indie", "instagram", "indiemusic", "https://www.instagram.com/indiemusic/"),
    ("indie", "instagram", "_indiesoftboi_", "https://www.instagram.com/_indiesoftboi_/"),
    ("indie", "instagram", "altmusicnew", "https://www.instagram.com/altmusicnew/"),
    ("indie", "instagram", "a_listgeocities", "https://www.instagram.com/a_listgeocities/"),
    # country
    ("country", "instagram", "whiskeyriff", "https://www.instagram.com/whiskeyriff/"),
    ("country", "instagram", "whiskeyriffraff", "https://www.instagram.com/whiskeyriffraff/"),
    # charts
    ("charts", "instagram", "chartdata.ig", "https://www.instagram.com/chartdata.ig/"),
    ("charts", "instagram", "chartdata", "https://www.instagram.com/chartdata/"),
    # memes
    ("memes", "instagram", "musicmemes", "https://www.instagram.com/musicmemes/"),
    # popculture (tiktok)
    ("popculture", "tiktok", "musicnewsz", "https://www.tiktok.com/@musicnewsz"),
    ("popculture", "tiktok", "dailymusic_._", "https://www.tiktok.com/@dailymusic_._"),
]

# spelling not confirmed yet — if the Viewer errors on these, just skip them
# (bars + concert are CONFIRMED official RapTV pages: rap's bio lists @bars @concert)
UNVERIFIED = {"popehiveupdates"}


def apply(database_url: str) -> dict:
    """Upsert genres for every channel + all source profiles. Idempotent."""
    import psycopg
    import psycopg.rows

    stats = {"channels": 0, "genres": 0, "profiles": 0}
    with psycopg.connect(database_url, autocommit=True, row_factory=psycopg.rows.dict_row) as c:
        channels = c.execute("select id, display_name from channels").fetchall()
        stats["channels"] = len(channels)
        for ch in channels:
            for slug, (label, seeds, tags) in GENRES.items():
                row = c.execute(
                    """insert into genres (channel_id, slug, label, weight, seed_queries, hashtags)
                       values (%s,%s,%s,1,%s,%s)
                       on conflict (channel_id, slug) do update
                       set label=excluded.label, seed_queries=excluded.seed_queries,
                           hashtags=excluded.hashtags
                       returning id""",
                    (ch["id"], slug, label, seeds, tags),
                ).fetchone()
                stats["genres"] += 1
                for _g, platform, handle, url in SOURCES:
                    if _g != slug:
                        continue
                    c.execute(
                        """insert into source_profiles
                             (genre_id, platform, handle, profile_url, status)
                           values (%s,%s,%s,%s,'candidate')
                           on conflict (genre_id, platform, handle) do update
                           set profile_url=excluded.profile_url""",
                        (row["id"], platform, handle, url),
                    )
                    stats["profiles"] += 1

        # genre map for the app UI
        rows = c.execute(
            """select g.id, g.slug, g.label, g.channel_id, c.display_name
               from genres g join channels c on c.id = g.channel_id
               order by g.label"""
        ).fetchall()
        (ENGINE / "genres.json").write_text(json.dumps(rows, default=str))
    return stats
