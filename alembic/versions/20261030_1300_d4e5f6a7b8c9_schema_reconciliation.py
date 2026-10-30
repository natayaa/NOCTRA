"""Schema reconciliation — align databases with the ORM metadata.

Revision ID: d4e5f6a7b8c9
Revises:     c3d4e5f6a7b8
Create Date: 2026-10-30 13:00:00

Databases in this project were provisioned two ways: by running the
migration chain, and by `Base.metadata.create_all()` (tests, early
deployments). The two drifted apart in both directions. This revision
is the convergence point; every statement is idempotent so it is safe
on either kind of database and on retries.

What it does
------------

1. **Unique constraints instead of unnamed unique indexes.** Code
   columns were declared `unique=True` in the ORM but created as
   `ix_<table>_code` unique *indexes* by early migrations. A unique
   constraint is the canonical form; `USING INDEX` adopts the existing
   index without rebuilding it. A plain constraint is added when no
   index exists (older `create_all` databases).
2. **Missing data guards.** `projects.code` and the vehicle
   `(customer_id, plate_number)` pair were never protected at the DB
   level. The migration refuses to run, with a readable report, if
   duplicate rows would block the constraint.
3. **Drop indexes superseded by composites or removed from the ORM.**
   e.g. `ix_invoices_status` (covered by `ix_invoices_status_issue`) or
   the leftover `ix_customers_email_lower`.
4. **Create indexes the ORM declares but the chain never created**,
   such as the RBAC lookup indexes and `ix_inquiries_status`.
5. **Restore server defaults.** The ORM declares `server_default` for
   status/boolean/counter columns; older databases were created without
   them, which made raw SQL inserts and rollback paths behave
   differently from the application.
6. **Add `users.password_changed_at`**, which existed only in the ORM
   (force-logout support). Without it, a migration-built database
   cannot authenticate users.

Downgrade reverses the structural changes. The unique
constraint/index conversion is semantically neutral, so downgrade
recreates the historical unique indexes.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _has_constraint(table: str, name: str) -> bool:
    return bool(
        op.get_bind().execute(
            sa.text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = :name AND conrelid = to_regclass(:tbl)"
            ),
            {"name": name, "tbl": table},
        ).first()
    )


def _ensure_unique(
    table: str, constraint: str, columns: list[str], index: str | None
) -> None:
    """Add `constraint` if missing, adopting `index` when it exists."""
    cols = ", ".join(columns)
    if index is None:
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint} "
            f"UNIQUE ({cols})"
        )
        return

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{constraint}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                IF EXISTS (
                    SELECT 1
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_index i ON i.indexrelid = c.oid
                    WHERE c.relname = '{index}'
                      AND n.nspname = current_schema()
                      AND i.indrelid = '{table}'::regclass
                      AND i.indisunique
                ) THEN
                    ALTER TABLE {table}
                        ADD CONSTRAINT {constraint}
                        UNIQUE USING INDEX {index};
                ELSE
                    ALTER TABLE {table}
                        ADD CONSTRAINT {constraint}
                        UNIQUE ({cols});
                END IF;
            END IF;
        END $$;
        """
    )


def _assert_unique_data(
    table: str,
    columns: list[str],
    label: str,
    where: str | None = None,
) -> None:
    """Fail with a readable report if a unique constraint cannot be added."""
    cols = ", ".join(columns)
    where_sql = f"WHERE {where} " if where else ""
    rows = op.get_bind().execute(
        sa.text(
            f"SELECT {cols}, COUNT(*) AS n FROM {table} "
            f"{where_sql}"
            f"GROUP BY {cols} HAVING COUNT(*) > 1 "
            f"ORDER BY n DESC LIMIT 20"
        )
    ).fetchall()
    if not rows:
        return

    details = "\n".join("  • " + " / ".join(str(v) for v in row) for row in rows)
    raise RuntimeError(
        f"Cannot add unique constraint {label} — duplicates exist.\n"
        "Merge or renumber the following rows, then re-run the migration:\n"
        f"{details}"
    )


# ────────────────────────────────────────────────────────────────
# Upgrade
# ────────────────────────────────────────────────────────────────

# Tables whose early unique indexes become named unique constraints.
_UNIQUE_CODES = [
    "accounts",
    "customers",
    "employees",
    "expenses",
    "invoices",
    "materials",
    "payments",
    "projects",
    "purchase_orders",
    "suppliers",
]

# Indexes superseded by a composite index or no longer declared by the ORM.
_OBSOLETE_INDEXES = [
    ("accounts", "ix_accounts_account_type"),
    ("app_settings", "ix_app_settings_category"),
    ("customers", "ix_customers_email_lower"),
    ("email_logs", "ix_email_logs_status"),
    ("expenses", "ix_expenses_category"),
    ("inventory_transactions", "ix_inventory_transactions_transaction_type"),
    ("invoices", "ix_invoices_status"),
    ("payments", "ix_payments_direction"),
    ("payments", "ix_payments_reversal_of_id"),
    ("vehicle_models", "ix_vehicle_models_brand_id"),
    ("vehicles", "ix_vehicles_customer_id"),
]

