from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import sources, media, channels, schedule

app = FastAPI(title="Shorts Factory")
for r in (sources, media, channels, schedule):
    app.include_router(r.router)
app.mount("/", StaticFiles(directory="app/static", html=True), name="ui")
