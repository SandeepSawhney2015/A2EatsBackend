from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_url() -> str:
    url = get_settings().database_url
    # SQLAlchemy needs the driver spelled out; Neon gives plain postgresql://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_engine_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
