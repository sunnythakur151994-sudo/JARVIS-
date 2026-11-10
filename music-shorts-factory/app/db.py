import psycopg, psycopg.rows
from contextlib import contextmanager
from .config import settings

@contextmanager
def conn():
    with psycopg.connect(settings.database_url, row_factory=psycopg.rows.dict_row) as c:
        yield c

def claim(conn, table: str, n: int, worker: str):
    """Postgres-as-queue. SKIP LOCKED means two workers never take the same row."""
    with conn.cursor() as cur:
        cur.execute(f"""
            update {table} set locked_by=%s, locked_at=now()
            where id in (
                select id from {table}
                where status='queued' and (locked_at is null or locked_at < now()-interval '15 min')
                order by created_at limit %s for update skip locked)
            returning id""", (worker, n))
        return [r["id"] for r in cur.fetchall()]
