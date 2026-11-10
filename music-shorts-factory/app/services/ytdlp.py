import asyncio, json, shutil
from pathlib import Path
from ..config import settings

BIN = shutil.which("yt-dlp") or "yt-dlp"

async def _run(args: list[str], timeout: int = 300):
    p = await asyncio.create_subprocess_exec(
        BIN, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        raise RuntimeError("yt-dlp timeout")
    return p.returncode, out.decode(errors="replace"), err.decode(errors="replace")

def _base(cookie_path: str | None):
    a = ["--no-warnings", "--sleep-requests", str(settings.sleep_requests),
         "--retries", "3", "--socket-timeout", "20"]
    if cookie_path:
        a += ["--cookies", cookie_path]
    return a

async def profile_dump(url: str, cookie_path: str | None, limit: int = 12) -> dict:
    """Full profile page: avatar, bio, counts, recent items. Used by the viewer."""
    args = _base(cookie_path) + [
        "--dump-single-json", "--flat-playlist", f"--playlist-end={limit}", url]
    code, out, err = await _run(args, timeout=90)
    if code != 0:
        raise RuntimeError(err.strip().splitlines()[-1] if err else "dump failed")
    return json.loads(out)

async def download(url: str, cookie_path: str | None, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    args = _base(cookie_path) + [
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format", "mp4",
        "-o", str(dest), "--no-part", url]
    code, _, err = await _run(args)
    if code != 0 or not dest.exists():
        raise RuntimeError(err.strip().splitlines()[-1] if err else "download failed")
    return dest
