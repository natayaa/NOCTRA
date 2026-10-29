"""add project_items.occurred_at (model/migration drift)

Revision ID: a7b8c9d0e1f2
Revises:     f0c1d2e3a4b5
Create Date: 2026-10-29 16:10:00

`ProjectItem.occurred_at` has been in the ORM since the costing module but
was never created by a migration — databases provisioned with
`Base.metadata.create_all()` have it, alembic-built databases do not, and
every project detail / item query then fails on a missing column.

The statements are idempotent so the migration is safe on databases that
already carry the column (it only backfills and adds the index).
"""

from __future__ import annotations

from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f0c1d2e3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'project_items'
                  AND column_name = 'occurred_at'
            ) THEN
                ALTER TABLE project_items ADD COLUMN occurred_at timestamptz;
            END IF;
        END $$;
        """
    )
    op.execute(
        "UPDATE project_items SET occurred_at = created_at "
        "WHERE occurred_at IS NULL"
    )
    op.execute(
        "ALTER TABLE project_items "
        "ALTER COLUMN occurred_at SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE project_items "
        "ALTER COLUMN occurred_at SET DEFAULT now()"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_project_items_occurred_at "
        "ON project_items (occurred_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_items_occurred_at")
    op.execute(
        "ALTER TABLE project_items DROP COLUMN IF EXISTS occurred_at"
    )
