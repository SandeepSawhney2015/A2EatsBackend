from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.user import User
from app.services import stats

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    email: str | None
    full_name: str | None
    points: int
    top_restaurant_id: int | None
    flavor_profile: list[int]


@router.get("/me", response_model=UserResponse)
def read_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        points=stats.user_total_points(db, current_user.id),
        top_restaurant_id=stats.user_top_restaurant_id(db, current_user.id),
        flavor_profile=stats.user_flavor_profile(db, current_user.id),
    )
