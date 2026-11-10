from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from cryptography.fernet import Fernet
from ..db import conn
from ..config import settings

router = APIRouter(prefix="/api/channels", tags=["channels"])
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def _flow():
    return Flow.from_client_config(
        {"web": {"client_id": settings.yt_client_id,
                 "client_secret": settings.yt_client_secret,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token",
                 "redirect_uris": [settings.yt_redirect_uri]}},
        scopes=SCOPES, redirect_uri=settings.yt_redirect_uri)

@router.get("/connect")
def connect():
    url, _ = _flow().authorization_url(access_type="offline", prompt="consent")
    return RedirectResponse(url)

@router.get("/callback")
def callback(code: str):
    flow = _flow()
    flow.fetch_token(code=code)
    rt = flow.credentials.refresh_token
    if not rt:
        raise HTTPException(400, "no refresh token — revoke and retry with prompt=consent")
    token = Fernet(settings.fernet_key.encode()).encrypt(rt.encode()).decode()
    with conn() as c:
        c.execute("insert into channels (display_name, oauth_refresh, oauth_state) "
                  "values ('pending',%s,'pending') returning id", (token,))
        cid = c.fetchone()["id"]
        c.execute("insert into settings (channel_id) values (%s)", (cid,))
    return {"channel_id": cid}
