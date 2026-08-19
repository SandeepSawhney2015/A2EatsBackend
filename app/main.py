from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="A2 Eats API", version="0.1.0")

app.include_router(health.router)


@app.get("/")
def root():
    return {"message": "Welcome to the A2 Eats API"}
