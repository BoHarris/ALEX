"""extend governance tasks for automated changes workflow

Revision ID: 20260315_0007_automated_changes_workflow
Revises: 20260314_0006_governance_tasks
Create Date: 2026-03-15 09:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0007_automated_changes_workflow"
down_revision = "20260314_0006_governance_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("governance_tasks", sa.Column("assignee_type", sa.String(), nullable=True))
    op.add_column("governance_tasks", sa.Column("assignee_label", sa.String(), nullable=True))
    op.create_index("ix_governance_tasks_assignee_type", "governance_tasks", ["assignee_type"], unique=False)

    op.add_column("governance_task_activities", sa.Column("actor_type", sa.String(), nullable=True))
    op.add_column("governance_task_activities", sa.Column("actor_label", sa.String(), nullable=True))
    op.create_index("ix_governance_task_activities_actor_type", "governance_task_activities", ["actor_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_governance_task_activities_actor_type", table_name="governance_task_activities")
    op.drop_column("governance_task_activities", "actor_label")
    op.drop_column("governance_task_activities", "actor_type")

    op.drop_index("ix_governance_tasks_assignee_type", table_name="governance_tasks")
    op.drop_column("governance_tasks", "assignee_label")
    op.drop_column("governance_tasks", "assignee_type")
