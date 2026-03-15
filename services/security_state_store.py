from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database.models.security_state import SecurityState


@dataclass(frozen=True)
class SecurityStateStoreError(RuntimeError):
    message: str = "Shared security state store is unavailable."

    def __str__(self) -> str:
        return self.message


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _purge_expired(db: Session, *, namespace: str) -> None:
    now = _utcnow()
    removed_any = False
    expired_items = (
        db.query(SecurityState)
        .filter(SecurityState.namespace == namespace)
        .all()
    )
    for item in expired_items:
        expires_at = _normalize_datetime(item.expires_at)
        if expires_at and expires_at <= now:
            db.delete(item)
            removed_any = True
    if removed_any:
        db.flush()


def increment_counter(
    db: Session,
    *,
    namespace: str,
    state_key: str,
    window_seconds: int,
) -> int:
    try:
        _purge_expired(db, namespace=namespace)
        record = (
            db.query(SecurityState)
            .filter(SecurityState.namespace == namespace, SecurityState.state_key == state_key)
            .first()
        )
        now = _utcnow()
        if record is None:
            record = SecurityState(
                namespace=namespace,
                state_key=state_key,
                counter_value=1,
                expires_at=now + timedelta(seconds=window_seconds),
            )
            db.add(record)
        else:
            record.counter_value += 1
            record.expires_at = now + timedelta(seconds=window_seconds)
            db.add(record)
        db.flush()
        return int(record.counter_value)
    except Exception as exc:
        raise SecurityStateStoreError() from exc


def get_counter(
    db: Session,
    *,
    namespace: str,
    state_key: str,
) -> int:
    try:
        record = (
            db.query(SecurityState)
            .filter(SecurityState.namespace == namespace, SecurityState.state_key == state_key)
            .first()
        )
        if not record:
            return 0
        expires_at = _normalize_datetime(record.expires_at)
        if expires_at and expires_at <= _utcnow():
            db.delete(record)
            db.flush()
            return 0
        return int(record.counter_value)
    except Exception as exc:
        raise SecurityStateStoreError() from exc


def reset_counter(
    db: Session,
    *,
    namespace: str,
    state_key: str,
) -> None:
    try:
        record = (
            db.query(SecurityState)
            .filter(SecurityState.namespace == namespace, SecurityState.state_key == state_key)
            .first()
        )
        if record is not None:
            db.delete(record)
            db.flush()
    except Exception as exc:
        raise SecurityStateStoreError() from exc


def register_distinct_member(
    db: Session,
    *,
    namespace: str,
    owner_key: str,
    member_key: str,
    window_seconds: int,
) -> int:
    try:
        _purge_expired(db, namespace=namespace)
        composite_key = f"{owner_key}:{member_key}"
        record = (
            db.query(SecurityState)
            .filter(SecurityState.namespace == namespace, SecurityState.state_key == composite_key)
            .first()
        )
        now = _utcnow()
        if record is None:
            record = SecurityState(
                namespace=namespace,
                state_key=composite_key,
                counter_value=1,
                expires_at=now + timedelta(seconds=window_seconds),
            )
            db.add(record)
        else:
            record.expires_at = now + timedelta(seconds=window_seconds)
            db.add(record)
        db.flush()
        return (
            db.query(SecurityState)
            .filter(SecurityState.namespace == namespace, SecurityState.state_key.like(f"{owner_key}:%"))
            .count()
        )
    except Exception as exc:
        raise SecurityStateStoreError() from exc
