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
    op.add_column("compliance_test_runs", sa.Column("dataset_name", sa.String(), nullable=True))
    op.add_column("compliance_test_runs", sa.Column("total_tests", sa.Integer(), nullable=True))
    op.add_column("compliance_test_runs", sa.Column("passed_tests", sa.Integer(), nullable=True))
    op.add_column("compliance_test_runs", sa.Column("failed_tests", sa.Integer(), nullable=True))
    op.add_column("compliance_test_runs", sa.Column("skipped_tests", sa.Integer(), nullable=True))
    op.add_column("compliance_test_runs", sa.Column("accuracy_score", sa.Numeric(6, 4), nullable=True))
    op.execute("UPDATE compliance_test_runs SET total_tests = 0 WHERE total_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET passed_tests = 0 WHERE passed_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET failed_tests = 0 WHERE failed_tests IS NULL")
    op.execute("UPDATE compliance_test_runs SET skipped_tests = 0 WHERE skipped_tests IS NULL")
    op.alter_column("compliance_test_runs", "total_tests", existing_type=sa.Integer(), nullable=False)
    op.alter_column("compliance_test_runs", "passed_tests", existing_type=sa.Integer(), nullable=False)
    op.alter_column("compliance_test_runs", "failed_tests", existing_type=sa.Integer(), nullable=False)
    op.alter_column("compliance_test_runs", "skipped_tests", existing_type=sa.Integer(), nullable=False)
    op.create_index("ix_compliance_test_runs_dataset_name", "compliance_test_runs", ["dataset_name"], unique=False)

    op.add_column("compliance_test_case_results", sa.Column("dataset_name", sa.String(), nullable=True))
    op.add_column("compliance_test_case_results", sa.Column("expected_result", sa.String(), nullable=True))
    op.add_column("compliance_test_case_results", sa.Column("actual_result", sa.String(), nullable=True))
    op.add_column("compliance_test_case_results", sa.Column("confidence_score", sa.Numeric(6, 4), nullable=True))
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
