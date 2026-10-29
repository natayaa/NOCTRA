"""Add indexes used by the audit list and inquiry follow-up counters.

- `audit_logs.created_at` backs the unfiltered `ORDER BY created_at DESC`
  listing and the dashboard activity feed. The model declared it since
  the beginning but no migration ever created it.
- `inquiries.follow_up_date` backs the overdue-follow-up count that runs
  on every inquiry list request.

Both are created CONCURRENTLY so deploying on a live database does not
block writes. `IF NOT EXISTS` keeps the migration safe when a database
was bootstrapped with `create_all` (tests) instead of migrations.

Revision ID: c3d4e5f6a7b8
Revises:     b2c3d4e5f6a7
Create Date: 2026-10-30 12:00:00
"""

from __future__ import annotations

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_audit_logs_created_at ON audit_logs (created_at)"
        )
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_inquiries_follow_up_date ON inquiries (follow_up_date)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_inquiries_follow_up_date"
        )
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_audit_logs_created_at"
        )
