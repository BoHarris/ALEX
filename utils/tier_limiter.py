from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models.scan_quota_counter import ScanQuotaCounter
from utils.plan_features import get_plan_features


def _daily_limit_for_tier(tier: str) -> int:
    features = get_plan_features(tier)
    return int(features["scan_limit_per_day"])


def _get_or_create_counter(db: Session, user_id: int, day: date) -> ScanQuotaCounter:
    record = (
        db.query(ScanQuotaCounter)
        .filter(
            ScanQuotaCounter.user_id == user_id,
            ScanQuotaCounter.day == day,
        )
        .first()
    )
    if record:
        return record

    record = ScanQuotaCounter(user_id=user_id, day=day, count=0)
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        record = (
            db.query(ScanQuotaCounter)
            .filter(
                ScanQuotaCounter.user_id == user_id,
                ScanQuotaCounter.day == day,
            )
            .first()
        )
        if record:
            return record
        raise
    return record


def has_remaining_scan_quota(db: Session, user_id: int | str, tier: str) -> bool:
    daily_limit = _daily_limit_for_tier(tier)
    today = date.today()
    try:
        record = _get_or_create_counter(db, int(user_id), today)
        return record.count < daily_limit
    except IntegrityError:
        db.rollback()
        return False


def reserve_scan_quota(db: Session, user_id: int | str, tier: str) -> bool:
    daily_limit = _daily_limit_for_tier(tier)
    today = date.today()
    try:
        record = _get_or_create_counter(db, int(user_id), today)
        if record.count >= daily_limit:
            db.rollback()
            return False
        record.count += 1
        db.add(record)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def release_scan_quota_reservation(db: Session, user_id: int | str) -> None:
    today = date.today()
    try:
        record = _get_or_create_counter(db, int(user_id), today)
        if record.count > 0:
            record.count -= 1
            db.add(record)
            db.commit()
    except IntegrityError:
        db.rollback()


def check_scan_allowed(db: Session, user_id: str, tier: str) -> bool:
    # Backward-compat wrapper for existing call sites.
    return reserve_scan_quota(db, user_id, tier)
