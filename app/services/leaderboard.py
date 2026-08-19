import json

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.redis import get_redis
from app.models.checkin import Checkin
from app.models.restaurant import Restaurant
from app.models.user import User

TOP_N = 20
CACHE_SECONDS = 24 * 60 * 60

# Cache-aside: the first request after the cache expires runs the real query
# and stores the result in Redis with a 24h TTL; everyone else reads the
# cached copy until it dies.

_USERS_KEY = "leaderboard:users"
_RESTAURANTS_KEY = "leaderboard:restaurants"


def _cached(key: str, compute) -> list[dict]:
    r = get_redis()
    hit = r.get(key)
    if hit is not None:
        return json.loads(hit)
    result = compute()
    r.set(key, json.dumps(result), ex=CACHE_SECONDS)
    return result


def top_users(db: Session) -> list[dict]:
    def compute():
        rows = db.execute(
            select(
                User.id,
                User.username,
                func.sum(Checkin.points).label("points"),
            )
            .join(Checkin, Checkin.user_id == User.id)
            .group_by(User.id, User.username)
            .order_by(desc("points"), User.id)
            .limit(TOP_N)
        ).all()
        return [
            {"rank": i + 1, "user_id": uid, "username": username, "points": int(points)}
            for i, (uid, username, points) in enumerate(rows)
        ]

    return _cached(_USERS_KEY, compute)


def top_restaurants(db: Session) -> list[dict]:
    def compute():
        rows = db.execute(
            select(
                Restaurant.id,
                Restaurant.name,
                func.sum(Checkin.points).label("points"),
            )
            .join(Checkin, Checkin.restaurant_id == Restaurant.id)
            .group_by(Restaurant.id, Restaurant.name)
            .order_by(desc("points"), Restaurant.id)
            .limit(TOP_N)
        ).all()
        return [
            {"rank": i + 1, "restaurant_id": rid, "name": name, "points": int(points)}
            for i, (rid, name, points) in enumerate(rows)
        ]

    return _cached(_RESTAURANTS_KEY, compute)
