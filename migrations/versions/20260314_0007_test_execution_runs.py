"""extend compliance test runs for executable governance runs

Revision ID: 20260314_0007_test_execution_runs
Revises: 20260314_0006_governance_tasks
Create Date: 2026-03-14 03:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0007_test_execution_runs"
down_revision = "20260314_0006_governance_tasks"
branch_labels = None
depends_on = None

FK_RUNS_TRIGGERED_BY_USER = "fk_compliance_test_runs_triggered_by_user_id_users"
FK_RUNS_TRIGGERED_BY_EMPLOYEE = "fk_compliance_test_runs_triggered_by_employee_id_employees"


def upgrade() -> None:
    with op.batch_alter_table("compliance_test_runs", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("triggered_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("triggered_by_employee_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("run_type", sa.String(), nullable=False, server_default="recorded"))
        batch_op.add_column(sa.Column("trigger_source", sa.String(), nullable=False, server_default="manual"))
        batch_op.add_column(sa.Column("execution_engine", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("pytest_node_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("return_code", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("stdout", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("stderr", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("failure_summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.Text(), nullable=True))
        batch_op.create_foreign_key(FK_RUNS_TRIGGERED_BY_USER, "users", ["triggered_by_user_id"], ["id"])
        batch_op.create_foreign_key(FK_RUNS_TRIGGERED_BY_EMPLOYEE, "employees", ["triggered_by_employee_id"], ["id"])
        batch_op.create_index("ix_compliance_test_runs_triggered_by_user_id", ["triggered_by_user_id"])
        batch_op.create_index("ix_compliance_test_runs_triggered_by_employee_id", ["triggered_by_employee_id"])
        batch_op.create_index("ix_compliance_test_runs_run_type", ["run_type"])
        batch_op.create_index("ix_compliance_test_runs_trigger_source", ["trigger_source"])
        batch_op.create_index("ix_compliance_test_runs_pytest_node_id", ["pytest_node_id"])
        batch_op.create_index("ix_compliance_test_runs_started_at", ["started_at"])
        batch_op.create_index("ix_compliance_test_runs_completed_at", ["completed_at"])


def downgrade() -> None:
    with op.batch_alter_table("compliance_test_runs", recreate="always") as batch_op:
        batch_op.drop_index("ix_compliance_test_runs_completed_at")
        batch_op.drop_index("ix_compliance_test_runs_started_at")
        batch_op.drop_index("ix_compliance_test_runs_pytest_node_id")
        batch_op.drop_index("ix_compliance_test_runs_trigger_source")
        batch_op.drop_index("ix_compliance_test_runs_run_type")
        batch_op.drop_index("ix_compliance_test_runs_triggered_by_employee_id")
        batch_op.drop_index("ix_compliance_test_runs_triggered_by_user_id")
        batch_op.drop_constraint(FK_RUNS_TRIGGERED_BY_EMPLOYEE, type_="foreignkey")
        batch_op.drop_constraint(FK_RUNS_TRIGGERED_BY_USER, type_="foreignkey")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("failure_summary")
        batch_op.drop_column("stderr")
        batch_op.drop_column("stdout")
        batch_op.drop_column("return_code")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("pytest_node_id")
        batch_op.drop_column("execution_engine")
        batch_op.drop_column("trigger_source")
        batch_op.drop_column("run_type")
        batch_op.drop_column("triggered_by_employee_id")
        batch_op.drop_column("triggered_by_user_id")
