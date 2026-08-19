from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    apple_sub: Mapped[str] = mapped_column(String, unique=True, index=True)
    # Uniqueness is enforced by the DB constraint, not a lookup: writes that
    # collide fail with IntegrityError and become a 409. Stored lowercase.
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Change limit: 2 per calendar month (UTC), e.g. month "2026-08".
    username_change_month: Mapped[str | None] = mapped_column(String, nullable=True)
    username_changes_in_month: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
