"""add inventory occurred_at, payment reversal integrity, missing indexes

Revision ID: f0c1d2e3a4b5
Revises:     de9d8331a6ff
Create Date: 2026-10-29 15:00:00

The model layer had drifted ahead of the migrations:

- `inventory_transactions.occurred_at` existed only in the ORM. Every
  inventory query selected a column the database did not have, so the
  inventory screens and stock ledger failed against a migrated database.
- `payments.reversal_of_id` lacked the unique constraint and self-FK the
  model declares, allowing two reversals of the same payment.
- Several indexes declared by the models were never created.

Existing rows are backfilled from `created_at`; legacy data is preserved.
"""

from __future__ import annotations

from alembic import op

revision = "f0c1d2e3a4b5"
down_revision = "de9d8331a6ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Everything here is written idempotently: databases bootstrapped with
    # `Base.metadata.create_all()` already carry some of these objects,
    # while genuinely migration-built databases do not. Either way the
    # revision must succeed and converge on the same schema.
    #
    # ── inventory_transactions.occurred_at ────────────────────────
    op.execute(
        "ALTER TABLE inventory_transactions "
        "ADD COLUMN IF NOT EXISTS occurred_at timestamptz"
    )
    op.execute(
        "UPDATE inventory_transactions "
        "SET occurred_at = created_at "
        "WHERE occurred_at IS NULL"
    )
    op.execute(
        "ALTER TABLE inventory_transactions "
        "ALTER COLUMN occurred_at SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE inventory_transactions "
        "ALTER COLUMN occurred_at SET DEFAULT now()"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS "
        "ix_inventory_transactions_occurred_at "
        "ON inventory_transactions (occurred_at)"
    )

    # ── payments.reversal_of_id integrity ─────────────────────────
    # The column itself was ORM-only until now — a migration-built
    # database has no `reversal_of_id`, so it must be created before the
    # constraint that references it.
    # A payment may be reversed at most once, and a reversal must point
    # at a real payment. Multiple NULLs remain allowed.
    op.execute(
        "ALTER TABLE payments "
        "ADD COLUMN IF NOT EXISTS reversal_of_id uuid"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_payments_reversal_of_id'
                  AND conrelid = 'payments'::regclass
            ) THEN
                ALTER TABLE payments
                    ADD CONSTRAINT uq_payments_reversal_of_id
                    UNIQUE (reversal_of_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_payments_reversal_of_id_payments'
                  AND conrelid = 'payments'::regclass
            ) THEN
                ALTER TABLE payments
                    ADD CONSTRAINT fk_payments_reversal_of_id_payments
                    FOREIGN KEY (reversal_of_id)
                    REFERENCES payments (id)
                    ON DELETE RESTRICT;
            END IF;
        END $$;
        """
    )

    # ── Indexes the models declare but the schema lacked ──────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_materials_active_category "
        "ON materials (is_active, category)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_suppliers_active_name "
        "ON suppliers (is_active, name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_vehicles_brand "
        "ON vehicles (brand_id)"
    )

    # Superseded by ix_audit_logs_action_created (leftmost prefix).
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action")


def downgrade() -> None:
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.drop_index("ix_vehicles_brand", table_name="vehicles")
    op.drop_index("ix_suppliers_active_name", table_name="suppliers")
    op.drop_index("ix_materials_active_category", table_name="materials")
    op.drop_constraint(
        "fk_payments_reversal_of_id_payments",
        "payments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_payments_reversal_of_id", "payments", type_="unique"
    )
    op.drop_index(
        "ix_inventory_transactions_occurred_at",
        table_name="inventory_transactions",
    )
    op.drop_column("inventory_transactions", "occurred_at")
