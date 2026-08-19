from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
