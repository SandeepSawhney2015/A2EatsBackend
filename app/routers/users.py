from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.user import User
from app.services import stats
from app.services.users import (
    ChangeLimitReachedError,
    UsernameTakenError,
    change_username,
)

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    points: int
    top_restaurant_id: int | None
    flavor_profile: list[int]


class UsernameChangeRequest(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,20}$")


@router.get("/me", response_model=UserResponse)
def read_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        points=stats.user_total_points(db, current_user.id),
        top_restaurant_id=stats.user_top_restaurant_id(db, current_user.id),
        flavor_profile=stats.user_flavor_profile(db, current_user.id),
    )


@router.patch("/me/username", response_model=UserResponse)
def update_username(
    body: UsernameChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user = change_username(db, current_user, body.username)
    except ChangeLimitReachedError:
        raise HTTPException(status_code=429, detail="Username can only be changed twice a month")
    except UsernameTakenError:
        raise HTTPException(status_code=409, detail="Username already taken")

    return read_me(db=db, current_user=user)
