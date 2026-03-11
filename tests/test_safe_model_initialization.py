import importlib

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

import database.database as database_module
import services.scan_service as scan_service
import services.startup_validation as startup_validation


def test_scan_service_does_not_load_model_during_import(monkeypatch):
    def _explode(_path):
        raise AssertionError("joblib.load should not run during module import")

    monkeypatch.setattr(scan_service.joblib, "load", _explode)
    reloaded = importlib.reload(scan_service)

    assert reloaded is scan_service
    assert reloaded._xgb_model is None


def test_startup_validation_loads_model_successfully(monkeypatch):
    sentinel_model = object()
    monkeypatch.setattr(startup_validation, "_validate_environment", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_database", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_schema_revision", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_schema_state", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_directories", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_assets", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_pdf_support", lambda: None)
    monkeypatch.setattr(startup_validation, "ensure_default_company_and_employee", lambda db: None)
    monkeypatch.setattr(startup_validation, "initialize_scan_model", lambda _path: sentinel_model)

    class _DummySession:
        def close(self):
            return None

    monkeypatch.setattr(database_module, "SessionLocal", lambda: _DummySession())

    result = startup_validation.run_startup_validations()

    assert result is sentinel_model


def test_startup_validation_fails_gracefully_when_model_load_fails(monkeypatch):
    monkeypatch.setattr(startup_validation, "_validate_environment", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_database", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_schema_revision", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_schema_state", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_directories", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_assets", lambda: None)
    monkeypatch.setattr(startup_validation, "_validate_pdf_support", lambda: None)
    monkeypatch.setattr(startup_validation, "ensure_default_company_and_employee", lambda db: None)

    class _DummySession:
        def close(self):
            return None

    monkeypatch.setattr(database_module, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(
        startup_validation,
        "initialize_scan_model",
        lambda _path: (_ for _ in ()).throw(
            RuntimeError(
                "StartupError: XGBoost model could not be loaded. Verify model file exists and is compatible with current environment."
            )
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        startup_validation.run_startup_validations()

    assert "XGBoost model could not be loaded" in str(exc.value)


def test_schema_revision_validation_passes_when_revision_matches(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": startup_validation._required_schema_revision()},
        )

    monkeypatch.setattr(startup_validation, "engine", engine)
    monkeypatch.setattr(startup_validation, "MIGRATIONS_DIR", startup_validation.BASE_DIR / "migrations" / "versions")

    startup_validation._validate_schema_revision()


def test_schema_revision_validation_fails_when_revision_is_outdated(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": "outdated_revision"},
        )

    monkeypatch.setattr(startup_validation, "engine", engine)
    monkeypatch.setattr(startup_validation, "MIGRATIONS_DIR", startup_validation.BASE_DIR / "migrations" / "versions")

    with pytest.raises(RuntimeError) as exc:
        startup_validation._validate_schema_revision()

    assert "Database schema version mismatch" in str(exc.value)


def test_predict_pii_columns_uses_initialized_model():
    class _FakeModel:
        def __init__(self):
            self.calls = 0

        def predict(self, frame):
            self.calls += 1
            return [0, 1]

    model = _FakeModel()
    previous_model = scan_service._xgb_model
    scan_service.set_scan_model(model)

    try:
        frame = pd.DataFrame(
            {
                "email": ["ada@example.com", "grace@example.com"],
                "notes": ["safe", "safe"],
            }
        )
        pii_columns, detection_results = scan_service._predict_pii_columns(frame)
    finally:
        scan_service.set_scan_model(previous_model)

    assert pii_columns == ["email"]
    assert detection_results[0]["detected_type"] == "PII_EMAIL"
    assert model.calls == 1
