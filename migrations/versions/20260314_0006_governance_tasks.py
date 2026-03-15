"""add governance task workflow tables

Revision ID: 20260314_0006_governance_tasks
Revises: 20260314_0005_mvp_readiness_features
Create Date: 2026-03-14 01:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0006_governance_tasks"
down_revision = "20260314_0005_mvp_readiness_features"
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
        "governance_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("source_type", sa.String(), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.String()),
        sa.Column("source_module", sa.String(), nullable=False, server_default="manual"),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("grc_incidents.id")),
        sa.Column("assignee_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("reporter_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("linked_source", sa.String(), nullable=True),
        sa.Column("linked_source_type", sa.String(), nullable=True),
        sa.Column("linked_source_id", sa.Integer(), nullable=True),
    )
    _create_indexes(
        "governance_tasks",
        [
            ("ix_governance_tasks_id", ["id"], False),
            ("ix_governance_tasks_company_id", ["company_id"], False),
            ("ix_governance_tasks_title", ["title"], False),
            ("ix_governance_tasks_status", ["status"], False),
            ("ix_governance_tasks_priority", ["priority"], False),
            ("ix_governance_tasks_source_type", ["source_type"], False),
            ("ix_governance_tasks_source_id", ["source_id"], False),
            ("ix_governance_tasks_source_module", ["source_module"], False),
            ("ix_governance_tasks_incident_id", ["incident_id"], False),
            ("ix_governance_tasks_assignee_employee_id", ["assignee_employee_id"], False),
            ("ix_governance_tasks_reporter_employee_id", ["reporter_employee_id"], False),
            ("ix_governance_tasks_due_date", ["due_date"], False),
            ("ix_governance_tasks_created_at", ["created_at"], False),
            ("ix_governance_tasks_resolved_at", ["resolved_at"], False),
            ("ix_governance_tasks_linked_source", ["linked_source"], False),
            ("ix_governance_tasks_linked_source_type", ["linked_source_type"], False),
            ("ix_governance_tasks_linked_source_id", ["linked_source_id"], False),
        ],
    )

    op.create_table(
        "governance_task_activities",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("governance_tasks.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("actor_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("from_value", sa.String()),
        sa.Column("to_value", sa.String()),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_indexes(
        "governance_task_activities",
        [
            ("ix_governance_task_activities_id", ["id"], False),
            ("ix_governance_task_activities_task_id", ["task_id"], False),
            ("ix_governance_task_activities_company_id", ["company_id"], False),
            ("ix_governance_task_activities_actor_employee_id", ["actor_employee_id"], False),
            ("ix_governance_task_activities_action", ["action"], False),
            ("ix_governance_task_activities_created_at", ["created_at"], False),
        ],
    )


def downgrade() -> None:
    _drop_indexes(
        "governance_task_activities",
        [
            "ix_governance_task_activities_created_at",
            "ix_governance_task_activities_action",
            "ix_governance_task_activities_actor_employee_id",
            "ix_governance_task_activities_company_id",
            "ix_governance_task_activities_task_id",
            "ix_governance_task_activities_id",
        ],
    )
    op.drop_table("governance_task_activities")

    _drop_indexes(
        "governance_tasks",
        [
            "ix_governance_tasks_resolved_at",
            "ix_governance_tasks_created_at",
            "ix_governance_tasks_due_date",
            "ix_governance_tasks_reporter_employee_id",
            "ix_governance_tasks_assignee_employee_id",
            "ix_governance_tasks_incident_id",
            "ix_governance_tasks_source_module",
            "ix_governance_tasks_source_id",
            "ix_governance_tasks_source_type",
            "ix_governance_tasks_priority",
            "ix_governance_tasks_status",
            "ix_governance_tasks_title",
            "ix_governance_tasks_company_id",
            "ix_governance_tasks_id",
        ],
    )
    op.drop_table("governance_tasks")
