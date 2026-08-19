from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401 — register all tables with Base before create_all
from app.db import Base, engine
from app.routers import apple_auth, checkins, health, leaderboard, restaurants, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables that don't exist yet. Fine while learning; a real
    # deployment would use migrations (alembic) instead.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"WARNING: could not reach database, DB routes will fail: {exc}")
    yield


app = FastAPI(title="A2 Eats API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(apple_auth.router)
app.include_router(users.router)
app.include_router(restaurants.router)
app.include_router(checkins.router)
app.include_router(leaderboard.router)


@app.get("/")
def root():
    return {"message": "Welcome to the A2 Eats API"}
