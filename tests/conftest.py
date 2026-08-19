"""Shared test fixtures.

Tests run against SQLite (instead of Neon) and Redis database 1 (instead of
the default 0), both wiped between tests, so the suite never touches real
data. Apple token verification is stubbed — only Apple can mint real tokens.
"""

import json
import os
import time
from unittest.mock import patch

# Must be set before any app import: the engine and settings read these once.
os.environ["DATABASE_URL"] = "sqlite:///./_test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-padding-to-32-bytes"

import pytest
from fastapi.testclient import TestClient

from app.core.redis import get_redis
from app.db import Base, engine
from app.main import app

FAKE_APPLE_SUB = "001234.testuser.5678"


@pytest.fixture(autouse=True)
def clean_state():
    """Fresh tables and empty Redis for every test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    get_redis().flushdb()
    yield
    get_redis().flushdb()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def apple_stub():
    claims = {"sub": FAKE_APPLE_SUB, "email": "test@example.com"}
    with patch("app.routers.apple_auth.verify_apple_token", return_value=claims):
        yield claims


@pytest.fixture
def auth_header(client, apple_stub):
    """Sign in and return the Authorization header for the test user."""
    tokens = client.post("/auth/apple", json={"identity_token": "stub"}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def make_restaurant(client):
    def _make(name="Test Spot", lat=42.2851, lng=-83.7452, address="Ann Arbor"):
        r = client.post(
            "/restaurants",
            json={"name": name, "address": address, "latitude": lat, "longitude": lng},
        )
        assert r.status_code == 201
        return r.json()

    return _make


@pytest.fixture
def skip_cooldown():
    """Backdate the user's last check-in so the 30-min cooldown has passed."""

    def _skip(user_id=1, minutes=31):
        key = f"last_checkin:{user_id}"
        r = get_redis()
        data = json.loads(r.get(key))
        data["ts"] = time.time() - minutes * 60
        r.set(key, json.dumps(data))

    return _skip


def checkin_payload(restaurant, lat=None, lng=None, **extra):
    return {
        "restaurant_id": restaurant["id"],
        "latitude": lat if lat is not None else restaurant["latitude"],
        "longitude": lng if lng is not None else restaurant["longitude"],
        **extra,
    }
