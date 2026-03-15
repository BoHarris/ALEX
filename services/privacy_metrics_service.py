from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models.scan_results import ScanResult
from services.scan_service import parse_scan_result_metadata

logger = logging.getLogger(__name__)


def _validate_activity_window_days(days: int) -> None:
    """
    Validate activity window days parameter.
    
    Raises ValueError if days is outside acceptable range.
    """
    if not isinstance(days, int):
        raise ValueError(f"activity_window_days must be an integer, got {type(days).__name__}")
    if days <= 0:
        raise ValueError(f"activity_window_days must be positive, got {days}")
    if days > 3650:  # ~10 years - reasonable upper bound
        raise ValueError(f"activity_window_days must be <= 3650, got {days}")


def _validate_company_id(company_id: int) -> None:
    """
    Validate company_id parameter.
    
    Raises ValueError if company_id is not a positive integer.
    """
    if not isinstance(company_id, int):
        raise ValueError(f"company_id must be an integer, got {type(company_id).__name__}")
    if company_id <= 0:
        raise ValueError(f"company_id must be positive, got {company_id}")


def _scope_scan_query(db: Session, *, company_id: int):
    return db.query(ScanResult).filter(ScanResult.company_id == company_id)


def get_privacy_metrics(
    db: Session,
    *,
    company_id: int,
    activity_window_days: int = 30,
) -> dict[str, object]:
    """
    Calculate privacy metrics for a company's scan results.
    
    Args:
        db: Database session
        company_id: Company ID (must be positive integer)
        activity_window_days: Number of days to consider for recent activity (1-3650, default 30)
    
    Returns:
        Dictionary with:
        - total_scans: Total number of scans
        - total_sensitive_fields_detected: Total PII fields found
        - total_redactions: Same as total_sensitive_fields_detected
        - pii_distribution: Count by PII type
        - recent_scan_activity: Activity grouped by date in window
    
    Raises:
        ValueError: If parameters are invalid
        Exception: If database query fails (logged)
    """
    # Validate inputs for defense in depth
    try:
        _validate_company_id(company_id)
        _validate_activity_window_days(activity_window_days)
    except ValueError as e:
        logger.error(f"Privacy metrics validation failed: {e}")
        raise
    
    try:
        base_query = _scope_scan_query(db, company_id=company_id)
        
        # Fetch total scans
        total_scans = base_query.with_entities(func.count(ScanResult.id)).scalar() or 0
        
        # Fetch total redactions
        total_redactions = (
            base_query.with_entities(func.coalesce(func.sum(ScanResult.total_pii_found), 0)).scalar() or 0
        )
        
        # Aggregate PII distribution with error tracking
        pii_distribution: dict[str, int] = {}
        parsing_errors = 0
        
        redaction_rows = base_query.with_entities(ScanResult.redacted_type_counts).all()
        for (raw_metadata,) in redaction_rows:
            try:
                counts, _ = parse_scan_result_metadata(raw_metadata)
                for pii_type, count in counts.items():
                    pii_distribution[pii_type] = pii_distribution.get(pii_type, 0) + int(count)
            except Exception as e:
                parsing_errors += 1
                logger.warning(
                    f"Failed to parse scan metadata for company {company_id}: {e}",
                    exc_info=False,
                )
        
        if parsing_errors > 0:
            logger.info(f"PII distribution: {parsing_errors} metadata parsing errors for company {company_id}")
        
        # Fetch recent activity within window
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
        
        # Log metrics summary
        logger.info(
            f"Privacy metrics calculated for company {company_id}: "
            f"total_scans={total_scans}, total_redactions={total_redactions}, "
            f"pii_types={len(pii_distribution)}, activity_window_days={activity_window_days}"
        )
        
        return {
            "total_scans": int(total_scans),
            "total_sensitive_fields_detected": int(total_redactions),
            "total_redactions": int(total_redactions),
            "pii_distribution": dict(sorted(pii_distribution.items())),
            "recent_scan_activity": recent_scan_activity,
        }
        
    except Exception as e:
        logger.error(f"Database error calculating privacy metrics for company {company_id}: {e}", exc_info=True)
        raise
