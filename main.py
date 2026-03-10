import logging
import uuid
from sqlalchemy import text
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from contextlib import asynccontextmanager

from database.database import Base, engine

from routers import protected, logout, refresh
from routers.webauthn_auth import router as webauthn_auth_router

from routers.predict import router as predict_router
from routers.redacted_router import router as redacted_router

from database.models.company import Company  # noqa: F401
from database.models.user import User 

from services.startup_validation import run_startup_validations
import database.models  # registers models

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename="logs/api.log", 
    level=logging.INFO, 
    format='%(asctime)s - %(message)s')


def _ensure_sqlite_user_role_column() -> None:
    """
    Idempotent SQLite schema patch: add users.role if it does not exist.
    """
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = {row[1] for row in columns}
        if "role" not in column_names:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'member'")
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_user_role_column()
    run_startup_validations()
    
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("redacted", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    yield
    

    

app = FastAPI(
    title="PII Sentinel", 
    description="Real-Time PII Detection and Redaction API",
    lifespan=lifespan
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#auth (passkeys-only)
app.include_router(webauthn_auth_router)

#existing routers
app.include_router(protected.router)
app.include_router(protected.companies_router)
app.include_router(predict_router)
app.include_router(logout.router)
app.include_router(refresh.router)
app.include_router(redacted_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    
    logger.exception(
        "Unhandled exception | error_id=%s | method=%s | path=%s | client=%s",
        error_id,
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )
    
    return JSONResponse(
        status_code=500, 
        content={
            "details": "Internal server error",
            error_id: "error_id"
            }
        )

#SMTP settings
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
FRONTEND_URL = os.getenv("FRONTEND_URL")

if not os.path.exists("DejaVuSans.ttf"):
    raise FileNotFoundError("Missing DejaVuSans.ttf — place it in the project root for PDF export.")

@app.get("/")
def root():
    return {"message": "Welcome to PII Sentinel API. Upload a CSV to detect and redact PII."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