# Model-declared indexes absent from the migration chain.
_REQUIRED_INDEXES = [
    ("inquiries", "ix_inquiries_status", "status"),
    ("roles", "ix_roles_is_system", "is_system"),
    ("role_permissions", "ix_role_permissions_permission", "permission_id"),
    ("user_roles", "ix_user_roles_role", "role_id"),
    ("vehicles", "ix_vehicles_model", "model_id"),
]

# Columns whose ORM `server_default` never reached older databases.
_SERVER_DEFAULTS = [
    ("app_settings", "category", "'general'"),
    ("app_settings", "is_secret", "false"),
    ("customers", "country", "'Indonesia'"),
    ("customers", "status", "'LEAD'"),
    ("customers", "is_active", "true"),
    ("email_logs", "status", "'PENDING'"),
    ("employees", "is_active", "true"),
    ("inquiries", "status", "'NEW'"),
    ("inquiries", "source", "'ADMIN'"),
    ("invoices", "status", "'DRAFT'"),
    ("materials", "is_active", "true"),
    ("project_items", "status", "'PLANNED'"),
    ("projects", "status", "'DRAFT'"),
    ("projects", "priority", "0"),
    ("purchase_orders", "status", "'DRAFT'"),
    ("roles", "is_system", "false"),
    ("suppliers", "is_active", "true"),
    ("users", "is_active", "true"),
    ("users", "is_superuser", "false"),
    ("users", "failed_login_attempts", "0"),
]


def upgrade() -> None:
    # ── 1. Data guards before adding unique constraints ───────────
    # Only necessary where the constraint does not already exist.
    if not _has_constraint("projects", "uq_projects_code"):
        _assert_unique_data("projects", ["code"], "uq_projects_code")
    if not _has_constraint("vehicles", "uq_vehicles_customer_plate"):
        # Multiple vehicles without a plate are allowed (NULL != NULL).
        _assert_unique_data(
            "vehicles",
            ["customer_id", "plate_number"],
            "uq_vehicles_customer_plate",
            where="plate_number IS NOT NULL",
        )

    # ── 2. Unique constraints ─────────────────────────────────────
    for table in _UNIQUE_CODES:
        _ensure_unique(
            table,
            f"uq_{table}_code",
            ["code"],
            index=f"ix_{table}_code",
        )

    # Composite unique on vehicles (model declares it; no index exists).
    if not _has_constraint("vehicles", "uq_vehicles_customer_plate"):
        op.execute(
            "ALTER TABLE vehicles ADD CONSTRAINT uq_vehicles_customer_plate "
            "UNIQUE (customer_id, plate_number)"
        )

    # ── 3. Drop superseded / stale indexes ────────────────────────
    for table, index in _OBSOLETE_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index}")

    # ── 4. Create missing model indexes ───────────────────────────
    for table, index, column in _REQUIRED_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index} ON {table} ({column})"
        )

    # ── 5. Missing column ─────────────────────────────────────────
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS password_changed_at timestamptz"
    )

    # ── 6. Server defaults ────────────────────────────────────────
    for table, column, default in _SERVER_DEFAULTS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"SET DEFAULT {default}"
        )

    # Keep autovacuum/statistics unaffected by the DDL above.
    for table in {t for t, _ in _OBSOLETE_INDEXES}:
        op.execute(f"ANALYZE {table}")


# ────────────────────────────────────────────────────────────────
# Downgrade
# ────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # ── Server defaults ───────────────────────────────────────────
    for table, column, _default in _SERVER_DEFAULTS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"
        )

    # ── Column and indexes added by upgrade ───────────────────────
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_changed_at")
    # `ix_inquiries_status` already existed in migration-built databases;
    # keep it so a downgrade returns to the chain's schema.
    for _table, index, _column in _REQUIRED_INDEXES:
        if index != "ix_inquiries_status":
            op.execute(f"DROP INDEX IF EXISTS {index}")

    # ── Composite unique ──────────────────────────────────────────
    op.execute(
        "ALTER TABLE vehicles "
        "DROP CONSTRAINT IF EXISTS uq_vehicles_customer_plate"
    )

    # ── Unique constraints → historical unique indexes ────────────
    for table in _UNIQUE_CODES:
        op.execute(
            f"ALTER TABLE {table} "
            f"DROP CONSTRAINT IF EXISTS uq_{table}_code"
        )
        op.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table}_code "
            f"ON {table} (code)"
        )

    # ── Recreate indexes that existed before this revision ────────
    _HISTORICAL = {
        "ix_accounts_account_type": "accounts (account_type)",
        "ix_app_settings_category": "app_settings (category)",
        "ix_email_logs_status": "email_logs (status)",
        "ix_expenses_category": "expenses (category)",
        "ix_inventory_transactions_transaction_type":
            "inventory_transactions (transaction_type)",
        "ix_invoices_status": "invoices (status)",
        "ix_payments_direction": "payments (direction)",
        "ix_vehicle_models_brand_id": "vehicle_models (brand_id)",
        "ix_vehicles_customer_id": "vehicles (customer_id)",
    }
    for index, target in _HISTORICAL.items():
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index} ON {target}"
        )
