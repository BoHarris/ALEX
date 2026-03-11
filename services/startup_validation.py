import importlib.util
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import inspect, text

from database.database import ENV, engine
from services.compliance_service import ensure_default_company_and_employee
from services.scan_service import initialize_scan_model

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations" / "versions"
MODEL_PATH = BASE_DIR / "models" / "xgboost_model.pkl"
FONT_PATH = BASE_DIR / "DejaVuSans.ttf"
REQUIRED_DIRS = (
    BASE_DIR / "uploads",
    BASE_DIR / "redacted",
    BASE_DIR / "logs",
)
REQUIRED_SCHEMA = {
    "users": {"id", "email", "role", "company_id", "refresh_version"},
    "pending_registrations": {"id", "email", "webauthn_user_handle", "challenge", "expires_at"},
    "refresh_sessions": {"id", "user_id", "refresh_jti_hash", "revoked", "created_at"},
    "scan_results": {"id", "user_id", "company_id", "filename", "redacted_type_counts"},
    "webauthn_challenges": {"id", "user_id", "challenge", "challenge_type", "expires_at"},
    "company_settings": {"id", "company_id", "default_policy_label", "allowed_upload_types"},
    "audit_events": {"id", "company_id", "user_id", "event_type", "event_category", "description", "event_metadata", "created_at"},
    "audit_logs": {"id", "user_id", "organization_id", "event_type", "event_category", "created_at"},
    "security_states": {"id", "namespace", "state_key", "counter_value", "expires_at"},
    "scan_quota_counters": {"id", "user_id", "day", "count"},
    "security_incidents": {"id", "severity", "status", "description", "detected_at"},
    "employees": {"id", "employee_id", "email", "role", "company_id", "user_id"},
    "compliance_records": {"id", "organization_id", "module", "title", "status", "created_at"},
    "compliance_comments": {"id", "compliance_record_id", "employee_id", "comment", "created_at"},
    "compliance_attachments": {"id", "compliance_record_id", "label", "path_or_url", "created_at"},
    "compliance_approvals": {"id", "compliance_record_id", "approver_employee_id", "status", "created_at"},
    "compliance_activities": {"id", "compliance_record_id", "action", "created_at"},
    "wiki_pages": {"id", "compliance_record_id", "slug", "category", "content_markdown"},
    "vendors": {"id", "compliance_record_id", "vendor_name", "service_category", "security_review_status"},
    "compliance_test_runs": {"id", "organization_id", "category", "suite_name", "dataset_name", "status", "total_tests", "passed_tests", "failed_tests", "accuracy_score", "run_at"},
    "compliance_test_case_results": {"id", "test_run_id", "name", "dataset_name", "expected_result", "actual_result", "status", "confidence_score", "last_run_at"},
    "compliance_test_failure_tasks": {"id", "compliance_record_id", "organization_id", "test_node_id", "latest_failed_run_id", "latest_failed_result_id", "status", "priority", "created_at"},
    "access_reviews": {"id", "compliance_record_id", "reviewer_employee_id", "reviewed_employee_id", "decision"},
    "training_modules": {"id", "organization_id", "title", "category"},
    "training_assignments": {"id", "compliance_record_id", "employee_id", "training_module_id", "completion_status"},
    "grc_incidents": {"id", "compliance_record_id", "severity", "description", "detected_at"},
    "hr_controls": {"id", "compliance_record_id", "employee_id", "control_type", "status"},
    "risk_register_items": {"id", "compliance_record_id", "risk_title", "risk_category", "risk_score"},
    "code_reviews": {"id", "compliance_record_id", "summary", "review_type", "risk_level", "created_by_employee_id"},
}


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing {name} environment variable")
    return value


def _require_effective_setting(name: str, default: str) -> str:
    value = (os.getenv(name) or default).strip()
    if not value:
        raise RuntimeError(f"Missing {name} environment variable")
    return value


def _resolve_origin() -> str:
    origin = (
        os.getenv("ORIGIN")
        or os.getenv("FRONTEND_ORIGIN")
        or "http://localhost:3000"
    ).strip()
    if not origin:
        raise RuntimeError("Missing ORIGIN environment variable")
    return origin


def _resolve_rp_id(origin: str) -> str:
    explicit_rp_id = (os.getenv("RP_ID") or "").strip()
    if explicit_rp_id:
        return explicit_rp_id

    parsed = urlparse(origin)
    if parsed.hostname:
        return parsed.hostname

    raise RuntimeError("Missing RP_ID environment variable")


def _is_local_runtime(origin: str, rp_id: str) -> bool:
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    return engine.dialect.name == "sqlite" and host in {"localhost", "127.0.0.1"} and rp_id in {
        "localhost",
        "127.0.0.1",
    }


