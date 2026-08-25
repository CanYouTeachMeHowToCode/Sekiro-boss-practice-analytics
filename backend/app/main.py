from fastapi import FastAPI

from app.routers import attempts, bosses

app = FastAPI(title="Sekiro Boss Practice Analytics")

app.include_router(bosses.router)
app.include_router(attempts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
