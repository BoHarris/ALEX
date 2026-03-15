from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.scan_job import ScanJob
from database.models.scan_results import ScanResult
from dependencies.tier_guard import get_current_user_context
from services.scan_job_service import get_scan_job, serialize_scan_job
from utils.api_errors import error_payload
from utils.rbac import ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN, has_any_role

router = APIRouter(prefix="/scan-jobs", tags=["Scan Jobs"])


def _build_job_query(db: Session, current_user: dict):
    query = db.query(ScanJob)
    if has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN) and current_user["company_id"] is not None:
        return query.filter(ScanJob.company_id == current_user["company_id"])
    return query.filter(ScanJob.user_id == current_user["user_id"])


def _authorize_job_access(job: ScanJob, current_user: dict) -> None:
    is_owner = job.user_id == current_user["user_id"]
    is_company_admin = (
        has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN)
        and current_user["company_id"] is not None
        and job.company_id == current_user["company_id"]
    )
    if not is_owner and not is_company_admin:
        raise HTTPException(
            status_code=403,
            detail=error_payload(detail="Not authorized to access this scan job.", error_code="forbidden"),
        )


@router.get("")
def list_scan_jobs(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    jobs = _build_job_query(db, current_user).order_by(desc(ScanJob.created_at)).all()
    scans_by_id = {
        scan.id: scan
        for scan in db.query(ScanResult).filter(ScanResult.id.in_([job.scan_result_id for job in jobs if job.scan_result_id])).all()
    } if jobs else {}
    return {"jobs": [serialize_scan_job(job, scan=scans_by_id.get(job.scan_result_id)) for job in jobs]}


@router.get("/{job_id}")
def get_scan_job_status(
    job_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    job = get_scan_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=error_payload(detail="Scan job not found", error_code="scan_not_found"),
        )
    _authorize_job_access(job, current_user)
    scan = None
    if job.scan_result_id is not None:
        scan = db.query(ScanResult).filter(ScanResult.id == job.scan_result_id).first()
    return serialize_scan_job(job, scan=scan)
