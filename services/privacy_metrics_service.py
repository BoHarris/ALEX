from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models.scan_results import ScanResult
from services.scan_service import parse_scan_result_metadata


def _scope_scan_query(db: Session, *, company_id: int):
    return db.query(ScanResult).filter(ScanResult.company_id == company_id)


def get_privacy_metrics(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
) -> dict[str, object]:
    base_query = _scope_scan_query(db, company_id=company_id)
    total_scans = base_query.with_entities(func.count(ScanResult.id)).scalar() or 0
    total_redactions = base_query.with_entities(func.coalesce(func.sum(ScanResult.total_pii_found), 0)).scalar() or 0

    pii_distribution: dict[str, int] = {}
    redaction_rows = base_query.with_entities(ScanResult.redacted_type_counts).all()
    for (raw_metadata,) in redaction_rows:
        counts, _ = parse_scan_result_metadata(raw_metadata)
        for pii_type, count in counts.items():
            pii_distribution[pii_type] = pii_distribution.get(pii_type, 0) + int(count)

    window_start = datetime.now(timezone.utc) - timedelta(days=activity_window_days)
    activity_rows = (
        base_query.with_entities(
            func.date(ScanResult.scanned_at).label("scan_day"),
            func.count(ScanResult.id).label("scan_count"),
        )
        .filter(ScanResult.scanned_at >= window_start)
        .group_by(func.date(ScanResult.scanned_at))
        .order_by(func.date(ScanResult.scanned_at).asc())
        .all()
    )

    recent_scan_activity = [
        {"date": str(scan_day), "scans": int(scan_count)}
        for scan_day, scan_count in activity_rows
        if scan_day is not None
    ]

    return {
        "total_scans": int(total_scans),
        "total_sensitive_fields_detected": int(total_redactions),
        "total_redactions": int(total_redactions),
        "pii_distribution": dict(sorted(pii_distribution.items())),
        "recent_scan_activity": recent_scan_activity,
    }
