"""add compliance test failure tasks

Revision ID: 20260311_0004_test_failure_tasks
Revises: 20260311_0003_test_result_tracking
Create Date: 2026-03-11 18:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0004_test_failure_tasks"
down_revision = "20260311_0003_test_result_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("compliance_test_failure_tasks"):
        op.create_table(
            "compliance_test_failure_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("compliance_record_id", sa.Integer(), sa.ForeignKey("compliance_records.id"), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("test_node_id", sa.String(), nullable=False),
            sa.Column("latest_failed_run_id", sa.Integer(), sa.ForeignKey("compliance_test_runs.id"), nullable=False),
            sa.Column("latest_failed_result_id", sa.Integer(), sa.ForeignKey("compliance_test_case_results.id"), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
            sa.Column("assignee_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
            sa.Column("failure_signature", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("compliance_record_id", name="uq_compliance_test_failure_tasks_record_id"),
        )

    task_indexes = {index["name"] for index in inspector.get_indexes("compliance_test_failure_tasks")} if inspector.has_table("compliance_test_failure_tasks") else set()
    if "ix_compliance_test_failure_tasks_organization_id" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_organization_id", "compliance_test_failure_tasks", ["organization_id"], unique=False)
    if "ix_compliance_test_failure_tasks_test_node_id" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_test_node_id", "compliance_test_failure_tasks", ["test_node_id"], unique=False)
    if "ix_compliance_test_failure_tasks_status" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_status", "compliance_test_failure_tasks", ["status"], unique=False)
    if "ix_compliance_test_failure_tasks_priority" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_priority", "compliance_test_failure_tasks", ["priority"], unique=False)
    if "ix_compliance_test_failure_tasks_assignee_employee_id" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_assignee_employee_id", "compliance_test_failure_tasks", ["assignee_employee_id"], unique=False)
    if "ix_compliance_test_failure_tasks_latest_failed_run_id" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_latest_failed_run_id", "compliance_test_failure_tasks", ["latest_failed_run_id"], unique=False)
    if "ix_compliance_test_failure_tasks_latest_failed_result_id" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_latest_failed_result_id", "compliance_test_failure_tasks", ["latest_failed_result_id"], unique=False)
    if "ix_compliance_test_failure_tasks_failure_signature" not in task_indexes:
        op.create_index("ix_compliance_test_failure_tasks_failure_signature", "compliance_test_failure_tasks", ["failure_signature"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_compliance_test_failure_tasks_failure_signature", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_latest_failed_result_id", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_latest_failed_run_id", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_assignee_employee_id", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_priority", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_status", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_test_node_id", table_name="compliance_test_failure_tasks")
    op.drop_index("ix_compliance_test_failure_tasks_organization_id", table_name="compliance_test_failure_tasks")
    op.drop_table("compliance_test_failure_tasks")
