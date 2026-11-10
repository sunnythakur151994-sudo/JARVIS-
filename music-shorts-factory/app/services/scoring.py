"""Genre-fit scoring for discovered channels. Runs on the flat-playlist dump."""
import statistics

WEIGHTS = {"follower": 0.30, "frequency": 0.20, "views": 0.30,
           "recency": 0.15, "keyword": 0.05}

def score_profile(dump: dict, keywords: list[str]) -> tuple[float, dict]:
    entries = dump.get("entries") or []
    views = [e.get("view_count") or 0 for e in entries]
    followers = dump.get("channel_follower_count") or 0

    f_score = min(followers / 100_000, 1.0) * 100
    freq = len(entries) / max(dump.get("playlist_count") or len(entries) or 1, 1)
    freq_score = min(freq, 1.0) * 100
    v_score = min((statistics.mean(views) if views else 0) / 250_000, 1.0) * 100
    rec_score = 100 if len(entries) >= 6 else len(entries) / 6 * 100
    blob = f"{dump.get('title','')} {dump.get('description','')}".lower()
    k_score = 100 if any(k.lower() in blob for k in keywords) else 0

    parts = {"follower": f_score, "frequency": freq_score, "views": v_score,
             "recency": rec_score, "keyword": k_score}
    total = sum(parts[k] * w for k, w in WEIGHTS.items())
    return round(total, 2), parts

def verdict(total: float) -> str:
    return "approved" if total >= 55 else "candidate"
