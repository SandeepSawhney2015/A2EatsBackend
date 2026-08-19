import json
import math
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.redis import get_redis
from app.models.checkin import Checkin

MAX_DISTANCE_FEET = 200
FIRST_VISIT_POINTS = 10
REPEAT_VISIT_POINTS = 5
# Nobody eats out more than this in one day.
MAX_CHECKINS_PER_DAY = 10
# The multiplier maxes out at 5x, reached by the (MAX/2)th check-in of the
# day: 1x, 2x, 3x, 4x, 5x, then flat. Both derive from the daily cap.
MULTIPLIER_CAP = MAX_CHECKINS_PER_DAY / 2
MULTIPLIER_STEP = (MULTIPLIER_CAP - 1) / (MAX_CHECKINS_PER_DAY / 2 - 1)
RATE_LIMIT_SECONDS = 24 * 60 * 60
# Must wait between ANY two check-ins — you have to actually eat somewhere
# before checking in at the next place.
MIN_INTERVAL_SECONDS = 30 * 60
# Fastest plausible travel between two check-in locations. Anything faster
# means the reported GPS is spoofed (or teleportation).
MAX_TRAVEL_MPH = 150

_EARTH_RADIUS_FEET = 20_902_231
_FEET_PER_MILE = 5280


def distance_feet(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance between two GPS points, in feet."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_FEET * math.asin(math.sqrt(a))


def _rate_limit_key(user_id: int, restaurant_id: int) -> str:
    return f"checkin_block:{user_id}:{restaurant_id}"


def _daily_key(user_id: int) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"daily_count:{user_id}:{day}"


def _last_checkin_key(user_id: int) -> str:
    return f"last_checkin:{user_id}"


def is_rate_limited(user_id: int, restaurant_id: int) -> bool:
    """True if this user checked into this restaurant within the last 24h."""
    return get_redis().exists(_rate_limit_key(user_id, restaurant_id)) == 1


def seconds_until_next_checkin(user_id: int) -> int:
    """Seconds remaining in the 30-minute global cooldown (0 = allowed)."""
    last = get_redis().get(_last_checkin_key(user_id))
    if last is None:
        return 0
    elapsed = time.time() - json.loads(last)["ts"]
    return max(0, int(MIN_INTERVAL_SECONDS - elapsed))


def daily_limit_reached(user_id: int) -> bool:
    """True if the user already hit today's check-in cap."""
    count = get_redis().get(_daily_key(user_id))
    return count is not None and int(count) >= MAX_CHECKINS_PER_DAY


def is_travel_plausible(user_id: int, lat: float, lng: float) -> bool:
    """Server-side GPS sanity check: could the user have physically moved from
    their last check-in location to these coordinates in the elapsed time?"""
    last = get_redis().get(_last_checkin_key(user_id))
    if last is None:
        return True
    prev = json.loads(last)
    elapsed_hours = max(time.time() - prev["ts"], 1.0) / 3600
    miles = distance_feet(prev["lat"], prev["lng"], lat, lng) / _FEET_PER_MILE
    return (miles / elapsed_hours) <= MAX_TRAVEL_MPH


def is_first_ever_visit(db: Session, user_id: int, restaurant_id: int) -> bool:
    prior = db.execute(
        select(Checkin.id)
        .where(Checkin.user_id == user_id, Checkin.restaurant_id == restaurant_id)
        .limit(1)
    ).scalar_one_or_none()
    return prior is None


def award_points(db: Session, user_id: int, restaurant_id: int, lat: float, lng: float) -> int:
    """Compute points for a check-in that has passed all checks, and record
    the Redis state (24h block, 30-min cooldown, daily counter) that future
    check-ins are validated against.

    Base: 10 for a first-ever visit to the restaurant, 5 for repeats.
    Multiplier: nth distinct restaurant today -> 1x, 1.25x, 1.5x ... capped 5x.
    """
    base = (
        FIRST_VISIT_POINTS
        if is_first_ever_visit(db, user_id, restaurant_id)
        else REPEAT_VISIT_POINTS
    )

    r = get_redis()
    # INCR returns the new count; the 24h-per-restaurant rule guarantees each
    # increment today is a distinct restaurant.
    nth_today = r.incr(_daily_key(user_id))
    if nth_today == 1:
        r.expire(_daily_key(user_id), RATE_LIMIT_SECONDS)
    multiplier = min(1 + MULTIPLIER_STEP * (nth_today - 1), MULTIPLIER_CAP)

    r.set(_rate_limit_key(user_id, restaurant_id), "1", ex=RATE_LIMIT_SECONDS)
    r.set(
        _last_checkin_key(user_id),
        json.dumps({"ts": time.time(), "lat": lat, "lng": lng}),
        ex=RATE_LIMIT_SECONDS,
    )

    return math.floor(base * multiplier + 0.5)  # round half-up
