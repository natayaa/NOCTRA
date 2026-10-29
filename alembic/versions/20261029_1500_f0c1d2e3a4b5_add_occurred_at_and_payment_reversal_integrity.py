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

import sqlalchemy as sa
from alembic import op

revision = "f0c1d2e3a4b5"
down_revision = "de9d8331a6ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── inventory_transactions.occurred_at ────────────────────────
    op.add_column(
        "inventory_transactions",
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE inventory_transactions "
        "SET occurred_at = created_at "
        "WHERE occurred_at IS NULL"
    )
    op.alter_column(
        "inventory_transactions",
        "occurred_at",
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.create_index(
        "ix_inventory_transactions_occurred_at",
        "inventory_transactions",
        ["occurred_at"],
        unique=False,
    )

    # ── payments.reversal_of_id integrity ─────────────────────────
    # A payment may be reversed at most once, and a reversal must point
    # at a real payment. Verified: no duplicate/orphan values exist.
    op.create_unique_constraint(
        "uq_payments_reversal_of_id",
        "payments",
        ["reversal_of_id"],
    )
    op.create_foreign_key(
        "fk_payments_reversal_of_id_payments",
        "payments",
        "payments",
        ["reversal_of_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ── Indexes the models declare but the schema lacked ──────────
    op.create_index(
        "ix_materials_active_category",
        "materials",
        ["is_active", "category"],
        unique=False,
    )
    op.create_index(
        "ix_suppliers_active_name",
        "suppliers",
        ["is_active", "name"],
        unique=False,
    )
    op.create_index(
        "ix_vehicles_brand",
        "vehicles",
        ["brand_id"],
        unique=False,
    )

    # Superseded by ix_audit_logs_action_created (leftmost prefix).
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")


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
