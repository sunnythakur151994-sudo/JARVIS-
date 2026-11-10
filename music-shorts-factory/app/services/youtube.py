import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ..config import settings

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def client(refresh_token: str):
    creds = Credentials(token=None, refresh_token=refresh_token,
                        client_id=settings.yt_client_id,
                        client_secret=settings.yt_client_secret,
                        token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload(refresh_token: str, path: str, title: str, desc: str,
           publish_at: str | None) -> str:
    yt = client(refresh_token)
    body = {
        "snippet": {"title": title[:100], "description": desc[:4900],
                    "categoryId": "10", "tags": ["music", "shorts"]},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True,
                            chunksize=1024 * 1024 * 4)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
