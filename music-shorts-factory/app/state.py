"""Every status change goes through here. Nothing writes media.status directly."""
import psycopg

ALLOWED: dict[str, set[str]] = {
    "discovered":  {"queued", "rejected", "duplicate"},
    "queued":      {"downloading", "rejected", "failed"},
    "downloading": {"downloaded", "failed", "duplicate"},
    "downloaded":  {"transforming", "rejected", "failed"},
    "transforming":{"ready", "failed", "rejected"},
    "ready":       {"scheduled", "skipped"},
    "scheduled":   {"publishing", "ready", "skipped"},
    "publishing":  {"published", "failed"},
    "published":   set(),
    "failed":      {"queued", "rejected"},
    "rejected":    set(),
    "duplicate":   set(),
    "skipped":     {"ready"},
}


class IllegalTransition(Exception):
    pass


def advance(conn: psycopg.Connection, media_id: str, to: str,
            note: str | None = None, actor: str = "worker") -> None:
    with conn.cursor() as cur:
        cur.execute("select status from media where id = %s for update", (media_id,))
        row = cur.fetchone()
        if row is None:
            raise IllegalTransition(f"{media_id} does not exist")
        frm = row[0]
        if to not in ALLOWED[frm]:
            raise IllegalTransition(f"{frm} -> {to} not allowed for {media_id}")
        cur.execute(
            "update media set status=%s, reason=coalesce(%s, reason), updated_at=now() "
            "where id=%s", (to, note, media_id))
        cur.execute(
            "insert into upload_log (media_id, from_state, to_state, note, actor) "
            "values (%s,%s,%s,%s,%s)", (media_id, frm, to, note, actor))
