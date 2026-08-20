import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.restaurant import Restaurant
from app.services import stats
from app.core.config import get_settings

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


class RestaurantCreate(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float


class RestaurantResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class RestaurantDetailResponse(RestaurantResponse):
    points: int


@router.post("", response_model=RestaurantResponse, status_code=201)
def create_restaurant(
    body: RestaurantCreate,
    db: Session = Depends(get_db),
    x_admin_token: str = Header(),
):
    expected = get_settings().restaurant_secret_token
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Invalid admin token, please try again")
    restaurant = Restaurant(**body.model_dump())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("", response_model=list[RestaurantResponse])
def list_restaurants(db: Session = Depends(get_db)):
    return db.execute(select(Restaurant).order_by(Restaurant.id)).scalars().all()


@router.get("/{restaurant_id}", response_model=RestaurantDetailResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantDetailResponse(
        **RestaurantResponse.model_validate(restaurant).model_dump(),
        points=stats.restaurant_total_points(db, restaurant_id),
    )
