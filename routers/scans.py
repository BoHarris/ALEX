import json
import logging
import os
import re
import tempfile
import time
import uuid
import zipfile
from functools import partial
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from dependencies.tier_guard import get_current_user_context
from services.audit_service import list_audit_events, record_audit_event, serialize_audit_event
from services.scan_job_service import create_scan_job, enqueue_scan_job, process_scan_job, should_run_async
from services.retention_service import apply_retention_state, apply_retention_state_bulk
from services.scan_service import ScanLimitError, parse_scan_result_metadata
from services.security_service import extract_request_security_context, register_scan_activity
from utils.report_cache import cache_html_report, cache_pdf_report
from utils.security_events import record_security_event
from utils.api_errors import error_payload
from utils.constants import SUPPORTED_EXTENSIONS, SUPPORTED_EXTENSIONS_SORTED
from utils.plan_features import get_plan_features
from utils.rbac import ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN, has_any_role
from utils.tier_limiter import release_scan_quota_reservation, reserve_scan_quota

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Scans"])

BASE_DIR = Path(__file__).resolve().parent.parent
REDACTED_BASE_DIR = (BASE_DIR / "redacted").resolve()
ARCHIVE_MAX_ENTRIES = max(1, int(os.getenv("SCAN_ARCHIVE_MAX_ENTRIES", "4000")))
ARCHIVE_MAX_TOTAL_UNCOMPRESSED_BYTES = max(
    1,
    int(os.getenv("SCAN_ARCHIVE_MAX_UNCOMPRESSED_BYTES", str(100 * 1024 * 1024))),
)
ARCHIVE_MAX_ENTRY_BYTES = max(
    1,
    int(os.getenv("SCAN_ARCHIVE_MAX_ENTRY_BYTES", str(25 * 1024 * 1024))),
)
ARCHIVE_MAX_COMPRESSION_RATIO = max(
    1.0,
    float(os.getenv("SCAN_ARCHIVE_MAX_COMPRESSION_RATIO", "100.0")),
)
XML_UNSAFE_DIRECTIVE_RE = re.compile(br"<!DOCTYPE|<!ENTITY", re.IGNORECASE)
SPREADSHEET_FORMULA_RE = re.compile(r"^\s*[=+\-@]")


class ScanResultPayload(BaseModel):
    job_id: int | None = None
    job_status: str | None = None
    poll_url: str | None = None
    scan_id: int | None = None
    filename: str
    pii_columns: list[str] = Field(default_factory=list)
    redacted_file: str | None = None
    risk_score: int | None = None
    redacted_count: int | None = None
    total_values: int | None = None
    redaction_summary: dict[str, int] = Field(default_factory=dict)
    detection_results: list[dict[str, object]] = Field(default_factory=list)


def _scan_pipeline_filename(filename: str) -> str:
    path = Path(filename)
    if path.suffix.lower() == ".xls":
        return f"{path.stem}.xlsx"
    return filename


def _validate_safe_archive(*, source_path: str) -> None:
    try:
        with zipfile.ZipFile(source_path) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
    except zipfile.BadZipFile as exc:
        raise ValueError("Archive is malformed or unsupported.") from exc

    if not entries:
        raise ValueError("Archive is malformed or unsupported.")
    if len(entries) > ARCHIVE_MAX_ENTRIES:
        raise ValueError("Compressed archive exceeds safe processing limits.")

    total_uncompressed = 0
    for entry in entries:
        entry_path = Path(entry.filename)
        file_size = max(int(entry.file_size or 0), 0)
        compressed_size = max(int(entry.compress_size or 0), 0)

        if entry_path.is_absolute() or ".." in entry_path.parts:
            raise ValueError("Archive contains unsafe paths.")
        if file_size > ARCHIVE_MAX_ENTRY_BYTES:
            raise ValueError("Compressed archive exceeds safe processing limits.")

        total_uncompressed += file_size
        if total_uncompressed > ARCHIVE_MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ValueError("Compressed archive exceeds safe processing limits.")

        if compressed_size == 0 and file_size > 0:
            raise ValueError("Compressed archive exceeds safe processing limits.")
        if compressed_size and (file_size / compressed_size) > ARCHIVE_MAX_COMPRESSION_RATIO:
            raise ValueError("Compressed archive exceeds safe processing limits.")


