import asyncio, subprocess
from pathlib import Path
from ..db import conn
from ..state import advance
from ..config import settings

def build_filter(hook: str, wm_crop: int) -> str:
    f = []
    if wm_crop:
        f.append(f"crop=in_w:in_h-{wm_crop}:0:0")
    f += ["scale=1080:1920:force_original_aspect_ratio=increase",
          "crop=1080:1920", "eq=saturation=1.06:contrast=1.03"]
    if hook:
        safe = hook.replace(":", "\\:").replace("'", "")
        f.append(
            "drawtext=text='" + safe + "':fontsize=54:fontcolor=white:"
            "box=1:boxcolor=black@0.55:boxborderw=18:x=(w-tw)/2:y=250")
    return ",".join(f)

def render(src: Path, dst: Path, hook: str, max_s: int, wm: int):
    cmd = ["ffmpeg", "-y", "-i", str(src), "-t", str(max_s),
           "-vf", build_filter(hook, wm),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, capture_output=True)

async def run_once():
    with conn() as c:
        c.execute("""select m.id, m.local_path, m.caption, m.channel_id ch, g.slug,
                            coalesce(st.max_duration_s,58) max_s,
                            coalesce(st.watermark_crop,0) wm
                     from media m join genres g on g.id=m.genre_id
                     left join settings st on st.channel_id=m.channel_id
                     where m.status='downloaded' limit 3""")
        rows = c.fetchall()
    for r in rows:
        try:
            with conn() as c:
                advance(c, r["id"], "transforming")
            src = Path(r["local_path"])
            out = src.parent / f"{src.stem}_t.mp4"
            await asyncio.to_thread(render, src, out, r["caption"] or "", r["max_s"], r["wm"])
            with conn() as c:
                c.execute("update media set local_path=%s where id=%s", (str(out), r["id"]))
                advance(c, r["id"], "ready")
        except Exception as e:
            with conn() as c:
                advance(c, r["id"], "failed", str(e)[:300])
