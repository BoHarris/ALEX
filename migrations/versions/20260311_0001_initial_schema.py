"""initial schema

Revision ID: 20260311_0001_initial_schema
Revises:
Create Date: 2026-03-11 00:00:00
"""
from __future__ import annotations

from alembic import op

from database.database import Base
import database.models  # noqa: F401


revision = "20260311_0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
