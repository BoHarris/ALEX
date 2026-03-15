from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models.scan_job import ScanJob
from database.models.scan_results import ScanResult
from services.audit_service import record_audit_event
from services.scan_service import ScanContext, ScanLimitError, parse_scan_result_metadata, run_scan_pipeline
from utils.security_events import record_security_event

JOB_QUEUED = "QUEUED"
JOB_RUNNING = "RUNNING"
JOB_COMPLETED = "COMPLETED"
JOB_FAILED = "FAILED"
ASYNC_SCAN_THRESHOLD_BYTES = max(1, int(os.getenv("SCAN_ASYNC_THRESHOLD_BYTES", str(5 * 1024 * 1024))))
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def should_run_async(file_size_bytes: int) -> bool:
    return int(file_size_bytes) > ASYNC_SCAN_THRESHOLD_BYTES


def job_progress(status: str) -> int:
    normalized = (status or "").upper()
    if normalized in {JOB_COMPLETED, JOB_FAILED}:
        return 100
    if normalized == JOB_RUNNING:
        return 60
    return 10


def create_scan_job(
    db: Session,
    *,
    company_id: int | None,
    user_id: int,
    filename: str,
    file_type: str,
) -> ScanJob:
    job = ScanJob(
        company_id=company_id,
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        status=JOB_QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_scan_job(db: Session, job_id: int) -> ScanJob | None:
    return db.query(ScanJob).filter(ScanJob.id == job_id).first()


def serialize_scan_result(scan: ScanResult | None) -> dict[str, Any] | None:
    if not scan:
        return None
    counts, detections = parse_scan_result_metadata(getattr(scan, "redacted_type_counts", None))
    pii_columns = [item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()]
    return {
        "scan_id": scan.id,
        "filename": scan.filename,
        "pii_columns": pii_columns,
        "redacted_file": f"/scans/{scan.id}/download" if scan.redacted_file_path else None,
        "risk_score": scan.risk_score,
        "redacted_count": scan.total_pii_found,
        "total_values": None,
        "redaction_summary": counts,
        "detection_results": detections,
    }


def serialize_scan_job(
    job: ScanJob,
    *,
    scan: ScanResult | None = None,
    result_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result_scan = scan
    if result_payload is None and result_scan is None and job.scan_result_id is not None:
        db = SessionLocal()
        try:
            result_scan = db.query(ScanResult).filter(ScanResult.id == job.scan_result_id).first()
        finally:
            db.close()
    if result_payload is None:
        result_payload = serialize_scan_result(result_scan)
    return {
        "job_id": job.id,
        "company_id": job.company_id,
        "user_id": job.user_id,
        "scan_result_id": job.scan_result_id,
        "status": job.status,
        "progress": job_progress(job.status),
        "filename": job.filename,
        "file_type": job.file_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "result": result_payload,
    }


def _mark_job_running(job: ScanJob) -> None:
    job.status = JOB_RUNNING
    job.started_at = job.started_at or _utcnow()


def _mark_job_completed(job: ScanJob, *, scan_result_id: int) -> None:
    job.status = JOB_COMPLETED
    job.scan_result_id = scan_result_id
    job.completed_at = _utcnow()
    job.error_message = None


def _mark_job_failed(job: ScanJob, *, error_message: str) -> None:
    job.status = JOB_FAILED
    job.completed_at = _utcnow()
    job.error_message = error_message[:500]


def _record_audit_event_best_effort(db: Session, **kwargs) -> None:
    try:
        record_audit_event(db, **kwargs)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to persist audit event for scan job.", exc_info=True)


def _record_security_event_best_effort(db: Session, **kwargs) -> None:
    try:
        record_security_event(db, **kwargs)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to persist security event for scan job.", exc_info=True)


def process_scan_job(
    *,
    job_id: int,
    source_path: str,
    original_filename: str,
    pipeline_filename: str,
    context_data: dict[str, Any],
    aggressive: bool = False,
    model: Any = None,
    cleanup_source: bool = True,
    sanitize_output_file: Callable[..., str] | None = None,
    db_session: Session | None = None,
) -> dict[str, Any]:
    db = db_session or SessionLocal()
    owns_session = db_session is None
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            raise RuntimeError("Scan job not found")

        _mark_job_running(job)
        db.add(job)
        db.commit()
        db.refresh(job)

        result = run_scan_pipeline(
            source_path=source_path,
            filename=pipeline_filename,
            context=ScanContext(
                user_id=int(context_data["user_id"]),
                company_id=context_data.get("company_id"),
                tier=context_data.get("tier"),
            ),
            model=model,
            aggressive=aggressive,
        )

        sanitized_output_path = result.redacted_file
        if sanitize_output_file and result.redacted_file and os.path.exists(result.redacted_file):
            sanitized_output_path = sanitize_output_file(file_path=result.redacted_file)

        scan = db.query(ScanResult).filter(ScanResult.id == result.scan_id).first()
        result_payload = {
            "scan_id": result.scan_id,
            "filename": original_filename,
            "pii_columns": result.pii_columns,
            "redacted_file": f"/scans/{result.scan_id}/download" if sanitized_output_path else None,
            "risk_score": result.risk_score,
            "redacted_count": result.redacted_count,
            "total_values": result.total_values,
            "redaction_summary": result.redacted_type_counts,
            "detection_results": result.detection_results,
        }
        if scan:
            scan.filename = original_filename
            scan.file_type = Path(original_filename).suffix.lstrip(".") or scan.file_type
            scan.redacted_file_path = sanitized_output_path
            db.add(scan)

        _mark_job_completed(job, scan_result_id=result.scan_id)
        db.add(job)
        db.commit()
        if scan:
            db.refresh(scan)
        db.refresh(job)

        serialized_job = serialize_scan_job(job, scan=scan, result_payload=result_payload if scan is None else None)
        _record_audit_event_best_effort(
            db,
            company_id=context_data.get("company_id"),
            user_id=int(context_data["user_id"]),
            event_type="scan_job_completed",
            event_category="scan",
            description=f"Scan job {job.id} completed.",
            target_type="scan_job",
            target_id=str(job.id),
            event_metadata={"scan_id": result.scan_id, "filename": original_filename},
        )
        return serialized_job
    except ScanLimitError as exc:
        db.rollback()
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job:
            _mark_job_failed(job, error_message=exc.detail)
            db.add(job)
        db.commit()
        _record_audit_event_best_effort(
            db,
            company_id=context_data.get("company_id"),
            user_id=int(context_data["user_id"]),
            event_type="scan_job_failed",
            event_category="scan",
            description=f"Scan job {job_id} failed processing limits.",
            target_type="scan_job",
            target_id=str(job_id),
            event_metadata={"reason": exc.detail, "error_code": exc.error_code},
        )
        _record_security_event_best_effort(
            db,
            company_id=context_data.get("company_id"),
            user_id=int(context_data["user_id"]),
            event_type="FAILED_SCAN",
            severity="medium",
            description=f"Scan job {job_id} failed processing limits.",
            event_metadata={"reason": exc.detail, "error_code": exc.error_code},
        )
        raise
    except Exception as exc:
        db.rollback()
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job:
            _mark_job_failed(job, error_message=str(exc))
            db.add(job)
        db.commit()
        _record_audit_event_best_effort(
            db,
            company_id=context_data.get("company_id"),
            user_id=int(context_data["user_id"]),
            event_type="scan_job_failed",
            event_category="scan",
            description=f"Scan job {job_id} failed unexpectedly.",
            target_type="scan_job",
            target_id=str(job_id),
            event_metadata={"reason": str(exc)},
        )
        _record_security_event_best_effort(
            db,
            company_id=context_data.get("company_id"),
            user_id=int(context_data["user_id"]),
            event_type="FAILED_SCAN",
            severity="high",
            description=f"Scan job {job_id} failed unexpectedly.",
            event_metadata={"reason": str(exc)},
        )
        raise
    finally:
        if owns_session:
            db.close()
        if cleanup_source and source_path and os.path.exists(source_path):
            os.remove(source_path)


def _run_job_safely(**kwargs) -> None:
    try:
        process_scan_job(**kwargs)
    except Exception:
        return None


def enqueue_scan_job(background_tasks: BackgroundTasks, **kwargs) -> None:
    background_tasks.add_task(_run_job_safely, **kwargs)
