from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.checkin import Checkin

# Everything here is derived from the checkins table on demand — no stored
# counters to keep in sync.


def user_total_points(db: Session, user_id: int) -> int:
    total = db.execute(
        select(func.coalesce(func.sum(Checkin.points), 0)).where(Checkin.user_id == user_id)
    ).scalar_one()
    return int(total)


def user_top_restaurant_id(db: Session, user_id: int) -> int | None:
    row = db.execute(
        select(Checkin.restaurant_id)
        .where(Checkin.user_id == user_id)
        .group_by(Checkin.restaurant_id)
        .order_by(desc(func.count()), Checkin.restaurant_id)
        .limit(1)
    ).scalar_one_or_none()
    return row


def user_flavor_profile(db: Session, user_id: int) -> list[int]:
    """Distinct restaurant ids this user has checked into."""
    rows = db.execute(
        select(Checkin.restaurant_id)
        .where(Checkin.user_id == user_id)
        .distinct()
        .order_by(Checkin.restaurant_id)
    ).scalars()
    return list(rows)


def restaurant_total_points(db: Session, restaurant_id: int) -> int:
    total = db.execute(
        select(func.coalesce(func.sum(Checkin.points), 0)).where(
            Checkin.restaurant_id == restaurant_id
        )
    ).scalar_one()
    return int(total)
