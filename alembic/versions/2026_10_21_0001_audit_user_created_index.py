"""Add composite index (user_id, created_at) to audit_logs.

Covers: `WHERE user_id = ? ORDER BY created_at DESC` — the shape used by
the audit list filtered by user. The leftmost prefix also serves bare
`WHERE user_id = ?`, replacing the now-redundant single-column index.

Revision ID: a1f2c3d4e5b6
Revises:     <previous_revision>
Create Date: 2026-10-21 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1f2c3d4e5b6"
down_revision = None  # ← replace with your latest revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new composite index BEFORE dropping the old one so that
    # queries against `user_id` never lose an index mid-migration.
    # CONCURRENTLY avoids blocking writes — safe on a live table.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_audit_logs_user_created",
            "audit_logs",
            ["user_id", "created_at"],
            unique=False,
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_audit_logs_user_id",
            table_name="audit_logs",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    # Recreate the single-column index, then drop the composite.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_audit_logs_user_id",
            "audit_logs",
            ["user_id"],
            unique=False,
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_audit_logs_user_created",
            table_name="audit_logs",
            postgresql_concurrently=True,
        )