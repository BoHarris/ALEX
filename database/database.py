import os
import logging
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    pass

ENV = os.getenv("ENV", "development").lower()
logger = logging.getLogger(__name__)


def is_production() -> bool:
    return ENV == "production"

# ----------------------------
# ORM Engine Configuration
# ----------------------------
sqlite_path = os.getenv("SQLITE_DB_PATH", "./pii_sentinel.db")
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip() or f"sqlite:///{sqlite_path}"
IS_SQLITE_URL = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE_URL else {},
    pool_pre_ping=True,
)
if ENV != "production":
    logger.debug("database.py loaded")
    logger.debug("SQLITE_DB_PATH env: %s", os.getenv("SQLITE_DB_PATH"))
    logger.debug("DATABASE_URL configured: %s", "yes" if os.getenv("DATABASE_URL") else "no")
    logger.debug("SQLAlchemy engine dialect: %s", engine.dialect.name)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
        SQLAlchemy session dependency for local enviroment.
        Use this in FastAPI dependencies like Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
