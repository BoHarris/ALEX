from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database.models.company_settings import CompanySettings
from database.models.scan_results import ScanResult
from utils.plan_features import get_plan_features


def resolve_retention_days(db: Session, company_id: int | None, tier: str | None) -> int:
    if company_id is not None:
        settings = db.query(CompanySettings).filter(CompanySettings.company_id == company_id).first()
        if settings and settings.retention_days:
            return max(1, int(settings.retention_days))
        if settings and settings.retention_days_display:
            return max(1, int(settings.retention_days_display))
    plan = get_plan_features(tier)
    return int(plan.get("retention_days", 30))


def build_retention_expiration(*, scanned_at: datetime | None, retention_days: int) -> datetime:
    reference = scanned_at or datetime.now(timezone.utc)
    return reference + timedelta(days=max(1, retention_days))


def apply_retention_state(db: Session, scan: ScanResult) -> ScanResult:
    if scan.retention_expiration and scan.status not in {"expired", "deleted"}:
        now = datetime.now(timezone.utc)
        expiry = scan.retention_expiration
        if expiry.tzinfo is None:
            now = now.replace(tzinfo=None)
        if expiry <= now:
            scan.status = "expired"
            db.add(scan)
    return scan


def apply_retention_state_bulk(db: Session, scans: list[ScanResult]) -> list[ScanResult]:
    changed = False
    for scan in scans:
        previous = scan.status
        apply_retention_state(db, scan)
        if scan.status != previous:
            changed = True
    if changed:
        db.commit()
    return scans
