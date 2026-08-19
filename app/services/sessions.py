import hashlib
import secrets
from datetime import timedelta

from app.core.config import get_settings
from app.core.redis import get_redis

# Refresh tokens live in Redis: key = sha256 of the token, value = user id,
# TTL = the session length. We store the hash so a leaked Redis dump doesn't
# contain usable tokens. Sliding expiry: every refresh rotates the token and
# restarts the 60-day clock.


def _key(token: str) -> str:
    return "session:" + hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    ttl = timedelta(days=get_settings().refresh_expire_days)
    get_redis().set(_key(token), str(user_id), ex=ttl)
    return token


def rotate_session(token: str) -> tuple[int, str] | None:
    """Validate a refresh token. If valid, revoke it and issue a replacement.

    Returns (user_id, new_token), or None if the session is expired/unknown.
    """
    r = get_redis()
    user_id = r.getdel(_key(token))
    if user_id is None:
        return None
    return int(user_id), create_session(int(user_id))


def revoke_session(token: str) -> None:
    get_redis().delete(_key(token))
