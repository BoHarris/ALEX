# routers/redacted_router.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from pathlib import Path
from mimetypes import guess_type
from sqlalchemy import desc

from database.database import SessionLocal
from database.models.scan_results import ScanResult
from services.audit_report_service import generate_audit_report_html, render_report_pdf_from_html

router = APIRouter(prefix="/redacted", tags=["Redacted"])

BASE_DIR = Path(__file__).resolve().parent.parent

REDACTED_DIR = BASE_DIR / "static" / "redacted"

@router.get("/files")
def list_redacted_files():
    if not REDACTED_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Redacted folder not found")
    files = [f.name for f in REDACTED_DIR.iterdir() if f.is_file()]
    return {"files": files}

@router.get("/download/{filename}")
def download_redacted_file(filename: str):
    path = REDACTED_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # auto‐guess the correct mime type
    mime, _ = guess_type(str(path))
    disposition = "inline" if mime =="application/pdf" else "attachment"
    return FileResponse(
        str(path),
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f"{disposition}; filename={filename}"}
    )


@router.get("/report/{filename}")
def download_scan_report(filename: str):
    db = SessionLocal()
    try:
        scan = (
            db.query(ScanResult)
            .filter(ScanResult.redacted_file_path.like(f"%{filename}"))
            .order_by(desc(ScanResult.scanned_at))
            .first()
        )
        if not scan:
            raise HTTPException(status_code=404, detail="No scan metadata found for this file")

        html = generate_audit_report_html(scan)
        timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
        report_name = f"{Path(filename).stem}_audit_report_{timestamp}.html"
        return HTMLResponse(
            content=html,
            status_code=200,
            headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
        )
    finally:
        db.close()


@router.get("/report/{filename}/pdf")
def download_scan_report_pdf(filename: str):
    db = SessionLocal()
    try:
        scan = (
            db.query(ScanResult)
            .filter(ScanResult.redacted_file_path.like(f"%{filename}"))
            .order_by(desc(ScanResult.scanned_at))
            .first()
        )
        if not scan:
            raise HTTPException(status_code=404, detail="No scan metadata found for this file")

        html = generate_audit_report_html(scan)
        try:
            pdf_bytes = render_report_pdf_from_html(html)
        except RuntimeError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc

        timestamp = scan.scanned_at.strftime("%Y%m%d_%H%M%S") if scan.scanned_at else "unknown_time"
        report_name = f"{Path(filename).stem}_audit_report_{timestamp}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
        )
    finally:
        db.close()
