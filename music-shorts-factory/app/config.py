from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    storage_root: str = "/storage"
    cookie_root: str = "/cookies"
    fernet_key: str
    yt_client_id: str
    yt_client_secret: str
    yt_redirect_uri: str = "http://localhost:8000/api/channels/callback"
    sleep_requests: float = 2.0
    max_concurrent_pulls: int = 2
    class Config:
        env_file = ".env"

settings = Settings()
