from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.scan_results import ScanResult
from dependencies.tier_guard import get_current_user_context
from services.audit_report_service import (
    generate_audit_report_html,
    render_report_pdf_from_html,
)

router = APIRouter(prefix="/scans", tags=["Scans"])

BASE_DIR = Path(__file__).resolve().parent.parent


def _build_scan_query(db: Session, current_user: dict):
    query = db.query(ScanResult)
    if current_user["role"] == "admin" and current_user["company_id"] is not None:
        return query.filter(ScanResult.company_id == current_user["company_id"])
    return query.filter(ScanResult.user_id == current_user["user_id"])


def _authorize_scan_access(scan: ScanResult, current_user: dict) -> None:
    is_owner = scan.user_id == current_user["user_id"]
    is_company_admin = (
        current_user["role"] == "admin"
        and current_user["company_id"] is not None
        and scan.company_id == current_user["company_id"]
    )
    if not is_owner and not is_company_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this scan.")


def _get_scan_or_404(db: Session, scan_id: int) -> ScanResult:
    scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("")
def list_scans(
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scans = (
        _build_scan_query(db, current_user)
        .order_by(desc(ScanResult.scanned_at))
        .all()
    )
    return {
        "scans": [
            {
                "scan_id": scan.id,
                "filename": scan.filename,
                "file_type": scan.file_type,
                "risk_score": scan.risk_score,
                "total_pii_found": scan.total_pii_found,
                "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            }
            for scan in scans
        ]
    }


@router.get("/{scan_id}/download")
def download_redacted_file(
    scan_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)

    if not scan.redacted_file_path:
        raise HTTPException(status_code=404, detail="Redacted file path not found")

    path = BASE_DIR / scan.redacted_file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Redacted file not found")

    mime, _ = guess_type(str(path))
    
    scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return FileResponse(
        str(path),
        media_type=mime or "application/octet-stream",
        filename=path.name,
    )
    
    



@router.get("/{scan_id}/report/html")
def download_scan_report(
    scan_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)

    html = generate_audit_report_html(scan)
    timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
    report_name = f"{Path(scan.filename).stem}_audit_report_{timestamp}.html"
    encoded_name = quote(report_name)
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@router.get("/{scan_id}/report/pdf")
def download_scan_report_pdf(
    scan_id: int,
    current_user: dict = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    scan = _get_scan_or_404(db, scan_id)
    _authorize_scan_access(scan, current_user)

    html = generate_audit_report_html(scan)
    try:
        pdf_bytes = render_report_pdf_from_html(html)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
    report_name = f"{Path(scan.filename).stem}_audit_report_{timestamp}.pdf"
    encoded_name = quote(report_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
