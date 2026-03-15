"""add mvp readiness schema features

Revision ID: 20260314_0005_mvp_readiness_features
Revises: 20260311_0004_test_failure_tasks
Create Date: 2026-03-14 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0005_mvp_readiness_features"
down_revision = "20260311_0004_test_failure_tasks"
branch_labels = None
depends_on = None


def _existing_columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _existing_indexes(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("users"):
        user_columns = _existing_columns(inspector, "users")
        if "has_completed_onboarding" not in user_columns:
            op.add_column(
                "users",
                sa.Column("has_completed_onboarding", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
            with op.batch_alter_table("users") as batch_op:
                batch_op.alter_column("has_completed_onboarding", existing_type=sa.Boolean(), server_default=None)

    if inspector.has_table("refresh_sessions"):
        refresh_columns = _existing_columns(inspector, "refresh_sessions")
        if "device_info" not in refresh_columns:
            op.add_column("refresh_sessions", sa.Column("device_info", sa.String(), nullable=True))

    if inspector.has_table("scan_results"):
        scan_columns = _existing_columns(inspector, "scan_results")
        if "report_html_path" not in scan_columns:
            op.add_column("scan_results", sa.Column("report_html_path", sa.String(), nullable=True))
        if "report_pdf_path" not in scan_columns:
            op.add_column("scan_results", sa.Column("report_pdf_path", sa.String(), nullable=True))

    if not inspector.has_table("scan_jobs"):
        op.create_table(
            "scan_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("scan_result_id", sa.Integer(), sa.ForeignKey("scan_results.id"), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("file_type", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
        )
        inspector = sa.inspect(bind)
    scan_job_indexes = _existing_indexes(inspector, "scan_jobs") if inspector.has_table("scan_jobs") else set()
    for name, cols, unique in (
        ("ix_scan_jobs_company_id", ["company_id"], False),
        ("ix_scan_jobs_user_id", ["user_id"], False),
        ("ix_scan_jobs_scan_result_id", ["scan_result_id"], False),
        ("ix_scan_jobs_status", ["status"], False),
        ("ix_scan_jobs_created_at", ["created_at"], False),
    ):
        if name not in scan_job_indexes:
            op.create_index(name, "scan_jobs", cols, unique=unique)

    if not inspector.has_table("organization_memberships"):
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="INVITED"),
            sa.Column("invited_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("company_id", "user_id", name="uq_organization_memberships_company_user"),
        )
        inspector = sa.inspect(bind)
    membership_indexes = _existing_indexes(inspector, "organization_memberships") if inspector.has_table("organization_memberships") else set()
    for name, cols, unique in (
        ("ix_organization_memberships_company_id", ["company_id"], False),
        ("ix_organization_memberships_user_id", ["user_id"], False),
        ("ix_organization_memberships_status", ["status"], False),
        ("ix_organization_memberships_created_at", ["created_at"], False),
    ):
        if name not in membership_indexes:
            op.create_index(name, "organization_memberships", cols, unique=unique)

    if not inspector.has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("hashed_key", sa.String(), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
            sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        )
        inspector = sa.inspect(bind)
    api_key_indexes = _existing_indexes(inspector, "api_keys") if inspector.has_table("api_keys") else set()
    for name, cols, unique in (
        ("ix_api_keys_company_id", ["company_id"], False),
        ("ix_api_keys_created_by_user_id", ["created_by_user_id"], False),
        ("ix_api_keys_hashed_key", ["hashed_key"], True),
        ("ix_api_keys_created_at", ["created_at"], False),
    ):
        if name not in api_key_indexes:
            op.create_index(name, "api_keys", cols, unique=unique)

    if not inspector.has_table("security_events"):
        op.create_table(
            "security_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("severity", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("event_metadata", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        inspector = sa.inspect(bind)
    security_event_indexes = _existing_indexes(inspector, "security_events") if inspector.has_table("security_events") else set()
    for name, cols, unique in (
        ("ix_security_events_company_id", ["company_id"], False),
        ("ix_security_events_user_id", ["user_id"], False),
        ("ix_security_events_event_type", ["event_type"], False),
        ("ix_security_events_severity", ["severity"], False),
        ("ix_security_events_created_at", ["created_at"], False),
    ):
        if name not in security_event_indexes:
            op.create_index(name, "security_events", cols, unique=unique)


def downgrade() -> None:
    for name in (
        "ix_security_events_created_at",
        "ix_security_events_severity",
        "ix_security_events_event_type",
        "ix_security_events_user_id",
        "ix_security_events_company_id",
    ):
        op.drop_index(name, table_name="security_events")
    op.drop_table("security_events")

    for name in (
        "ix_api_keys_created_at",
        "ix_api_keys_hashed_key",
        "ix_api_keys_created_by_user_id",
        "ix_api_keys_company_id",
    ):
        op.drop_index(name, table_name="api_keys")
    op.drop_table("api_keys")

    for name in (
        "ix_organization_memberships_created_at",
        "ix_organization_memberships_status",
        "ix_organization_memberships_user_id",
        "ix_organization_memberships_company_id",
    ):
        op.drop_index(name, table_name="organization_memberships")
    op.drop_table("organization_memberships")

    for name in (
        "ix_scan_jobs_created_at",
        "ix_scan_jobs_status",
        "ix_scan_jobs_scan_result_id",
        "ix_scan_jobs_user_id",
        "ix_scan_jobs_company_id",
    ):
        op.drop_index(name, table_name="scan_jobs")
    op.drop_table("scan_jobs")

    op.drop_column("scan_results", "report_pdf_path")
    op.drop_column("scan_results", "report_html_path")
    op.drop_column("refresh_sessions", "device_info")
    op.drop_column("users", "has_completed_onboarding")
