"""add test result tracking fields

Revision ID: 20260311_0003_test_result_tracking
Revises: 20260311_0002_audit_event_metadata
Create Date: 2026-03-11 01:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0003_test_result_tracking"
down_revision = "20260311_0002_audit_event_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    run_columns = {column["name"] for column in inspector.get_columns("compliance_test_runs")}
    run_indexes = {index["name"] for index in inspector.get_indexes("compliance_test_runs")}

    if "dataset_name" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("dataset_name", sa.String(), nullable=True))
    if "total_tests" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("total_tests", sa.Integer(), nullable=True))
    if "passed_tests" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("passed_tests", sa.Integer(), nullable=True))
    if "failed_tests" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("failed_tests", sa.Integer(), nullable=True))
    if "skipped_tests" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("skipped_tests", sa.Integer(), nullable=True))
    if "accuracy_score" not in run_columns:
        op.add_column("compliance_test_runs", sa.Column("accuracy_score", sa.Numeric(6, 4), nullable=True))
    op.execute("UPDATE compliance_test_runs SET total_tests = 0 WHERE total_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET passed_tests = 0 WHERE passed_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET failed_tests = 0 WHERE failed_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET skipped_tests = 0 WHERE skipped_tests IS NULL")
    with op.batch_alter_table("compliance_test_runs") as batch_op:
        batch_op.alter_column("total_tests", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("passed_tests", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("failed_tests", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("skipped_tests", existing_type=sa.Integer(), nullable=False)
    if "ix_compliance_test_runs_dataset_name" not in run_indexes:
        op.create_index("ix_compliance_test_runs_dataset_name", "compliance_test_runs", ["dataset_name"], unique=False)

    case_columns = {column["name"] for column in inspector.get_columns("compliance_test_case_results")}
    case_indexes = {index["name"] for index in inspector.get_indexes("compliance_test_case_results")}

    if "dataset_name" not in case_columns:
        op.add_column("compliance_test_case_results", sa.Column("dataset_name", sa.String(), nullable=True))
    if "expected_result" not in case_columns:
        op.add_column("compliance_test_case_results", sa.Column("expected_result", sa.String(), nullable=True))
    if "actual_result" not in case_columns:
        op.add_column("compliance_test_case_results", sa.Column("actual_result", sa.String(), nullable=True))
    if "confidence_score" not in case_columns:
        op.add_column("compliance_test_case_results", sa.Column("confidence_score", sa.Numeric(6, 4), nullable=True))
    if "ix_compliance_test_case_results_dataset_name" not in case_indexes:
        op.create_index("ix_compliance_test_case_results_dataset_name", "compliance_test_case_results", ["dataset_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_compliance_test_case_results_dataset_name", table_name="compliance_test_case_results")
    op.drop_column("compliance_test_case_results", "confidence_score")
    op.drop_column("compliance_test_case_results", "actual_result")
    op.drop_column("compliance_test_case_results", "expected_result")
    op.drop_column("compliance_test_case_results", "dataset_name")

    op.drop_index("ix_compliance_test_runs_dataset_name", table_name="compliance_test_runs")
    op.drop_column("compliance_test_runs", "accuracy_score")
    op.drop_column("compliance_test_runs", "skipped_tests")
    op.drop_column("compliance_test_runs", "failed_tests")
    op.drop_column("compliance_test_runs", "passed_tests")
    op.drop_column("compliance_test_runs", "total_tests")
    op.drop_column("compliance_test_runs", "dataset_name")
