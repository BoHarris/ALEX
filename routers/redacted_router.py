from mimetypes import guess_type
import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.scan_results import ScanResult
from dependencies.tier_guard import get_current_user_context
from services.retention_service import apply_retention_state, apply_retention_state_bulk
from services.audit_report_service import (
    generate_audit_report_html,
    render_report_pdf_from_html,
)
from services.audit_service import record_audit_event
from services.security_service import extract_request_security_context
from utils.api_errors import error_payload
from utils.rbac import ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN, has_any_role

router = APIRouter(prefix="/scans", tags=["Scans"])

BASE_DIR = Path(__file__).resolve().parent.parent
REDACTED_BASE_DIR = (BASE_DIR / "redacted").resolve()


def _parse_redacted_type_counts(raw_value: str | None) -> dict[str, int]:
    if not raw_value:
        return {}

    try:
        data = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    normalized: dict[str, int] = {}
    for key, value in data.items():
        label = str(key).strip()
        if not label:
            continue
        try:
            normalized[label] = int(value)
        except (TypeError, ValueError):
            continue
    return normalized


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
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail=error_payload(
                detail="Invalid file path",
                error_code="forbidden",
            ),
        )
    return candidate


@router.get("")
def list_scans(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    is_company_admin = has_any_role(current_user["role"], ROLE_ORG_ADMIN, ROLE_SECURITY_ADMIN) and current_user["company_id"] is not None
    scans = (
        _build_scan_query(db, current_user)
        .order_by(desc(ScanResult.scanned_at))
        .all()
    )
    scans = apply_retention_state_bulk(db, scans)
    active_scans: list[dict] = []
    archived_scans: list[dict] = []

    for scan in scans:
        scan_payload = {
            "scan_id": scan.id,
            "filename": scan.filename,
            "file_type": scan.file_type,
            "risk_score": scan.risk_score,
            "total_pii_found": scan.total_pii_found,
            "redacted_count": scan.total_pii_found,
            "redacted_type_counts": _parse_redacted_type_counts(scan.redacted_type_counts),
            "pii_types_found": [
                item.strip() for item in (scan.pii_types_found or "").split(",") if item.strip()
            ],
            "status": scan.status if scan.status else ("ready" if scan.redacted_file_path else "failed"),
            "is_archived": scan.status in {"archived", "expired"},
            "archived_at": scan.archived_at.isoformat() if scan.archived_at else None,
            "retention_expiration": scan.retention_expiration.isoformat() if scan.retention_expiration else None,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            "submitter": (
                {
                    "first_name": scan.user.first_name,
                    "last_name": scan.user.last_name,
                    "email": scan.user.email,
                }
                if is_company_admin and scan.user is not None
                else None
            ),
        }
        if scan_payload["is_archived"]:
            archived_scans.append(scan_payload)
        else:
            active_scans.append(scan_payload)

    return {"scans": active_scans, "archived_scans": archived_scans}


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
            detail=error_payload(
                detail="Redacted file path not found",
                error_code="scan_not_found",
            ),
        )

    path = _resolve_redacted_file_path(scan.redacted_file_path)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=error_payload(
                detail="Redacted file not found",
                error_code="scan_not_found",
            ),
        )

    mime, _ = guess_type(str(path))
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
    )
    db.commit()

    return FileResponse(
        str(path),
        media_type=mime or "application/octet-stream",
        filename=path.name,
    )
    
    



@router.get("/{scan_id}/report/html")
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

    html = generate_audit_report_html(scan)
    timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
    report_name = f"{Path(scan.filename).stem}_audit_report_{timestamp}.html"
    encoded_name = quote(report_name)
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
    )
    db.commit()
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


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

    html = generate_audit_report_html(scan)
    try:
        pdf_bytes = render_report_pdf_from_html(html)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=501,
            detail=error_payload(
                detail=str(exc),
                error_code="report_generation_unavailable",
            ),
        ) from exc

    timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
    report_name = f"{Path(scan.filename).stem}_audit_report_{timestamp}.pdf"
    encoded_name = quote(report_name)
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
    )
    db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
