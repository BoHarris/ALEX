import logging
import uuid
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
import os
from contextlib import asynccontextmanager

from routers import protected, logout, refresh
from routers.admin_router import router as admin_router
from routers.compliance_router import router as compliance_router
from routers.privacy_metrics import router as privacy_metrics_router
from routers.webauthn_auth import router as webauthn_auth_router

from routers.scans import router as scans_router

from database.models.company import Company  # noqa: F401
from database.models.user import User 

from services.startup_validation import run_startup_validations
from services.request_context import (
    ProductionHTTPSMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
import database.models  # registers models
from database.database import engine
from utils.api_errors import default_error_code_for_status, error_payload

logger = logging.getLogger(__name__)

os.makedirs("logs", exist_ok=True)

log_level_name = (os.getenv("LOG_LEVEL") or ("INFO" if os.getenv("ENV", "development").lower() == "production" else "DEBUG")).upper()
log_level = getattr(logging, log_level_name, logging.INFO)
log_max_bytes = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
file_handler = RotatingFileHandler(
    filename="logs/api.log",
    maxBytes=log_max_bytes,
    backupCount=log_backup_count,
    encoding="utf-8",
)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[file_handler],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pii_model = run_startup_validations()
    
    yield
    

    

app = FastAPI(
    title="PII Sentinel", 
    description="Real-Time PII Detection and Redaction API",
    lifespan=lifespan
    )

cors_origins_env = (os.getenv("CORS_ORIGINS") or "").strip()
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ProductionHTTPSMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

#auth (passkeys-only)
app.include_router(webauthn_auth_router)

#existing routers
app.include_router(protected.router)
app.include_router(protected.companies_router)
app.include_router(logout.router)
app.include_router(refresh.router)
app.include_router(scans_router)
app.include_router(privacy_metrics_router)
app.include_router(admin_router)
app.include_router(compliance_router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        payload = {
            "detail": str(detail.get("detail", "Request failed")),
            "error_code": str(
                detail.get("error_code", default_error_code_for_status(exc.status_code))
            ),
        }
        if detail.get("error_id"):
            payload["error_id"] = str(detail["error_id"])
    else:
        payload = error_payload(
            detail=str(detail) if detail else "Request failed",
            error_code=default_error_code_for_status(exc.status_code),
        )
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation failure | method=%s | path=%s | errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content=error_payload(
            detail="Validation error",
            error_code="validation_error",
        ),
    )


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
        content=error_payload(
            detail="Internal server error",
            error_code="internal_error",
            error_id=error_id,
        ),
        )

#SMTP settings
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
FRONTEND_URL = os.getenv("FRONTEND_URL")

@app.get("/")
def root():
    return {"message": "Welcome to PII Sentinel API. Upload a CSV to detect and redact PII."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        logger.exception("Readiness check failed: database connectivity error")
        return JSONResponse(
            status_code=503,
            content=error_payload(
                detail="Service not ready",
                error_code="service_unavailable",
            ),
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
