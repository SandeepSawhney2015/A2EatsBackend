from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Checkin(Base):
    """One row per check-in. This is the source of truth that user points,
    restaurant points, top restaurant, and flavor profiles are computed from."""

    __tablename__ = "checkins"

    # (user_id, restaurant_id) can't be the PK: repeat visits after 24h mean
    # the pair isn't unique. The composite index below gives the same lookup
    # speed, and its user_id prefix also serves all per-user queries.
    __table_args__ = (Index("ix_checkins_user_restaurant", "user_id", "restaurant_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
