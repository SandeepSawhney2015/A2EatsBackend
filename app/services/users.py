from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def upsert_apple_user(
    db: Session,
    apple_sub: str,
    email: str | None = None,
    full_name: str | None = None,
) -> User:
    user = db.execute(select(User).where(User.apple_sub == apple_sub)).scalar_one_or_none()

    if user is None:
        user = User(apple_sub=apple_sub, email=email, full_name=full_name)
        db.add(user)
    else:
        # Apple only sends email/name on first sign-in; keep what we have,
        # but fill in anything we're missing.
        if email and not user.email:
            user.email = email
        if full_name and not user.full_name:
            user.full_name = full_name

    db.commit()
    db.refresh(user)
    return user