def _validate_safe_xml_upload(*, source_path: str) -> None:
    with open(source_path, "rb") as handle:
        header = handle.read(8192)
    if XML_UNSAFE_DIRECTIVE_RE.search(header):
        raise ValueError("XML DTD and entity declarations are not allowed.")


def _sanitize_spreadsheet_cell(value):
    if value is None:
        return value
    if isinstance(value, float) and pd.isna(value):
        return value
    text = value if isinstance(value, str) else str(value)
    if SPREADSHEET_FORMULA_RE.match(text):
        return f"'{text}"
    return value


def _sanitize_dataframe_for_spreadsheet(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.apply(lambda column: column.map(_sanitize_spreadsheet_cell))


def _sanitize_redacted_output_file(*, file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext not in {".csv", ".tsv", ".xlsx", ".xls"}:
        return str(path)

    if ext in {".csv", ".tsv"}:
        separator = "\t" if ext == ".tsv" else ","
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, sep=separator)
        sanitized = _sanitize_dataframe_for_spreadsheet(frame)
        sanitized.to_csv(path, index=False, sep=separator)
        return str(path)

    frame = pd.read_excel(path, dtype=str).fillna("")
    sanitized = _sanitize_dataframe_for_spreadsheet(frame)
    output_path = path if ext == ".xlsx" else path.with_suffix(".xlsx")
    sanitized.to_excel(output_path, index=False)
    if output_path != path and path.exists():
        path.unlink()
    return str(output_path)


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


def _passes_content_signature_check(*, sample_bytes: bytes, source_path: str, ext: str) -> bool:
    if not sample_bytes:
        return False

    lowered_ext = ext.lower()
    if lowered_ext == ".pdf":
        return sample_bytes.startswith(b"%PDF-")
    if lowered_ext in {".xlsx", ".docx"}:
        return zipfile.is_zipfile(source_path)
    if lowered_ext == ".xls":
        return sample_bytes.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
    if lowered_ext == ".json":
        stripped = sample_bytes.lstrip()
        return stripped.startswith(b"{") or stripped.startswith(b"[")
    if lowered_ext == ".xml":
        return sample_bytes.lstrip().startswith(b"<")
    if lowered_ext == ".html":
        lowered = sample_bytes[:4096].lower()
        return b"<html" in lowered or b"<!doctype html" in lowered
    if lowered_ext in {".csv", ".tsv", ".txt", ".log"}:
        return _is_text_payload(sample_bytes)
    return False


async def _stream_upload_to_tempfile(
    file: UploadFile,
    *,
    suffix: str,
    max_file_size_bytes: int,
    max_file_size_mb: int,
) -> tuple[str, int, bytes]:
    os.makedirs("uploads", exist_ok=True)
    sample = bytearray()
    total_size = 0
    chunk_size = 1024 * 1024
    temp_handle = tempfile.NamedTemporaryFile(delete=False, dir="uploads", suffix=suffix)
    temp_path = temp_handle.name

    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break

            total_size += len(chunk)
            if total_size > max_file_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=error_payload(
                        detail=f"File exceeds {max_file_size_mb}MB plan limit.",
                        error_code="file_too_large",
                    ),
                )

            if len(sample) < 4096:
                remaining = 4096 - len(sample)
                sample.extend(chunk[:remaining])

            temp_handle.write(chunk)
    except Exception:
        temp_handle.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    temp_handle.close()
    return temp_path, total_size, bytes(sample)


def _company_allowed_extensions(db: Session, company_id: int | None) -> set[str] | None:
    if company_id is None:
        return None
    settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
    if not settings or not settings.allowed_upload_types:
        return None
    try:
        values = json.loads(settings.allowed_upload_types)
    except Exception:
        return None
    if not isinstance(values, list):
        return None

    allowed: set[str] = set()
    for entry in values:
        text = str(entry).strip().lower()
        if not text:
            continue
        allowed.add(text if text.startswith(".") else f".{text}")
    return allowed or None


def _parse_redacted_type_counts(raw_value: str | None) -> dict[str, int]:
    counts, _ = parse_scan_result_metadata(raw_value)
    return counts


