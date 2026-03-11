from pathlib import Path

from fastapi import HTTPException

from routers import scans as scans_router
from routers.scans import (
    _authorize_scan_access,
    _build_scan_query,
    _get_scan_or_404,
    _parse_redacted_type_counts,
    archive_scan,
    download_redacted_file,
    download_scan_report,
    download_scan_report_html,
    download_scan_report_pdf,
    get_scan,
    list_scans,
    restore_scan,
    router,
)
from utils.api_errors import error_payload

BASE_DIR = scans_router.BASE_DIR
REDACTED_BASE_DIR = scans_router.REDACTED_BASE_DIR


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

# Compatibility module for legacy imports. The canonical scan router lives in `routers.scans`.
