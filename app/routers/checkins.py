from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.checkin import Checkin
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services import checkin_rules

router = APIRouter(prefix="/checkins", tags=["checkins"])


class CheckinCreate(BaseModel):
    restaurant_id: int
    latitude: float
    longitude: float
    # A check-in is proof you ate there — the photo is required.
    photo_url: str = Field(min_length=1, max_length=2000)


class CheckinResponse(BaseModel):
    user_id: int
    restaurant_id: int
    photo_url: str
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=CheckinResponse, status_code=201)
def create_checkin(
    body: CheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    restaurant = db.get(Restaurant, body.restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    distance = checkin_rules.distance_feet(
        body.latitude, body.longitude, restaurant.latitude, restaurant.longitude
    )
    if distance > checkin_rules.MAX_DISTANCE_FEET:
        raise HTTPException(
            status_code=400,
            detail=f"Too far from restaurant ({int(distance)} ft, max {checkin_rules.MAX_DISTANCE_FEET})",
        )

    if checkin_rules.daily_limit_reached(current_user.id):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {checkin_rules.MAX_CHECKINS_PER_DAY} check-ins reached",
        )

    wait = checkin_rules.seconds_until_next_checkin(current_user.id)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Enjoy your meal first — next check-in in {wait // 60 + 1} minutes",
        )

    if not checkin_rules.is_travel_plausible(current_user.id, body.latitude, body.longitude):
        raise HTTPException(
            status_code=400,
            detail="Location check failed",
        )

    if checkin_rules.is_rate_limited(current_user.id, body.restaurant_id):
        raise HTTPException(
            status_code=409,
            detail="Already checked in here in the last 24 hours",
        )

    points = checkin_rules.award_points(
        db, current_user.id, body.restaurant_id, body.latitude, body.longitude
    )

    checkin = Checkin(
        user_id=current_user.id,
        restaurant_id=body.restaurant_id,
        photo_url=body.photo_url,
        points=points,
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
