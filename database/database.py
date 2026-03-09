import os
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    pass

ENV = os.getenv("ENV", "development").lower()


def is_production() -> bool:
    return ENV == "production"

# ----------------------------
# Local SQLite (development)
# ----------------------------
sqlite_path = os.getenv("SQLITE_DB_PATH", "./pii_sentinel.db")
engine = create_engine(
    f"sqlite:///{sqlite_path}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
print("DEBUG database.py loaded")
print("DEBUG SQLITE_DB_PATH env:", os.getenv("SQLITE_DB_PATH"))
print("DEBUG sqlite_path resolved:", os.getenv("SQLITE_DB_PATH", "./pii_sentinel.db"))
print("SQLITE_DB_PATH:", sqlite_path)
print("SQLAlchemy URL:", f"sqlite:///{sqlite_path}")

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
        
        
# ----------------------------
# Turso (production) via libsql_client
# ----------------------------
_turso_client = None

def _require_turso_env() -> tuple[str, str]:
    db_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not db_url or not auth_token:
        raise RuntimeError(
            "Production requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the environment."
        )
    return db_url, auth_token

async def get_turso_client():
    """
    Lazily creates and returns a singleton Turso client (async)
    """
    global _turso_client
    
    if _turso_client is None:
        try:
            import libsql_client
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: libsql-client\n"
                "Install with: pip install libsql-client"
            ) from exc
            
        db_url, auth_token = _require_turso_env()
        _turso_client = libsql_client.create_client(db_url, auth_token=auth_token)
        
    return _turso_client

async def turso_execute(sql: str, args: Optional[list] = None):
    """ 
    Execute a statement in Turso and return the results
    """
    client = await get_turso_client()
    if args is None:
        return await client.execute(sql)
    return await client.execute(sql, args)

async def close_turso_client():
    """
    Call this on app shutdown to avoid aiohttp warnings and free resources
    """
    global _turso_client
    if _turso_client is not None:
        await _turso_client.close()
        _turso_client = None
        

    