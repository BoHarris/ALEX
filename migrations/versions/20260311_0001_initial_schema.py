"""initial schema

Revision ID: 20260311_0001_initial_schema
Revises:
Create Date: 2026-03-11 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _create_indexes(table_name: str, indexes: list[tuple[str, list[str], bool]]) -> None:
    for index_name, columns, unique in indexes:
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_indexes(table_name: str, index_names: list[str]) -> None:
    for index_name in index_names:
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_name", sa.String(), nullable=False, unique=True),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("country", sa.String()),
        sa.Column("industry", sa.String()),
        sa.Column("company_size", sa.Integer()),
        sa.Column("subscription_tier", sa.String()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("is_verified", sa.Boolean()),
        sa.Column("deleted_at", sa.DateTime(timezone=False)),
    )
    _create_indexes(
        "companies",
        [
            ("ix_companies_company_name", ["company_name"], True),
            ("ix_companies_id", ["id"], False),
        ],
    )

    op.create_table(
        "pending_registrations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("company_name", sa.String()),
        sa.Column("create_company", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer()),
        sa.Column("webauthn_user_handle", sa.String(), nullable=False, unique=True),
        sa.Column("challenge", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "pending_registrations",
        [
            ("ix_pending_registrations_company_id", ["company_id"], False),
            ("ix_pending_registrations_email", ["email"], False),
            ("ix_pending_registrations_expires_at", ["expires_at"], False),
            ("ix_pending_registrations_id", ["id"], False),
            ("ix_pending_registrations_webauthn_user_handle", ["webauthn_user_handle"], True),
        ],
    )

    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_notes", sa.Text()),
    )
    _create_indexes(
        "security_incidents",
        [
            ("ix_security_incidents_detected_at", ["detected_at"], False),
            ("ix_security_incidents_id", ["id"], False),
            ("ix_security_incidents_severity", ["severity"], False),
            ("ix_security_incidents_status", ["status"], False),
        ],
    )

    op.create_table(
        "security_states",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("state_key", sa.String(), nullable=False),
        sa.Column("counter_value", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("namespace", "state_key", name="uq_security_states_namespace_key"),
    )
    _create_indexes(
        "security_states",
        [
            ("ix_security_states_created_at", ["created_at"], False),
            ("ix_security_states_expires_at", ["expires_at"], False),
            ("ix_security_states_id", ["id"], False),
            ("ix_security_states_namespace", ["namespace"], False),
            ("ix_security_states_state_key", ["state_key"], False),
        ],
    )

    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, unique=True),
        sa.Column("default_policy_label", sa.String()),
        sa.Column("default_report_display_name", sa.String()),
        sa.Column("allowed_upload_types", sa.Text()),
        sa.Column("contact_email", sa.String()),
        sa.Column("compliance_mode", sa.String()),
        sa.Column("branding_primary_color", sa.String()),
        sa.Column("retention_days_display", sa.Integer()),
        sa.Column("retention_days", sa.Integer()),
        sa.Column("require_storage_encryption", sa.String()),
        sa.Column("secure_cookie_enforced", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "company_settings",
        [
            ("ix_company_settings_company_id", ["company_id"], True),
            ("ix_company_settings_id", ["id"], False),
        ],
    )

    op.create_table(
        "compliance_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("suite_name", sa.String(), nullable=False),
        sa.Column("dataset_name", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_tests", sa.Integer(), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=False),
        sa.Column("failed_tests", sa.Integer(), nullable=False),
        sa.Column("skipped_tests", sa.Integer(), nullable=False),
        sa.Column("accuracy_score", sa.Numeric(precision=6, scale=4)),
        sa.Column("coverage_percent", sa.Numeric(precision=5, scale=2)),
        sa.Column("report_link", sa.Text()),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_test_runs",
        [
            ("ix_compliance_test_runs_category", ["category"], False),
            ("ix_compliance_test_runs_dataset_name", ["dataset_name"], False),
            ("ix_compliance_test_runs_id", ["id"], False),
            ("ix_compliance_test_runs_organization_id", ["organization_id"], False),
            ("ix_compliance_test_runs_run_at", ["run_at"], False),
            ("ix_compliance_test_runs_status", ["status"], False),
        ],
    )

    op.create_table(
        "training_modules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("document_link", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "training_modules",
        [
            ("ix_training_modules_category", ["category"], False),
            ("ix_training_modules_id", ["id"], False),
            ("ix_training_modules_organization_id", ["organization_id"], False),
        ],
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String()),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("phone_number", sa.String()),
        sa.Column("timezone", sa.String()),
        sa.Column("locale", sa.String()),
        sa.Column("profile_picture", sa.String()),
        sa.Column("refresh_version", sa.Integer(), nullable=False),
        sa.Column("email_verification_token", sa.String()),
        sa.Column("webauthn_credential_id", sa.String(), unique=True),
        sa.Column("webauthn_public_key", sa.String()),
        sa.Column("webauthn_sign_count", sa.Integer(), nullable=False),
        sa.Column("webauthn_transports", sa.String()),
        sa.Column("webauthn_user_handle", sa.String(), unique=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
    )
    _create_indexes(
        "users",
        [
            ("ix_users_email", ["email"], True),
            ("ix_users_id", ["id"], False),
            ("ix_users_webauthn_credential_id", ["webauthn_credential_id"], True),
            ("ix_users_webauthn_user_handle", ["webauthn_user_handle"], True),
        ],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("target_type", sa.String()),
        sa.Column("target_id", sa.String()),
        sa.Column("event_metadata", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "audit_events",
        [
            ("ix_audit_events_company_id", ["company_id"], False),
            ("ix_audit_events_created_at", ["created_at"], False),
            ("ix_audit_events_event_category", ["event_category"], False),
            ("ix_audit_events_event_type", ["event_type"], False),
            ("ix_audit_events_id", ["id"], False),
            ("ix_audit_events_user_id", ["user_id"], False),
        ],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_category", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String()),
        sa.Column("resource_id", sa.String()),
        sa.Column("ip_address", sa.String()),
        sa.Column("device_fingerprint", sa.String()),
        sa.Column("event_metadata", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "audit_logs",
        [
            ("ix_audit_logs_created_at", ["created_at"], False),
            ("ix_audit_logs_event_category", ["event_category"], False),
            ("ix_audit_logs_event_type", ["event_type"], False),
            ("ix_audit_logs_id", ["id"], False),
            ("ix_audit_logs_organization_id", ["organization_id"], False),
            ("ix_audit_logs_resource_id", ["resource_id"], False),
            ("ix_audit_logs_resource_type", ["resource_type"], False),
            ("ix_audit_logs_user_id", ["user_id"], False),
        ],
    )

    op.create_table(
        "compliance_test_case_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("test_run_id", sa.Integer(), sa.ForeignKey("compliance_test_runs.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("dataset_name", sa.String()),
        sa.Column("file_name", sa.String()),
        sa.Column("description", sa.Text()),
        sa.Column("expected_result", sa.String()),
        sa.Column("actual_result", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=6, scale=4)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("output", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_test_case_results",
        [
            ("ix_compliance_test_case_results_dataset_name", ["dataset_name"], False),
            ("ix_compliance_test_case_results_id", ["id"], False),
            ("ix_compliance_test_case_results_last_run_at", ["last_run_at"], False),
            ("ix_compliance_test_case_results_name", ["name"], False),
            ("ix_compliance_test_case_results_status", ["status"], False),
            ("ix_compliance_test_case_results_test_run_id", ["test_run_id"], False),
        ],
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("employee_id", sa.String(), nullable=False, unique=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("department", sa.String()),
        sa.Column("job_title", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
    )
    _create_indexes(
        "employees",
        [
            ("ix_employees_company_id", ["company_id"], False),
            ("ix_employees_email", ["email"], True),
            ("ix_employees_employee_id", ["employee_id"], True),
            ("ix_employees_id", ["id"], False),
            ("ix_employees_role", ["role"], False),
            ("ix_employees_status", ["status"], False),
            ("ix_employees_user_id", ["user_id"], True),
        ],
    )

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refresh_jti_hash", sa.String(), nullable=False, unique=True),
        sa.Column("session_binding_hash", sa.String()),
        sa.Column("issued_ip_address", sa.String()),
        sa.Column("last_seen_ip_address", sa.String()),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "refresh_sessions",
        [
            ("ix_refresh_sessions_created_at", ["created_at"], False),
            ("ix_refresh_sessions_id", ["id"], False),
            ("ix_refresh_sessions_refresh_jti_hash", ["refresh_jti_hash"], True),
            ("ix_refresh_sessions_revoked", ["revoked"], False),
            ("ix_refresh_sessions_user_id", ["user_id"], False),
        ],
    )

    op.create_table(
        "scan_quota_counters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "day", name="uq_scan_quota_user_day"),
    )
    _create_indexes(
        "scan_quota_counters",
        [
            ("ix_scan_quota_counters_day", ["day"], False),
            ("ix_scan_quota_counters_id", ["id"], False),
            ("ix_scan_quota_counters_user_id", ["user_id"], False),
        ],
    )

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("pii_types_found", sa.String()),
        sa.Column("redacted_type_counts", sa.String()),
        sa.Column("total_pii_found", sa.Integer(), nullable=False),
        sa.Column("redacted_file_path", sa.String()),
        sa.Column("scanned_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("retention_expiration", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "scan_results",
        [
            ("ix_scan_results_id", ["id"], False),
            ("ix_scan_results_retention_expiration", ["retention_expiration"], False),
            ("ix_scan_results_status", ["status"], False),
        ],
    )

    op.create_table(
        "webauthn_challenges",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("challenge", sa.String(), nullable=False),
        sa.Column("challenge_type", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "webauthn_challenges",
        [
            ("ix_webauthn_challenges_challenge_type", ["challenge_type"], False),
            ("ix_webauthn_challenges_id", ["id"], False),
            ("ix_webauthn_challenges_user_id", ["user_id"], False),
        ],
    )

    op.create_table(
        "compliance_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("owner_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("review_date", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("updated_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "compliance_records",
        [
            ("ix_compliance_records_created_by_employee_id", ["created_by_employee_id"], False),
            ("ix_compliance_records_due_date", ["due_date"], False),
            ("ix_compliance_records_id", ["id"], False),
            ("ix_compliance_records_module", ["module"], False),
            ("ix_compliance_records_organization_id", ["organization_id"], False),
            ("ix_compliance_records_owner_employee_id", ["owner_employee_id"], False),
            ("ix_compliance_records_review_date", ["review_date"], False),
            ("ix_compliance_records_status", ["status"], False),
            ("ix_compliance_records_updated_by_employee_id", ["updated_by_employee_id"], False),
        ],
    )

    op.create_table(
        "access_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("reviewer_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("reviewed_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("permissions_snapshot", sa.Text()),
        sa.Column("last_access_review_date", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "access_reviews",
        [
            ("ix_access_reviews_compliance_record_id", ["compliance_record_id"], True),
            ("ix_access_reviews_decision", ["decision"], False),
            ("ix_access_reviews_id", ["id"], False),
            ("ix_access_reviews_reviewed_employee_id", ["reviewed_employee_id"], False),
            ("ix_access_reviews_reviewer_employee_id", ["reviewer_employee_id"], False),
        ],
    )

    op.create_table(
        "code_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("review_type", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("created_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("assigned_reviewer_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("target_release", sa.String()),
        sa.Column("prompt_text", sa.Text()),
        sa.Column("design_notes", sa.Text()),
        sa.Column("code_notes", sa.Text()),
        sa.Column("files_impacted", sa.Text()),
        sa.Column("testing_notes", sa.Text()),
        sa.Column("security_review_notes", sa.Text()),
        sa.Column("privacy_review_notes", sa.Text()),
        sa.Column("reviewer_decision", sa.String()),
        sa.Column("reviewer_comments", sa.Text()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "code_reviews",
        [
            ("ix_code_reviews_assigned_reviewer_employee_id", ["assigned_reviewer_employee_id"], False),
            ("ix_code_reviews_compliance_record_id", ["compliance_record_id"], True),
            ("ix_code_reviews_created_by_employee_id", ["created_by_employee_id"], False),
            ("ix_code_reviews_id", ["id"], False),
            ("ix_code_reviews_review_type", ["review_type"], False),
            ("ix_code_reviews_reviewer_decision", ["reviewer_decision"], False),
            ("ix_code_reviews_risk_level", ["risk_level"], False),
            ("ix_code_reviews_target_release", ["target_release"], False),
        ],
    )

    op.create_table(
        "compliance_activities",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_activities",
        [
            ("ix_compliance_activities_action", ["action"], False),
            ("ix_compliance_activities_compliance_record_id", ["compliance_record_id"], False),
            ("ix_compliance_activities_employee_id", ["employee_id"], False),
            ("ix_compliance_activities_id", ["id"], False),
        ],
    )

    op.create_table(
        "compliance_approvals",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False),
        sa.Column("approver_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "compliance_approvals",
        [
            ("ix_compliance_approvals_approver_employee_id", ["approver_employee_id"], False),
            ("ix_compliance_approvals_compliance_record_id", ["compliance_record_id"], False),
            ("ix_compliance_approvals_id", ["id"], False),
            ("ix_compliance_approvals_status", ["status"], False),
        ],
    )

    op.create_table(
        "compliance_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("attachment_type", sa.String(), nullable=False),
        sa.Column("path_or_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_attachments",
        [
            ("ix_compliance_attachments_compliance_record_id", ["compliance_record_id"], False),
            ("ix_compliance_attachments_employee_id", ["employee_id"], False),
            ("ix_compliance_attachments_id", ["id"], False),
        ],
    )

    op.create_table(
        "compliance_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_comments",
        [
            ("ix_compliance_comments_compliance_record_id", ["compliance_record_id"], False),
            ("ix_compliance_comments_employee_id", ["employee_id"], False),
            ("ix_compliance_comments_id", ["id"], False),
        ],
    )

    op.create_table(
        "compliance_test_failure_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("test_node_id", sa.String(), nullable=False),
        sa.Column("latest_failed_run_id", sa.Integer(), sa.ForeignKey("compliance_test_runs.id"), nullable=False),
        sa.Column("latest_failed_result_id", sa.Integer(), sa.ForeignKey("compliance_test_case_results.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("assignee_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("failure_signature", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "compliance_test_failure_tasks",
        [
            ("ix_compliance_test_failure_tasks_assignee_employee_id", ["assignee_employee_id"], False),
            ("ix_compliance_test_failure_tasks_compliance_record_id", ["compliance_record_id"], True),
            ("ix_compliance_test_failure_tasks_failure_signature", ["failure_signature"], False),
            ("ix_compliance_test_failure_tasks_id", ["id"], False),
            ("ix_compliance_test_failure_tasks_latest_failed_result_id", ["latest_failed_result_id"], False),
            ("ix_compliance_test_failure_tasks_latest_failed_run_id", ["latest_failed_run_id"], False),
            ("ix_compliance_test_failure_tasks_organization_id", ["organization_id"], False),
            ("ix_compliance_test_failure_tasks_priority", ["priority"], False),
            ("ix_compliance_test_failure_tasks_status", ["status"], False),
            ("ix_compliance_test_failure_tasks_test_node_id", ["test_node_id"], False),
        ],
    )

    op.create_table(
        "grc_incidents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_to_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("root_cause", sa.Text()),
        sa.Column("lessons_learned", sa.Text()),
    )
    _create_indexes(
        "grc_incidents",
        [
            ("ix_grc_incidents_assigned_to_employee_id", ["assigned_to_employee_id"], False),
            ("ix_grc_incidents_compliance_record_id", ["compliance_record_id"], True),
            ("ix_grc_incidents_detected_by_employee_id", ["detected_by_employee_id"], False),
            ("ix_grc_incidents_id", ["id"], False),
            ("ix_grc_incidents_severity", ["severity"], False),
        ],
    )

    op.create_table(
        "hr_controls",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("control_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
    )
    _create_indexes(
        "hr_controls",
        [
            ("ix_hr_controls_compliance_record_id", ["compliance_record_id"], True),
            ("ix_hr_controls_control_type", ["control_type"], False),
            ("ix_hr_controls_employee_id", ["employee_id"], False),
            ("ix_hr_controls_id", ["id"], False),
            ("ix_hr_controls_reviewed_by_employee_id", ["reviewed_by_employee_id"], False),
            ("ix_hr_controls_status", ["status"], False),
        ],
    )

    op.create_table(
        "risk_register_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("risk_title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_category", sa.String(), nullable=False),
        sa.Column("likelihood", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("mitigation_plan", sa.Text()),
        sa.Column("owner_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("review_date", sa.DateTime(timezone=True)),
    )
    _create_indexes(
        "risk_register_items",
        [
            ("ix_risk_register_items_compliance_record_id", ["compliance_record_id"], True),
            ("ix_risk_register_items_id", ["id"], False),
            ("ix_risk_register_items_owner_employee_id", ["owner_employee_id"], False),
            ("ix_risk_register_items_risk_category", ["risk_category"], False),
            ("ix_risk_register_items_risk_score", ["risk_score"], False),
            ("ix_risk_register_items_risk_title", ["risk_title"], False),
        ],
    )

    op.create_table(
        "training_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("training_module_id", sa.Integer(), sa.ForeignKey("training_modules.id"), nullable=False),
        sa.Column("completion_status", sa.String(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("quiz_score", sa.Numeric(precision=5, scale=2)),
    )
    _create_indexes(
        "training_assignments",
        [
            ("ix_training_assignments_completion_status", ["completion_status"], False),
            ("ix_training_assignments_compliance_record_id", ["compliance_record_id"], True),
            ("ix_training_assignments_employee_id", ["employee_id"], False),
            ("ix_training_assignments_id", ["id"], False),
            ("ix_training_assignments_training_module_id", ["training_module_id"], False),
        ],
    )

    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("vendor_name", sa.String(), nullable=False),
        sa.Column("service_category", sa.String(), nullable=False),
        sa.Column("data_access_level", sa.String(), nullable=False),
        sa.Column("contract_start_date", sa.DateTime(timezone=True)),
        sa.Column("contract_end_date", sa.DateTime(timezone=True)),
        sa.Column("risk_rating", sa.String()),
        sa.Column("security_review_status", sa.String(), nullable=False),
        sa.Column("last_review_date", sa.DateTime(timezone=True)),
        sa.Column("document_links", sa.Text()),
    )
    _create_indexes(
        "vendors",
        [
            ("ix_vendors_compliance_record_id", ["compliance_record_id"], True),
            ("ix_vendors_id", ["id"], False),
            ("ix_vendors_risk_rating", ["risk_rating"], False),
            ("ix_vendors_security_review_status", ["security_review_status"], False),
            ("ix_vendors_vendor_name", ["vendor_name"], False),
        ],
    )

    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False, unique=True),
        sa.Column("parent_page_id", sa.Integer(), sa.ForeignKey("wiki_pages.id")),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("template_name", sa.String()),
        sa.Column("tags", sa.Text()),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    _create_indexes(
        "wiki_pages",
        [
            ("ix_wiki_pages_category", ["category"], False),
            ("ix_wiki_pages_compliance_record_id", ["compliance_record_id"], True),
            ("ix_wiki_pages_id", ["id"], False),
            ("ix_wiki_pages_parent_page_id", ["parent_page_id"], False),
            ("ix_wiki_pages_slug", ["slug"], True),
        ],
    )


def downgrade() -> None:
    _drop_indexes(
        "wiki_pages",
        [
            "ix_wiki_pages_slug",
            "ix_wiki_pages_parent_page_id",
            "ix_wiki_pages_id",
            "ix_wiki_pages_compliance_record_id",
            "ix_wiki_pages_category",
        ],
    )
    op.drop_table("wiki_pages")

    _drop_indexes(
        "vendors",
        [
            "ix_vendors_vendor_name",
            "ix_vendors_security_review_status",
            "ix_vendors_risk_rating",
            "ix_vendors_id",
            "ix_vendors_compliance_record_id",
        ],
    )
    op.drop_table("vendors")

    _drop_indexes(
        "training_assignments",
        [
            "ix_training_assignments_training_module_id",
            "ix_training_assignments_id",
            "ix_training_assignments_employee_id",
            "ix_training_assignments_compliance_record_id",
            "ix_training_assignments_completion_status",
        ],
    )
    op.drop_table("training_assignments")

    _drop_indexes(
        "risk_register_items",
        [
            "ix_risk_register_items_risk_title",
            "ix_risk_register_items_risk_score",
            "ix_risk_register_items_risk_category",
            "ix_risk_register_items_owner_employee_id",
            "ix_risk_register_items_id",
            "ix_risk_register_items_compliance_record_id",
        ],
    )
    op.drop_table("risk_register_items")

    _drop_indexes(
        "hr_controls",
        [
            "ix_hr_controls_status",
            "ix_hr_controls_reviewed_by_employee_id",
            "ix_hr_controls_id",
            "ix_hr_controls_employee_id",
            "ix_hr_controls_control_type",
            "ix_hr_controls_compliance_record_id",
        ],
    )
    op.drop_table("hr_controls")

    _drop_indexes(
        "grc_incidents",
        [
            "ix_grc_incidents_severity",
            "ix_grc_incidents_id",
            "ix_grc_incidents_detected_by_employee_id",
            "ix_grc_incidents_compliance_record_id",
            "ix_grc_incidents_assigned_to_employee_id",
        ],
    )
    op.drop_table("grc_incidents")

    _drop_indexes(
        "compliance_test_failure_tasks",
        [
            "ix_compliance_test_failure_tasks_test_node_id",
            "ix_compliance_test_failure_tasks_status",
            "ix_compliance_test_failure_tasks_priority",
            "ix_compliance_test_failure_tasks_organization_id",
            "ix_compliance_test_failure_tasks_latest_failed_run_id",
            "ix_compliance_test_failure_tasks_latest_failed_result_id",
            "ix_compliance_test_failure_tasks_id",
            "ix_compliance_test_failure_tasks_failure_signature",
            "ix_compliance_test_failure_tasks_compliance_record_id",
            "ix_compliance_test_failure_tasks_assignee_employee_id",
        ],
    )
    op.drop_table("compliance_test_failure_tasks")

    _drop_indexes(
        "compliance_comments",
        [
            "ix_compliance_comments_id",
            "ix_compliance_comments_employee_id",
            "ix_compliance_comments_compliance_record_id",
        ],
    )
    op.drop_table("compliance_comments")

    _drop_indexes(
        "compliance_attachments",
        [
            "ix_compliance_attachments_id",
            "ix_compliance_attachments_employee_id",
            "ix_compliance_attachments_compliance_record_id",
        ],
    )
    op.drop_table("compliance_attachments")

    _drop_indexes(
        "compliance_approvals",
        [
            "ix_compliance_approvals_status",
            "ix_compliance_approvals_id",
            "ix_compliance_approvals_compliance_record_id",
            "ix_compliance_approvals_approver_employee_id",
        ],
    )
    op.drop_table("compliance_approvals")

    _drop_indexes(
        "compliance_activities",
        [
            "ix_compliance_activities_id",
            "ix_compliance_activities_employee_id",
            "ix_compliance_activities_compliance_record_id",
            "ix_compliance_activities_action",
        ],
    )
    op.drop_table("compliance_activities")

    _drop_indexes(
        "code_reviews",
        [
            "ix_code_reviews_target_release",
            "ix_code_reviews_risk_level",
            "ix_code_reviews_reviewer_decision",
            "ix_code_reviews_review_type",
            "ix_code_reviews_id",
            "ix_code_reviews_created_by_employee_id",
            "ix_code_reviews_compliance_record_id",
            "ix_code_reviews_assigned_reviewer_employee_id",
        ],
    )
    op.drop_table("code_reviews")

    _drop_indexes(
        "access_reviews",
        [
            "ix_access_reviews_reviewer_employee_id",
            "ix_access_reviews_reviewed_employee_id",
            "ix_access_reviews_id",
            "ix_access_reviews_decision",
            "ix_access_reviews_compliance_record_id",
        ],
    )
    op.drop_table("access_reviews")

    _drop_indexes(
        "compliance_records",
        [
            "ix_compliance_records_updated_by_employee_id",
            "ix_compliance_records_status",
            "ix_compliance_records_review_date",
            "ix_compliance_records_owner_employee_id",
            "ix_compliance_records_organization_id",
            "ix_compliance_records_module",
            "ix_compliance_records_id",
            "ix_compliance_records_due_date",
            "ix_compliance_records_created_by_employee_id",
        ],
    )
    op.drop_table("compliance_records")

    _drop_indexes(
        "webauthn_challenges",
        [
            "ix_webauthn_challenges_user_id",
            "ix_webauthn_challenges_id",
            "ix_webauthn_challenges_challenge_type",
        ],
    )
    op.drop_table("webauthn_challenges")

    _drop_indexes(
        "scan_results",
        [
            "ix_scan_results_status",
            "ix_scan_results_retention_expiration",
            "ix_scan_results_id",
        ],
    )
    op.drop_table("scan_results")

    _drop_indexes(
        "scan_quota_counters",
        [
            "ix_scan_quota_counters_user_id",
            "ix_scan_quota_counters_id",
            "ix_scan_quota_counters_day",
        ],
    )
    op.drop_table("scan_quota_counters")

    _drop_indexes(
        "refresh_sessions",
        [
            "ix_refresh_sessions_user_id",
            "ix_refresh_sessions_revoked",
            "ix_refresh_sessions_refresh_jti_hash",
            "ix_refresh_sessions_id",
            "ix_refresh_sessions_created_at",
        ],
    )
    op.drop_table("refresh_sessions")

    _drop_indexes(
        "employees",
        [
            "ix_employees_user_id",
            "ix_employees_status",
            "ix_employees_role",
            "ix_employees_id",
            "ix_employees_employee_id",
            "ix_employees_email",
            "ix_employees_company_id",
        ],
    )
    op.drop_table("employees")

    _drop_indexes(
        "compliance_test_case_results",
        [
            "ix_compliance_test_case_results_test_run_id",
            "ix_compliance_test_case_results_status",
            "ix_compliance_test_case_results_name",
            "ix_compliance_test_case_results_last_run_at",
            "ix_compliance_test_case_results_id",
            "ix_compliance_test_case_results_dataset_name",
        ],
    )
    op.drop_table("compliance_test_case_results")

    _drop_indexes(
        "audit_logs",
        [
            "ix_audit_logs_user_id",
            "ix_audit_logs_resource_type",
            "ix_audit_logs_resource_id",
            "ix_audit_logs_organization_id",
            "ix_audit_logs_id",
            "ix_audit_logs_event_type",
            "ix_audit_logs_event_category",
            "ix_audit_logs_created_at",
        ],
    )
    op.drop_table("audit_logs")

    _drop_indexes(
        "audit_events",
        [
            "ix_audit_events_user_id",
            "ix_audit_events_id",
            "ix_audit_events_event_type",
            "ix_audit_events_event_category",
            "ix_audit_events_created_at",
            "ix_audit_events_company_id",
        ],
    )
    op.drop_table("audit_events")

    _drop_indexes(
        "users",
        [
            "ix_users_webauthn_user_handle",
            "ix_users_webauthn_credential_id",
            "ix_users_id",
            "ix_users_email",
        ],
    )
    op.drop_table("users")

    _drop_indexes(
        "training_modules",
        [
            "ix_training_modules_organization_id",
            "ix_training_modules_id",
            "ix_training_modules_category",
        ],
    )
    op.drop_table("training_modules")

    _drop_indexes(
        "compliance_test_runs",
        [
            "ix_compliance_test_runs_status",
            "ix_compliance_test_runs_run_at",
            "ix_compliance_test_runs_organization_id",
            "ix_compliance_test_runs_id",
            "ix_compliance_test_runs_dataset_name",
            "ix_compliance_test_runs_category",
        ],
    )
    op.drop_table("compliance_test_runs")

    _drop_indexes(
        "company_settings",
        [
            "ix_company_settings_id",
            "ix_company_settings_company_id",
        ],
    )
    op.drop_table("company_settings")

    _drop_indexes(
        "security_states",
        [
            "ix_security_states_state_key",
            "ix_security_states_namespace",
            "ix_security_states_id",
            "ix_security_states_expires_at",
            "ix_security_states_created_at",
        ],
    )
    op.drop_table("security_states")

    _drop_indexes(
        "security_incidents",
        [
            "ix_security_incidents_status",
            "ix_security_incidents_severity",
            "ix_security_incidents_id",
            "ix_security_incidents_detected_at",
        ],
    )
    op.drop_table("security_incidents")

    _drop_indexes(
        "pending_registrations",
        [
            "ix_pending_registrations_webauthn_user_handle",
            "ix_pending_registrations_id",
            "ix_pending_registrations_expires_at",
            "ix_pending_registrations_email",
            "ix_pending_registrations_company_id",
        ],
    )
    op.drop_table("pending_registrations")

    _drop_indexes(
        "companies",
        [
            "ix_companies_id",
            "ix_companies_company_name",
        ],
    )
    op.drop_table("companies")
