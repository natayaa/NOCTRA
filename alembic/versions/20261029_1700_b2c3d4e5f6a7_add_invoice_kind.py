"""add invoices.kind (DP / FINAL / OTHER)

Revision ID: b2c3d4e5f6a7
Revises:     a7b8c9d0e1f2
Create Date: 2026-10-29 17:00:00

A project may now be billed in stages: a DP invoice up front and one or
more final bills for the remainder. `kind` records what each invoice is.
Existing project invoices were full-project bills, so they are backfilled
as FINAL; everything else stays OTHER.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "kind",
            sa.String(length=10),
            nullable=False,
            server_default="OTHER",
        ),
    )
    op.execute(
        "UPDATE invoices SET kind = 'FINAL' WHERE project_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("invoices", "kind")
