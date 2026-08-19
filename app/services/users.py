from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User

USERNAME_CHANGES_PER_MONTH = 2


class UsernameRequiredError(Exception):
    """First-time signup attempted without choosing a username."""


class UsernameTakenError(Exception):
    """The UNIQUE constraint rejected the write — name already in use."""


class ChangeLimitReachedError(Exception):
    """Already changed username twice this month."""


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def upsert_apple_user(
    db: Session,
    apple_sub: str,
    email: str | None = None,
    full_name: str | None = None,
    username: str | None = None,
) -> User:
    user = db.execute(select(User).where(User.apple_sub == apple_sub)).scalar_one_or_none()

    if user is None:
        if username is None:
            raise UsernameRequiredError
        user = User(
            apple_sub=apple_sub,
            username=normalize_username(username),
            email=email,
            full_name=full_name,
        )
        db.add(user)
    else:
        # Apple only sends email/name on first sign-in; keep what we have,
        # but fill in anything we're missing.
        if email and not user.email:
            user.email = email
        if full_name and not user.full_name:
            user.full_name = full_name

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise UsernameTakenError
    db.refresh(user)
    return user


def change_username(db: Session, user: User, new_username: str) -> User:
    new_username = normalize_username(new_username)
    if new_username == user.username:
        return user  # no-op, doesn't burn a change

    month = _current_month()
    if user.username_change_month != month:
        user.username_change_month = month
        user.username_changes_in_month = 0
    if user.username_changes_in_month >= USERNAME_CHANGES_PER_MONTH:
        db.rollback()
        raise ChangeLimitReachedError

    user.username = new_username
    user.username_changes_in_month += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise UsernameTakenError
    db.refresh(user)
    return user
