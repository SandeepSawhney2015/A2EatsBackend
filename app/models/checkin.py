from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Checkin(Base):
    """One row per check-in. This is the source of truth that user points,
    restaurant points, top restaurant, and flavor profiles are computed from.

    Natural composite PK: (user_id, created_at). Unique because the 30-min
    cooldown means a user can't have two check-ins at the same instant, and
    the PK's b-tree gives fast per-user, time-ordered lookups for free.
    """

    __tablename__ = "checkins"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        default=lambda: datetime.now(timezone.utc),
    )
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    photo_url: Mapped[str] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=10)
