"""pre-migration baseline

Revision ID: de9d8331a6ff
Revises: 317eda3a7f40, b2e3d4f5a6c7
Create Date: 2026-10-21 03:43:48.769119+00:00
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'de9d8331a6ff'
down_revision: str | None = ('317eda3a7f40', 'b2e3d4f5a6c7')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass