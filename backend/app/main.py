from fastapi import FastAPI

from app.routers import attempts, auth, bosses, recordings, sekiro

app = FastAPI(title="Sekiro Boss Practice Analytics")

app.include_router(auth.router)
app.include_router(bosses.router)
app.include_router(attempts.router)
app.include_router(sekiro.router)
app.include_router(recordings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
