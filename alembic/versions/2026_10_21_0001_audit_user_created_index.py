"""Add composite index (user_id, created_at) to audit_logs.

Covers: `WHERE user_id = ? ORDER BY created_at DESC` — the shape used by
the audit list filtered by user. The leftmost prefix also serves bare
`WHERE user_id = ?`, replacing the now-redundant single-column index.

Revision ID: a1f2c3d4e5b6
Revises:     317eda3a7f40
Create Date: 2026-10-21 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1f2c3d4e5b6"
# Must chain onto the schema created by phase1–phase6. Leaving this as
# None made this a second root revision: a fresh `upgrade head` applied it
# first and failed on the missing `audit_logs` table.
down_revision = "317eda3a7f40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new composite index BEFORE dropping the old one so that
    # queries against `user_id` never lose an index mid-migration.
    # CONCURRENTLY avoids blocking writes — safe on a live table. Those
    # statements commit immediately, so IF [NOT] EXISTS keeps a retry
    # after a later failure safe.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_audit_logs_user_created "
            "ON audit_logs (user_id, created_at)"
        )

    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_audit_logs_user_id"
        )


def downgrade() -> None:
    # Recreate the single-column index, then drop the composite.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_audit_logs_user_id ON audit_logs (user_id)"
        )

    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_audit_logs_user_created"
        )