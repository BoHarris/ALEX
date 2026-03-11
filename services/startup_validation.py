import importlib.util
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import inspect, text

from database.database import ENV, Base, engine
from database.models.audit_event import AuditEvent
from database.models.audit_log import AuditLog
from database.models.compliance_activity import ComplianceActivity
from database.models.compliance_approval import ComplianceApproval
from database.models.compliance_attachment import ComplianceAttachment
from database.models.compliance_comment import ComplianceComment
from database.models.compliance_record import ComplianceRecord
from database.models.compliance_test_case_result import ComplianceTestCaseResult
from database.models.compliance_test_run import ComplianceTestRun
from database.models.code_review import CodeReview
from database.models.company_settings import CompanySettings
from database.models.employee import Employee
from database.models.refresh_session import RefreshSession
from database.models.grc_incident import GRCIncident
from database.models.hr_control import HRControl
from database.models.access_review import AccessReview
from database.models.risk_register_item import RiskRegisterItem
from database.models.scan_quota_counter import ScanQuotaCounter
from database.models.security_state import SecurityState
from database.models.security_incident import SecurityIncident
from database.models.training_assignment import TrainingAssignment
from database.models.training_module import TrainingModule
from database.models.vendor import Vendor
from database.models.wiki_page import WikiPage
from services.compliance_service import ensure_default_company_and_employee
from services.scan_service import initialize_scan_model

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_model.pkl"
FONT_PATH = BASE_DIR / "DejaVuSans.ttf"
REQUIRED_DIRS = (
    BASE_DIR / "uploads",
    BASE_DIR / "redacted",
    BASE_DIR / "logs",
)
REQUIRED_SCHEMA = {
    "users": {"id", "email", "role", "company_id", "refresh_version"},
    "refresh_sessions": {"id", "user_id", "refresh_jti_hash", "revoked", "created_at"},
    "scan_results": {"id", "user_id", "company_id", "filename", "redacted_type_counts"},
    "webauthn_challenges": {"id", "user_id", "challenge", "challenge_type", "expires_at"},
    "company_settings": {"id", "company_id", "default_policy_label", "allowed_upload_types"},
    "audit_events": {"id", "company_id", "user_id", "event_type", "description", "created_at"},
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
    "compliance_test_runs": {"id", "organization_id", "category", "suite_name", "status", "run_at"},
    "compliance_test_case_results": {"id", "test_run_id", "name", "status", "last_run_at"},
    "access_reviews": {"id", "compliance_record_id", "reviewer_employee_id", "reviewed_employee_id", "decision"},
    "training_modules": {"id", "organization_id", "title", "category"},
    "training_assignments": {"id", "compliance_record_id", "employee_id", "training_module_id", "completion_status"},
    "grc_incidents": {"id", "compliance_record_id", "severity", "description", "detected_at"},
    "hr_controls": {"id", "compliance_record_id", "employee_id", "control_type", "status"},
    "risk_register_items": {"id", "compliance_record_id", "risk_title", "risk_category", "risk_score"},
    "code_reviews": {"id", "compliance_record_id", "summary", "review_type", "risk_level", "created_by_employee_id"},
}
ADDITIVE_SCHEMA_UPDATES = {
    "scan_results": [
        "ALTER TABLE scan_results ADD COLUMN status VARCHAR DEFAULT 'active' NOT NULL",
        "ALTER TABLE scan_results ADD COLUMN archived_at DATETIME",
        "ALTER TABLE scan_results ADD COLUMN retention_expiration DATETIME",
    ],
    "company_settings": [
        "ALTER TABLE company_settings ADD COLUMN retention_days INTEGER",
        "ALTER TABLE company_settings ADD COLUMN require_storage_encryption VARCHAR",
        "ALTER TABLE company_settings ADD COLUMN secure_cookie_enforced VARCHAR",
    ],
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


def _bootstrap_feature_tables() -> None:
    """
    Explicitly create beta feature tables when absent.
    This is restricted to additive table creation only (no column mutation).
    """
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CompanySettings.__table__,
            AuditEvent.__table__,
            AuditLog.__table__,
            SecurityState.__table__,
            ScanQuotaCounter.__table__,
            SecurityIncident.__table__,
            RefreshSession.__table__,
            Employee.__table__,
            ComplianceRecord.__table__,
            ComplianceComment.__table__,
            ComplianceAttachment.__table__,
            ComplianceApproval.__table__,
            ComplianceActivity.__table__,
            WikiPage.__table__,
            Vendor.__table__,
            ComplianceTestRun.__table__,
            ComplianceTestCaseResult.__table__,
            AccessReview.__table__,
            TrainingModule.__table__,
            TrainingAssignment.__table__,
            GRCIncident.__table__,
            HRControl.__table__,
            RiskRegisterItem.__table__,
            CodeReview.__table__,
        ],
    )
    logger.info(
        "Startup validation: feature tables ensured (company_settings, audit_events, audit_logs, security_states, scan_quota_counters, security_incidents, refresh_sessions)."
    )


def _apply_additive_schema_updates() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, statements in ADDITIVE_SCHEMA_UPDATES.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for statement in statements:
                column_name = statement.split("ADD COLUMN", 1)[1].strip().split(" ", 1)[0]
                if column_name in existing_columns:
                    continue
                conn.execute(text(statement))
                logger.warning("Startup validation: applied additive schema update %s.%s", table_name, column_name)


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
    if (os.getenv("ENABLE_STARTUP_SCHEMA_BOOTSTRAP") or "true").strip().lower() == "true":
        logger.warning(
            "Startup validation: ENABLE_STARTUP_SCHEMA_BOOTSTRAP=true; applying additive feature table bootstrap."
        )
        _bootstrap_feature_tables()
        _apply_additive_schema_updates()
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