def _parse_detection_results(raw_value: str | None) -> list[dict[str, object]]:
    _, detections = parse_scan_result_metadata(raw_value)
    return detections


def _build_scan_submission_from_job_payload(job_payload: dict) -> ScanResultPayload:
    result_payload = job_payload.get("result") or {}
    return ScanResultPayload(
        job_id=job_payload.get("job_id"),
        job_status=job_payload.get("status"),
        poll_url=f"/scan-jobs/{job_payload['job_id']}" if job_payload.get("job_id") else None,
        scan_id=result_payload.get("scan_id"),
        filename=result_payload.get("filename") or job_payload.get("filename") or "unknown",
        pii_columns=result_payload.get("pii_columns") or [],
        redacted_file=result_payload.get("redacted_file"),
        risk_score=result_payload.get("risk_score"),
        redacted_count=result_payload.get("redacted_count"),
        total_values=result_payload.get("total_values"),
        redaction_summary=result_payload.get("redaction_summary") or {},
        detection_results=result_payload.get("detection_results") or [],
    )


def _serialize_scan(scan: ScanResult, *, include_submitter: bool) -> dict:
    return {
        "scan_id": scan.id,
        "filename": scan.filename,
        "file_type": scan.file_type,
        "risk_score": scan.risk_score,
        "total_pii_found": scan.total_pii_found,
        "redacted_count": scan.total_pii_found,
        "redacted_type_counts": _parse_redacted_type_counts(scan.redacted_type_counts),
        "detection_results": _parse_detection_results(scan.redacted_type_counts),
        "pii_types_found": [item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()],
        "status": scan.status if scan.status else ("ready" if scan.redacted_file_path else "failed"),
        "is_archived": scan.status in {"archived", "expired"},
        "archived_at": scan.archived_at.isoformat() if scan.archived_at else None,
        "retention_expiration": scan.retention_expiration.isoformat() if scan.retention_expiration else None,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "redacted_file": f"/scans/{scan.id}/download" if scan.redacted_file_path else None,
        "report_file": f"/scans/{scan.id}/report",
        "submitter": (
            {
                "first_name": scan.user.first_name,
                "last_name": scan.user.last_name,
                "email": scan.user.email,
            }
            if include_submitter and scan.user is not None
            else None
        ),
    }


def _scan_event_metadata(*, scan_id: int | None, filename: str | None, file_type: str | None, **extra: object) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if scan_id is not None:
        metadata["scan_id"] = scan_id
    if filename:
        metadata["filename"] = filename
    if file_type:
        metadata["file_type"] = file_type
    for key, value in extra.items():
        if value is not None:
            metadata[key] = value
    return metadata


def _build_scan_query(db: Session, current_user: dict):
    query = db.query(ScanResult)
    if has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN) and current_user["company_id"] is not None:
        return query.filter(ScanResult.company_id == current_user["company_id"])
    return query.filter(ScanResult.user_id == current_user["user_id"])


def _authorize_scan_access(scan: ScanResult, current_user: dict) -> None:
    is_owner = scan.user_id == current_user["user_id"]
    is_company_admin = (
        has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN)
        and current_user["company_id"] is not None
        and scan.company_id == current_user["company_id"]
    )
    if not is_owner and not is_company_admin:
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Not authorized to access this scan.",
                error_code="forbidden",
            ),
        )


def _get_scan_or_404(db: Session, scan_id: int) -> ScanResult:
    scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()
    if not scan:
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="Scan not found",
                error_code="scan_not_found",
            ),
        )
    return scan


def _resolve_redacted_file_path(stored_path: str) -> Path:
    raw_path = Path(stored_path)
    candidate = raw_path.resolve() if raw_path.is_absolute() else (BASE_DIR / raw_path).resolve()
    try:
        candidate.relative_to(REDACTED_BASE_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Invalid file path",
                error_code="forbidden",
            ),
        ) from exc
    return candidate


