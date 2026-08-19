from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.checkin import Checkin
from app.models.restaurant import Restaurant
from app.models.user import User

router = APIRouter(prefix="/checkins", tags=["checkins"])

POINTS_PER_CHECKIN = 10


class CheckinCreate(BaseModel):
    restaurant_id: int
    photo_url: str | None = None


class CheckinResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    photo_url: str | None
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=CheckinResponse, status_code=201)
def create_checkin(
    body: CheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.get(Restaurant, body.restaurant_id) is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    checkin = Checkin(
        user_id=current_user.id,
        restaurant_id=body.restaurant_id,
        photo_url=body.photo_url,
        points=POINTS_PER_CHECKIN,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/me", response_model=list[CheckinResponse])
def my_checkins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.execute(
            select(Checkin)
            .where(Checkin.user_id == current_user.id)
            .order_by(Checkin.created_at.desc())
        )
        .scalars()
        .all()
    )
