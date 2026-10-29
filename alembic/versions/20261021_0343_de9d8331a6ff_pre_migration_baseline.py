"""pre-migration baseline

Revision ID: de9d8331a6ff
Revises: b2e3d4f5a6c7
Create Date: 2026-10-21 03:43:48.769119+00:00

Originally a mergepoint of 317eda3a7f40 and b2e3d4f5a6c7. Once
a1f2c3d4e5b6 was chained onto 317eda3a7f40 (it used to be a second root),
b2e3d4f5a6c7 already descends from 317eda3a7f40, so a linear revision keeps
the graph with a single head without a redundant merge parent.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'de9d8331a6ff'
down_revision: str | None = 'b2e3d4f5a6c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass