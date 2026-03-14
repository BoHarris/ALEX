from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database.models.scan_results import ScanResult
from services.scan_service import parse_scan_result_metadata


def _scope_scan_query(db: Session, *, company_id: int):
    return db.query(ScanResult).filter(ScanResult.company_id == company_id)


def _coerce_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_scan_metric_snapshot(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
    as_of: datetime | None = None,
    scan_rows: list[ScanResult] | None = None,
) -> dict[str, object]:
    effective_as_of = _coerce_datetime(as_of) or datetime.now(timezone.utc)
    rows = scan_rows if scan_rows is not None else _scope_scan_query(db, company_id=company_id).all()
    filtered_rows = [
        row for row in rows
        if (_coerce_datetime(row.scanned_at) or effective_as_of) <= effective_as_of
    ]

    pii_distribution: dict[str, int] = {}
    findings: list[dict[str, object]] = []
    activity_counts: dict[str, int] = {}
    window_start = effective_as_of - timedelta(days=activity_window_days)
    sensitive_scan_count = 0
    successful_redaction_scans = 0
    dataset_names: set[str] = set()

    for row in filtered_rows:
        scanned_at = _coerce_datetime(row.scanned_at)
        counts, detections = parse_scan_result_metadata(row.redacted_type_counts)
        if row.filename:
            dataset_names.add(str(row.filename))
        if (row.total_pii_found or 0) > 0:
            sensitive_scan_count += 1
            if row.redacted_file_path:
                successful_redaction_scans += 1
        for pii_type, count in counts.items():
            pii_distribution[pii_type] = pii_distribution.get(pii_type, 0) + int(count)
        for detection in detections:
            findings.append(
                {
                    "scan_id": row.id,
                    "filename": row.filename,
                    "scanned_at": scanned_at.isoformat() if scanned_at else None,
                    **detection,
                }
            )
        if scanned_at is not None and scanned_at >= window_start:
            activity_key = scanned_at.date().isoformat()
            activity_counts[activity_key] = activity_counts.get(activity_key, 0) + 1

    total_redactions = sum(int(row.total_pii_found or 0) for row in filtered_rows)

    return {
        "total_scans": len(filtered_rows),
        "total_sensitive_fields_detected": total_redactions,
        "total_redactions": total_redactions,
        "pii_distribution": dict(sorted(pii_distribution.items())),
        "recent_scan_activity": [
            {"date": activity_date, "scans": scan_count}
            for activity_date, scan_count in sorted(activity_counts.items())
        ],
        "scan_findings": findings,
        "sensitive_scan_count": sensitive_scan_count,
        "successful_redaction_scans": successful_redaction_scans,
        "dataset_names": sorted(dataset_names),
    }


def get_privacy_metrics(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
) -> dict[str, object]:
    snapshot = get_scan_metric_snapshot(
        db,
        company_id=company_id,
        activity_window_days=activity_window_days,
    )
    return {
        "total_scans": int(snapshot["total_scans"]),
        "total_sensitive_fields_detected": int(snapshot["total_sensitive_fields_detected"]),
        "total_redactions": int(snapshot["total_redactions"]),
        "pii_distribution": dict(snapshot["pii_distribution"]),
        "recent_scan_activity": list(snapshot["recent_scan_activity"]),
    }