def _validate_environment() -> None:
    secret_key = _require_env("SECRET_KEY")
    origin = _resolve_origin()
    rp_id = _resolve_rp_id(origin)
    is_local_runtime = _is_local_runtime(origin, rp_id)
    secure_cookies_enabled = ENV == "production"
    access_ttl = int(_require_effective_setting("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_ttl = int(_require_effective_setting("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
    challenge_ttl = int(_require_effective_setting("CHALLENGE_TTL_MINUTES", "5"))

    logger.info(
        "Startup environment | env=%s | secure_cookies=%s | db_dialect=%s | origin=%s | rp_id=%s | access_ttl_min=%s | refresh_ttl_min=%s | challenge_ttl_min=%s",
        ENV,
        secure_cookies_enabled,
        engine.dialect.name,
        origin,
        rp_id,
        access_ttl,
        refresh_ttl,
        challenge_ttl,
    )

    if len(secret_key) < 32:
        if ENV == "production":
            raise RuntimeError("SECRET_KEY is too short for production (minimum length: 32).")
        logger.warning("Startup validation: SECRET_KEY is shorter than recommended minimum length (32).")

    if ENV == "production":
        database_url = (os.getenv("DATABASE_URL") or "").strip()
        if not database_url:
            logger.warning(
                "Startup validation: DATABASE_URL is not set in production; falling back to local SQLite engine configuration."
            )
        if not is_local_runtime and not origin.lower().startswith("https://"):
            raise RuntimeError("ORIGIN must use HTTPS in production.")
        if not is_local_runtime and rp_id == "localhost":
            raise RuntimeError("Missing RP_ID environment variable")
        if not is_local_runtime and origin == "http://localhost:3000":
            raise RuntimeError("Missing ORIGIN environment variable")


def _validate_database() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Startup validation: database connectivity OK.")
    except Exception as exc:
        raise RuntimeError("Database connection failed") from exc


def _required_schema_revision() -> str:
    revisions = sorted(path.stem for path in MIGRATIONS_DIR.glob("*.py") if path.name != "__init__.py")
    if not revisions:
        raise RuntimeError("Migration configuration is missing. Create and apply migrations before startup.")
    return revisions[-1]


def _validate_schema_revision() -> None:
    expected_revision = _required_schema_revision()
    inspector = inspect(engine)
    if not inspector.has_table("alembic_version"):
        raise RuntimeError("Database schema version mismatch. Run migrations before starting the application.")

    with engine.connect() as conn:
        revisions = {row[0] for row in conn.execute(text("SELECT version_num FROM alembic_version"))}

    if revisions != {expected_revision}:
        raise RuntimeError(
            "Database schema version mismatch. "
            f"Expected revision {expected_revision}; run migrations before starting the application."
        )

    logger.info("Startup validation: schema revision OK (%s).", expected_revision)


def _validate_schema_state() -> None:
    missing_tables: list[str] = []
    missing_columns: list[str] = []
    inspector = inspect(engine)

    for table, required_columns in REQUIRED_SCHEMA.items():
        if not inspector.has_table(table):
            missing_tables.append(table)
            continue
        column_names = {column["name"] for column in inspector.get_columns(table)}
        for required in required_columns:
            if required not in column_names:
                missing_columns.append(f"{table}.{required}")

    if missing_tables or missing_columns:
        pieces = []
        if missing_tables:
            pieces.append(f"missing tables: {', '.join(sorted(missing_tables))}")
        if missing_columns:
            pieces.append(f"missing columns: {', '.join(sorted(missing_columns))}")
        raise RuntimeError(
            "Database schema validation failed; run migrations before startup (" + "; ".join(pieces) + ")."
        )

    logger.info("Startup validation: schema state OK.")


def _ensure_writable_directory(path: Path, label: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(f"{label} directory could not be created at {path}") from exc

    probe = path / ".startup_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        raise RuntimeError(f"{label} directory is not writable") from exc


def _validate_directories() -> None:
    _ensure_writable_directory(REQUIRED_DIRS[0], "Upload storage")
    _ensure_writable_directory(REQUIRED_DIRS[1], "Redacted file output")
    _ensure_writable_directory(REQUIRED_DIRS[2], "Log output")
    logger.info(
        "Startup validation: storage directories writable | uploads=%s | redacted=%s | logs=%s",
        REQUIRED_DIRS[0],
        REQUIRED_DIRS[1],
        REQUIRED_DIRS[2],
    )


def _validate_assets() -> None:
    if not FONT_PATH.is_file():
        raise RuntimeError(f"Required report asset not found at configured path: {FONT_PATH}")
    logger.info("Startup validation: required assets present.")


def _validate_model_loading():
    model = initialize_scan_model(MODEL_PATH)
    logger.info("Startup validation: XGBoost model loaded successfully from %s", MODEL_PATH)
    return model


def _validate_pdf_support() -> None:
    has_weasyprint = importlib.util.find_spec("weasyprint") is not None
    has_reportlab = importlib.util.find_spec("reportlab") is not None

    if has_weasyprint:
        logger.info("Startup validation: PDF reports enabled via weasyprint.")
        return

    if has_reportlab:
        logger.warning(
            "Startup validation: weasyprint not installed; PDF reports will use the reportlab fallback renderer."
        )
        return

    logger.warning(
        "Startup validation: PDF report dependencies missing; install weasyprint or reportlab to enable PDF downloads."
    )


def run_startup_validations():
    """
    Central startup validation entrypoint.
    Raises RuntimeError for blocking startup issues and logs warnings for optional capabilities.
    """
    _validate_environment()
    _validate_database()
    _validate_schema_revision()
    _validate_schema_state()
    from database.database import SessionLocal

    db = SessionLocal()
    try:
        ensure_default_company_and_employee(db)
    finally:
        db.close()
    _validate_directories()
    _validate_assets()
    model = _validate_model_loading()
    _validate_pdf_support()
    logger.info("Startup validation completed successfully.")
    return model
