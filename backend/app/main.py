import logging

from fastapi import FastAPI

from app.routers import admin, attempts, auth, bosses, recordings, sekiro

# The app's own log lines (such as the admin view's), next to uvicorn's: uvicorn sets up only its own loggers.
_log = logging.getLogger("app")
if not _log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)

app = FastAPI(title="Sekiro Boss Practice Analytics")

app.include_router(auth.router)
app.include_router(bosses.router)
app.include_router(attempts.router)
app.include_router(sekiro.router)
app.include_router(recordings.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
