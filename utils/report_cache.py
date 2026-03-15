from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from database.models.scan_results import ScanResult
from services.audit_report_service import generate_audit_report_html, render_report_pdf_from_html

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_BASE_DIR = (BASE_DIR / "reports").resolve()


def _report_filename(scan: ScanResult, extension: str) -> str:
    safe_stem = Path(scan.filename or f"scan-{scan.id}").stem or f"scan-{scan.id}"
    return f"{safe_stem}_audit_report_{scan.id}.{extension}"


def _resolve_report_path(stored_path: str | None) -> Path | None:
    if not stored_path:
        return None
    raw_path = Path(stored_path)
    candidate = raw_path.resolve() if raw_path.is_absolute() else (BASE_DIR / raw_path).resolve()
    try:
        candidate.relative_to(REPORTS_BASE_DIR)
    except ValueError:
        return None
    return candidate


def get_cached_report_path(scan: ScanResult, *, report_format: str) -> Path | None:
    stored_path = scan.report_html_path if report_format == "html" else scan.report_pdf_path
    candidate = _resolve_report_path(stored_path)
    if candidate and candidate.is_file():
        return candidate
    return None


def cache_html_report(db: Session, scan: ScanResult) -> Path:
    REPORTS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    cached = get_cached_report_path(scan, report_format="html")
    if cached:
        return cached

    html_path = REPORTS_BASE_DIR / _report_filename(scan, "html")
    html_path.write_text(generate_audit_report_html(scan), encoding="utf-8")
    scan.report_html_path = str(html_path.relative_to(BASE_DIR))
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return html_path


def cache_pdf_report(db: Session, scan: ScanResult) -> Path:
    REPORTS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    cached = get_cached_report_path(scan, report_format="pdf")
    if cached:
        return cached

    html_path = cache_html_report(db, scan)
    pdf_path = REPORTS_BASE_DIR / _report_filename(scan, "pdf")
    pdf_path.write_bytes(render_report_pdf_from_html(html_path.read_text(encoding="utf-8")))
    scan.report_pdf_path = str(pdf_path.relative_to(BASE_DIR))
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return pdf_path
