from pathlib import Path
import os
import sys
import shutil
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-length-32!!")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import Base
from database.models.company_settings import CompanySettings
from database.models.company import Company
from database.models.scan_quota_counter import ScanQuotaCounter
from database.models.security_state import SecurityState
from database.models.user import User
from dependencies.tier_guard import _parse_subject_as_int
from routers import predict as predict_router
from routers import redacted_router
from utils.auth_utils import create_access_token, decode_token_with_error
from utils.tier_limiter import has_remaining_scan_quota, release_scan_quota_reservation, reserve_scan_quota
from services.security_state_store import SecurityStateStoreError

try:
    from routers import webauthn_auth
except ModuleNotFoundError:
    webauthn_auth = None


def test_parse_subject_invalid_returns_auth_error():
    with pytest.raises(HTTPException) as exc:
        _parse_subject_as_int("not-a-number")
    assert exc.value.status_code == 401


def test_access_decode_rejects_refresh_type_token():
    token = create_access_token({"sub": "123", "typ": "refresh"})
    payload, error = decode_token_with_error(token)
    assert payload is None
    assert error == "invalid_token"


def _make_local_test_dir() -> Path:
    base = PROJECT_ROOT / ".test_tmp" / f"hardening_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def test_resolve_redacted_file_path_rejects_escape(monkeypatch):
    base = _make_local_test_dir()
    redacted_dir = base / "redacted"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(redacted_router, "BASE_DIR", base)
    monkeypatch.setattr(redacted_router, "REDACTED_BASE_DIR", redacted_dir.resolve())

    try:
        with pytest.raises(HTTPException) as exc:
            redacted_router._resolve_redacted_file_path("../secrets.txt")
        assert exc.value.status_code == 403
    finally:
        shutil.rmtree(base.parent, ignore_errors=True)


def test_resolve_redacted_file_path_accepts_valid_file(monkeypatch):
    base = _make_local_test_dir()
    redacted_dir = base / "redacted"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    allowed = redacted_dir / "redacted_1.csv"
    allowed.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(redacted_router, "BASE_DIR", base)
    monkeypatch.setattr(redacted_router, "REDACTED_BASE_DIR", redacted_dir.resolve())

    try:
        resolved = redacted_router._resolve_redacted_file_path(str(Path("redacted") / "redacted_1.csv"))
        assert resolved == allowed.resolve()
    finally:
        shutil.rmtree(base.parent, ignore_errors=True)


def test_quota_reserve_and_release():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[User.__table__, ScanQuotaCounter.__table__])
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()

    user = User(first_name="A", last_name="B", email="a@example.com", role="member", tier="free")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert has_remaining_scan_quota(session, user.id, "free") is True
    assert reserve_scan_quota(session, user.id, "free") is True
    assert has_remaining_scan_quota(session, user.id, "free") is False

    release_scan_quota_reservation(session, user.id)
    assert has_remaining_scan_quota(session, user.id, "free") is True


def test_company_upload_policy_parsing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Company.__table__, CompanySettings.__table__])
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()

    session.add(Company(id=77, company_name="Acme"))
    session.commit()

    settings = CompanySettings(company_id=77, allowed_upload_types='["csv",".pdf"," json "]')
    session.add(settings)
    session.commit()

    allowed = predict_router._company_allowed_extensions(session, 77)
    assert allowed == {".csv", ".pdf", ".json"}


def test_auth_rate_limit_blocks_when_threshold_reached(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")
    monkeypatch.setattr(webauthn_auth, "AUTH_RATE_WINDOW_SECONDS", 60)
    monkeypatch.setattr(webauthn_auth, "AUTH_RATE_LIMIT_PER_IP", 1)
    monkeypatch.setattr(webauthn_auth, "AUTH_RATE_LIMIT_PER_IDENTIFIER", 1)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[SecurityState.__table__])
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()

    class _Client:
        host = "127.0.0.1"

    class _Request:
        client = _Client()

    request = _Request()
    webauthn_auth._enforce_auth_rate_limit(db=session, request=request, identifier="a@example.com")
    with pytest.raises(HTTPException) as exc:
        webauthn_auth._enforce_auth_rate_limit(db=session, request=request, identifier="a@example.com")
    assert exc.value.status_code == 429


def test_auth_rate_limit_returns_degraded_security_error_when_store_unavailable(monkeypatch):
    if webauthn_auth is None:
        pytest.skip("webauthn dependency is not installed in this test environment")

    class _Client:
        host = "127.0.0.1"

    class _Request:
        client = _Client()
        headers = {"user-agent": "pytest"}

    monkeypatch.setattr(
        "services.security_service._increment_threshold_counter",
        lambda *args, **kwargs: (_ for _ in ()).throw(SecurityStateStoreError()),
    )

    with pytest.raises(HTTPException) as exc:
        webauthn_auth._enforce_auth_rate_limit(
            db=None,
            request=_Request(),
            identifier="a@example.com",
        )
    assert exc.value.status_code == 503
    assert exc.value.detail["error_code"] == "security_state_unavailable"
