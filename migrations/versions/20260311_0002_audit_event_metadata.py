"""add audit event metadata fields

Revision ID: 20260311_0002_audit_event_metadata
Revises: 20260311_0001_initial_schema
Create Date: 2026-03-11 00:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0002_audit_event_metadata"
down_revision = "20260311_0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("event_category", sa.String(), nullable=True))
    op.add_column("audit_events", sa.Column("event_metadata", sa.Text(), nullable=True))
    op.execute("UPDATE audit_events SET event_category = 'system' WHERE event_category IS NULL")
    op.alter_column("audit_events", "event_category", existing_type=sa.String(), nullable=False)
    op.create_index("ix_audit_events_event_category", "audit_events", ["event_category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_event_category", table_name="audit_events")
    op.drop_column("audit_events", "event_metadata")
    op.drop_column("audit_events", "event_category")
