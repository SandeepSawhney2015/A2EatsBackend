from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import leaderboard

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class UserEntry(BaseModel):
    rank: int
    user_id: int
    name: str | None
    points: int


class RestaurantEntry(BaseModel):
    rank: int
    restaurant_id: int
    name: str
    points: int


@router.get("/users", response_model=list[UserEntry])
def user_leaderboard(db: Session = Depends(get_db)):
    return leaderboard.top_users(db)


@router.get("/restaurants", response_model=list[RestaurantEntry])
def restaurant_leaderboard(db: Session = Depends(get_db)):
    return leaderboard.top_restaurants(db)