@router.post("", response_model=ScanResultPayload)
async def create_scan(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_info: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
    aggressive: bool = False,
):
    if not isinstance(user_info, dict):
        error_id = str(uuid.uuid4())
        logger.error("Invalid user_info injected into scans route | error_id=%s | type=%r", error_id, type(user_info))
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
            detail=error_payload(detail="Missing filename.", error_code="validation_error"),
        )

    ext = os.path.splitext(file.filename)[1].lower()
    pipeline_filename = _scan_pipeline_filename(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail="Unsupported file type.", error_code="unsupported_file_type"),
        )

    plan = get_plan_features(user_info.get("tier"))
    max_file_size_mb = int(plan["max_file_size_mb"])
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_file_size_bytes:
                raise HTTPException(
                    status_code=413,
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

    user_id = user_info.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail=error_payload(detail="Missing user identity.", error_code="invalid_token"),
        )

    reserved_quota = False
    temp_path = None
    handed_off_to_job_worker = False
    scan_job = None
    request_context = extract_request_security_context(request)
    started_at = time.perf_counter()
    try:
        temp_path, total_size, file_signature_sample = await _stream_upload_to_tempfile(
            file,
            suffix=ext,
            max_file_size_bytes=max_file_size_bytes,
            max_file_size_mb=max_file_size_mb,
        )
        if not _passes_content_signature_check(sample_bytes=file_signature_sample, source_path=temp_path, ext=ext):
            raise HTTPException(
                status_code=400,
                detail=error_payload(
                    detail="Unsupported or invalid file signature.",
                    error_code="unsupported_file_type",
                ),
            )
        if ext in {".xlsx", ".docx"}:
            _validate_safe_archive(source_path=temp_path)
        if ext == ".xml":
            _validate_safe_xml_upload(source_path=temp_path)

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
            event_metadata=_scan_event_metadata(scan_id=None, filename=file.filename, file_type=ext.lstrip(".")),
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
                detail=error_payload(detail="Rate limit exceeded", error_code="rate_limit_exceeded"),
            )

        scan_job = create_scan_job(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            filename=file.filename,
            file_type=ext.lstrip("."),
        )
        job_context = {
            "user_id": int(user_id),
            "company_id": user_info.get("company_id"),
            "tier": user_info.get("tier"),
        }

        if should_run_async(total_size):
            enqueue_scan_job(
                background_tasks,
                job_id=scan_job.id,
                source_path=temp_path,
                original_filename=file.filename,
                pipeline_filename=pipeline_filename,
                context_data=job_context,
                aggressive=aggressive,
                model=getattr(request.app.state, "pii_model", None),
                cleanup_source=True,
                sanitize_output_file=_sanitize_redacted_output_file,
            )
            handed_off_to_job_worker = True
            response.status_code = 202
            return ScanResultPayload(
                job_id=scan_job.id,
                job_status=scan_job.status,
                poll_url=f"/scan-jobs/{scan_job.id}",
                scan_id=None,
                filename=file.filename,
                pii_columns=[],
                redacted_file=None,
                risk_score=None,
                redacted_count=None,
                total_values=None,
                redaction_summary={},
                detection_results=[],
            )

        job_payload = await run_in_threadpool(
            partial(
                process_scan_job,
                job_id=scan_job.id,
                source_path=temp_path,
                original_filename=file.filename,
                pipeline_filename=pipeline_filename,
                context_data=job_context,
                aggressive=aggressive,
                model=getattr(request.app.state, "pii_model", None),
                cleanup_source=True,
                sanitize_output_file=_sanitize_redacted_output_file,
                db_session=db,
            )
        )
        handed_off_to_job_worker = True
        result_payload = job_payload.get("result") or {}
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_completed",
            event_category="scan",
            description="A scan completed successfully.",
            target_type="scan",
            target_id=str(result_payload.get("scan_id")),
            request_context=request_context,
            event_metadata=_scan_event_metadata(
                scan_id=result_payload.get("scan_id"),
                filename=result_payload.get("filename") or file.filename,
                file_type=ext.lstrip("."),
                risk_score=result_payload.get("risk_score"),
                redacted_count=result_payload.get("redacted_count"),
                scan_duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            ),
        )
        db.commit()
        return _build_scan_submission_from_job_payload(job_payload)
    except ScanLimitError as exc:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        record_audit_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="scan_failed",
            event_category="scan",
            description="A scan request exceeded configured processing limits.",
            target_type="user",
            target_id=str(user_id),
            request_context=request_context,
            event_metadata=_scan_event_metadata(
                scan_id=None,
                filename=file.filename,
                file_type=ext.lstrip("."),
                reason=exc.detail,
                error_code=exc.error_code,
                scan_duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            ),
        )
        record_security_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="FAILED_SCAN",
            severity="medium",
            description="A scan request exceeded configured processing limits.",
            ip_address=getattr(request_context, "ip_address", None),
            event_metadata={"filename": file.filename, "error_code": exc.error_code},
        )
        db.commit()
        raise HTTPException(
            status_code=exc.status_code,
            detail=error_payload(detail=exc.detail, error_code=exc.error_code.lower()),
        ) from exc
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
            event_metadata=_scan_event_metadata(
                scan_id=None,
                filename=file.filename,
                file_type=ext.lstrip("."),
                reason=str(exc),
                scan_duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            ),
        )
        record_security_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="FAILED_SCAN",
            severity="medium",
            description="A scan request failed validation.",
            ip_address=getattr(request_context, "ip_address", None),
            event_metadata={"filename": file.filename, "reason": str(exc)},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=error_payload(detail=str(exc), error_code="validation_error"),
        ) from exc
    except RuntimeError as exc:
        if reserved_quota:
            release_scan_quota_reservation(db, user_id)
        error_id = str(uuid.uuid4())
        logger.exception("Scan runtime failure | error_id=%s | file=%s", error_id, file.filename)
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
            event_metadata=_scan_event_metadata(
                scan_id=None,
                filename=file.filename,
                file_type=ext.lstrip("."),
                error_id=error_id,
                scan_duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            ),
        )
        record_security_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="FAILED_SCAN",
            severity="high",
            description="A scan request failed during processing.",
            ip_address=getattr(request_context, "ip_address", None),
            event_metadata={"filename": file.filename, "error_id": error_id},
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
        logger.exception("Unexpected upload processing failure | error_id=%s | file=%s", error_id, file.filename)
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
            event_metadata=_scan_event_metadata(
                scan_id=None,
                filename=file.filename,
                file_type=ext.lstrip("."),
                error_id=error_id,
                scan_duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            ),
        )
        record_security_event(
            db,
            company_id=user_info.get("company_id"),
            user_id=int(user_id),
            event_type="FAILED_SCAN",
            severity="high",
            description="A scan request failed unexpectedly.",
            ip_address=getattr(request_context, "ip_address", None),
            event_metadata={"filename": file.filename, "error_id": error_id},
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
    finally:
        if temp_path and os.path.exists(temp_path) and not handed_off_to_job_worker:
            os.remove(temp_path)


@router.get("/supported-file-types")
def get_supported_file_types():
    return {"supported_extensions": SUPPORTED_EXTENSIONS_SORTED}


@router.get("")
def list_scans(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    is_company_admin = has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN) and current_user["company_id"] is not None
    scans = _build_scan_query(db, current_user).order_by(desc(ScanResult.scanned_at)).all()
    scans = apply_retention_state_bulk(db, scans)
    active_scans: list[dict] = []
    archived_scans: list[dict] = []

    for scan in scans:
        payload = _serialize_scan(scan, include_submitter=is_company_admin)
        if payload["is_archived"]:
            archived_scans.append(payload)
        else:
            active_scans.append(payload)
    return {"scans": active_scans, "archived_scans": archived_scans}


@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    include_submitter = has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN) and current_user["company_id"] is not None
    return _serialize_scan(scan, include_submitter=include_submitter)


