import logging
import io
import os
import uuid
import zipfile
from functools import partial

from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company_settings import CompanySettings
from dependencies.tier_guard import get_current_user_context
from services.audit_service import record_audit_event
from services.security_service import extract_request_security_context, register_scan_activity
from services.scan_service import ScanContext, run_scan_pipeline
from utils.tier_limiter import release_scan_quota_reservation, reserve_scan_quota
from utils.constants import SUPPORTED_EXTENSIONS
from utils.api_errors import error_payload
from utils.plan_features import get_plan_features

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])


def _is_text_payload(file_bytes: bytes) -> bool:
    if not file_bytes:
        return False
    sample = file_bytes[:2048]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
            return True
        except UnicodeDecodeError:
            return False


def _passes_content_signature_check(file_bytes: bytes, ext: str) -> bool:
    if not file_bytes:
        return False

    lowered_ext = ext.lower()

    if lowered_ext == ".pdf":
        return file_bytes.startswith(b"%PDF-")
    if lowered_ext in {".xlsx", ".docx"}:
        return zipfile.is_zipfile(io.BytesIO(file_bytes))
    if lowered_ext == ".xls":
        return file_bytes.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
    if lowered_ext == ".json":
        stripped = file_bytes.lstrip()
        return stripped.startswith(b"{") or stripped.startswith(b"[")
    if lowered_ext == ".xml":
        return file_bytes.lstrip().startswith(b"<")
    if lowered_ext == ".html":
        lowered = file_bytes[:4096].lower()
        return b"<html" in lowered or b"<!doctype html" in lowered
    if lowered_ext in {".csv", ".tsv", ".txt", ".log"}:
        return _is_text_payload(file_bytes)

    return False


def _company_allowed_extensions(db: Session, company_id: int | None) -> set[str] | None:
    if company_id is None:
        return None
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings or not settings.allowed_upload_types:
        return None
    try:
        import json

        values = json.loads(settings.allowed_upload_types)
        if not isinstance(values, list):
            return None
        allowed: set[str] = set()
        for entry in values:
            text = str(entry).strip().lower()
            if not text:
                continue
            allowed.add(text if text.startswith(".") else f".{text}")
        return allowed or None
    except Exception:
        return None


class PredictionResult(BaseModel):
    scan_id: int
    filename: str
    pii_columns: list[str]
    redacted_file: str
    risk_score: int
    redacted_count: int
    total_values: int
    redaction_summary: dict[str, int]


@router.post("/", response_model=PredictionResult)
async def predict(
    request: Request,
    file: UploadFile = File(...),
    user_info: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
    aggressive: bool = False,
):
    if not isinstance(user_info, dict):
        error_id = str(uuid.uuid4())
        logger.error(
            "Invalid user_info injected into predict route | error_id=%s | type=%r",
            error_id,
            type(user_info),
        )
        raise HTTPException(
            status_code=500,
            detail=error_payload(
                detail="Invalid authentication context.",
                error_code="internal_error",
                error_id=error_id,
            ),
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Missing filename.",
                error_code="validation_error",
            ),
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Unsupported file type.",
                error_code="unsupported_file_type",
            ),
        )

    plan = get_plan_features(user_info.get("tier"))
    max_file_size_mb = int(plan["max_file_size_mb"])
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_file_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=error_payload(
                        detail=f"File exceeds {max_file_size_mb}MB plan limit.",
                        error_code="file_too_large",
                    ),
                )
        except ValueError:
            pass

    allowed_extensions = _company_allowed_extensions(db, user_info.get("company_id"))
    if allowed_extensions is not None and ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="File type is not allowed by company policy.",
                error_code="unsupported_file_type",
            ),
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail=f"File exceeds {max_file_size_mb}MB plan limit.",
                error_code="file_too_large",
            ),
        )

    if not _passes_content_signature_check(file_bytes, ext):
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail="Unsupported or invalid file signature.",
                error_code="unsupported_file_type",
            ),
        )

    user_id = user_info.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail=error_payload(
                detail="Missing user identity.",
                error_code="invalid_token",
            ),
        )

    reserved_quota = False
    request_context = extract_request_security_context(request)
    try:
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_started",
            event_category="scan",
            description="A scan request was accepted for processing.",
            target_type="scan",
            target_id=None,
            request_context=request_context,
            event_metadata={"filename": file.filename, "file_type": ext.lstrip(".")},
        )
        register_scan_activity(
            db,
            organization_id=user_info.get("company_id"),
            user_id=int(user_id),
            context=request_context,
        )
        db.commit()
        reserved_quota = reserve_scan_quota(db, user_id, user_info.get("tier", "free"))
        if not reserved_quota:
            record_audit_event(
                db,
                company_id=user_info.get("company_id"),
                user_id=int(user_id),
                event_type="scan_throttled",
                event_category="security",
                description="A scan request exceeded the configured quota.",
                target_type="user",
                target_id=str(user_id),
                request_context=request_context,
            )
            db.commit()
            raise HTTPException(
                status_code=429,
                detail=error_payload(
                    detail="Rate limit exceeded",
                    error_code="rate_limit_exceeded",
                ),
            )
        context = ScanContext(
            user_id=int(user_id),
            company_id=user_info.get("company_id"),
            tier=user_info.get("tier"),
        )
        result = await run_in_threadpool(
            partial(
                run_scan_pipeline,
                file_bytes=file_bytes,
                filename=file.filename,
                context=context,
                aggressive=aggressive,
            )
        )
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_completed",
            event_category="scan",
            description="A scan completed successfully.",
            target_type="scan",
            target_id=str(result.scan_id),
            request_context=request_context,
            event_metadata={"risk_score": result.risk_score, "redacted_count": result.redacted_count},
        )
        db.commit()
        return PredictionResult(
            scan_id=result.scan_id,
            filename=result.filename,
            pii_columns=result.pii_columns,
            redacted_file=f"/scans/{result.scan_id}/download",
            risk_score=result.risk_score,
            redacted_count=result.redacted_count,
            total_values=result.total_values,
            redaction_summary=result.redacted_type_counts,
        )
    except ValueError as exc:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_failed",
            event_category="scan",
            description="A scan request failed validation.",
            target_type="user",
            target_id=str(user_id),
            request_context=request_context,
            event_metadata={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                detail=str(exc),
                error_code="validation_error",
            ),
        ) from exc
    except RuntimeError as exc:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        error_id = str(uuid.uuid4())
        logger.exception(
            "Scan runtime failure | error_id=%s | file=%s",
            error_id,
            file.filename,
        )
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_failed",
            event_category="scan",
            description="A scan request failed during processing.",
            target_type="user",
            target_id=str(user_id),
            request_context=request_context,
            event_metadata={"error_id": error_id},
        )
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=error_payload(
                detail="Scan processing failed.",
                error_code="internal_error",
                error_id=error_id,
            ),
        ) from exc
    except HTTPException:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        raise
    except Exception as exc:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        error_id = str(uuid.uuid4())
        logger.exception(
            "Unexpected upload processing failure | error_id=%s | file=%s",
            error_id,
            file.filename,
        )
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_failed",
            event_category="scan",
            description="A scan request failed unexpectedly.",
            target_type="user",
            target_id=str(user_id),
            request_context=request_context,
            event_metadata={"error_id": error_id},
        )
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=error_payload(
                detail="Failed to process upload.",
                error_code="internal_error",
                error_id=error_id,
            ),
        ) from exc
