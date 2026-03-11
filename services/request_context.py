from __future__ import annotations

import logging
import os
import time
import uuid
from urllib.parse import urlparse

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

IS_PROD = os.getenv("ENV", "development").lower() == "production"
_origin = (os.getenv("ORIGIN") or os.getenv("FRONTEND_ORIGIN") or "http://localhost:3000").strip()
_origin_host = (urlparse(_origin).hostname or "").lower()
ALLOW_LOCAL_PROD_HTTP = _origin_host in {"localhost", "127.0.0.1"}

DEFAULT_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        user_id = getattr(request.state, "user_id", None)
        operation = request.scope.get("path", "unknown")
        logger.info(
            "request_complete request_id=%s method=%s operation=%s status=%s user_id=%s duration_ms=%s",
            request_id,
            request.method,
            operation,
            response.status_code,
            user_id or "anonymous",
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in DEFAULT_SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if IS_PROD:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class ProductionHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if IS_PROD and not ALLOW_LOCAL_PROD_HTTP:
            forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
            scheme = (request.url.scheme or "").lower()
            if forwarded_proto not in {"https", ""} and scheme != "https":
                return JSONResponse(status_code=400, content={"detail": "HTTPS is required", "error_code": "https_required"})
            if forwarded_proto == "" and scheme != "https":
                return JSONResponse(status_code=400, content={"detail": "HTTPS is required", "error_code": "https_required"})
        return await call_next(request)