@router.get("/{scan_id}/lineage")
def get_scan_lineage(
    scan_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    events = list_audit_events(db, company_id=scan.company_id, scan_id=scan.id, limit=200)
    return {"scan_id": scan.id, "events": [serialize_audit_event(event) for event in reversed(events)]}


@router.post("/{scan_id}/archive")
def archive_scan(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    scan.status = "archived"
    scan.archived_at = scan.archived_at or scan.scanned_at
    db.add(scan)
    record_audit_event(
        db,
        company_id=scan.company_id,
        user_id=current_user["user_id"],
        event_type="scan_archived",
        event_category="scan",
        description=f"Archived scan {scan.id}.",
        target_type="scan",
        target_id=str(scan.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"ok": True, "scan_id": scan.id, "status": "archived"}


@router.post("/{scan_id}/restore")
def restore_scan(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    if scan.status == "expired":
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Expired scans cannot be restored by standard workflows.",
                error_code="forbidden",
            ),
        )
    scan.status = "active"
    scan.archived_at = None
    db.add(scan)
    record_audit_event(
        db,
        company_id=scan.company_id,
        user_id=current_user["user_id"],
        event_type="scan_restored",
        event_category="scan",
        description=f"Restored scan {scan.id}.",
        target_type="scan",
        target_id=str(scan.id),
        request_context=extract_request_security_context(request),
    )
    db.commit()
    return {"ok": True, "scan_id": scan.id, "status": "active"}


@router.get("/{scan_id}/download")
def download_redacted_file(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    if scan.status == "expired":
        raise HTTPException(
            status_code=410,
            detail=error_payload(
                detail="Scan has expired under the retention policy.",
                error_code="scan_expired",
            ),
        )
    if not scan.redacted_file_path:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Redacted file path not found", error_code="scan_not_found"),
        )
    path = _resolve_redacted_file_path(scan.redacted_file_path)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Redacted file not found", error_code="scan_not_found"),
        )

    mime, _ = guess_type(str(path))
    download_name = f"{Path(scan.filename).stem}_redacted{path.suffix}"
    record_audit_event(
        db,
        company_id=scan.company_id,
        user_id=current_user["user_id"],
        event_type="redacted_file_downloaded",
        event_category="scan",
        description=f"Downloaded redacted file for scan {scan.id}.",
        target_type="scan",
        target_id=str(scan.id),
        request_context=extract_request_security_context(request),
        event_metadata=_scan_event_metadata(scan_id=scan.id, filename=scan.filename, file_type=scan.file_type),
    )
    db.commit()
    return FileResponse(str(path), media_type=mime or "application/octet-stream", filename=download_name)


@router.get("/{scan_id}/report")
def download_scan_report(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    if scan.status == "expired":
        raise HTTPException(
            status_code=410,
            detail=error_payload(
                detail="Scan has expired under the retention policy.",
                error_code="scan_expired",
            ),
        )
    html_path = cache_html_report(db, scan)
    encoded_name = quote(html_path.name)
    record_audit_event(
        db,
        company_id=scan.company_id,
        user_id=current_user["user_id"],
        event_type="report_html_downloaded",
        event_category="scan",
        description=f"Downloaded HTML report for scan {scan.id}.",
        target_type="scan",
        target_id=str(scan.id),
        request_context=extract_request_security_context(request),
        event_metadata=_scan_event_metadata(
            scan_id=scan.id,
            filename=scan.filename,
            file_type=scan.file_type,
            report_format="html",
        ),
    )
    db.commit()
    return FileResponse(
        str(html_path),
        media_type="text/html; charset=utf-8",
        filename=html_path.name,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@router.get("/{scan_id}/report/html")
def download_scan_report_html(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    return download_scan_report(scan_id=scan_id, request=request, current_user=current_user, db=db)


@router.get("/{scan_id}/report/pdf")
def download_scan_report_pdf(
    scan_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)
    apply_retention_state(db, scan)
    if scan.status == "expired":
        raise HTTPException(
            status_code=410,
            detail=error_payload(
                detail="Scan has expired under the retention policy.",
                error_code="scan_expired",
            ),
        )
    try:
        pdf_path = cache_pdf_report(db, scan)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=501,
            detail=error_payload(detail=str(exc), error_code="report_generation_unavailable"),
        ) from exc

    encoded_name = quote(pdf_path.name)
    record_audit_event(
        db,
        company_id=scan.company_id,
        user_id=current_user["user_id"],
        event_type="report_pdf_downloaded",
        event_category="scan",
        description=f"Downloaded PDF report for scan {scan.id}.",
        target_type="scan",
        target_id=str(scan.id),
        request_context=extract_request_security_context(request),
        event_metadata=_scan_event_metadata(
            scan_id=scan.id,
            filename=scan.filename,
            file_type=scan.file_type,
            report_format="pdf",
        ),
    )
    db.commit()
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
