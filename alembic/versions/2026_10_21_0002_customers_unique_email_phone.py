"""Add partial unique indexes on customers.email / phone; drop redundant.

- `uq_customers_email_lower` — case-insensitive uniqueness on email.
  Enforced at DB level so concurrent inserts (from `create` or the public
  `find_or_create` intake) cannot both pass the application-level
  pre-check and create duplicate customers.
- `uq_customers_phone` — unique for non-null phones. Multiple customers
  without a phone are still allowed (partial index).
- Drop `ix_customers_email` — replaced by `uq_customers_email_lower`.
- Drop `ix_customers_phone` — replaced by `uq_customers_phone`.
- Drop `ix_customers_status` — covered by `ix_customers_status_created`
  (leftmost prefix on `status`).

Revision ID: b2e3d4f5a6c7
Revises:     a1f2c3d4e5b6
Create Date: 2026-10-21 00:02:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2e3d4f5a6c7"
down_revision = "a1f2c3d4e5b6"
branch_labels = None
depends_on = None


# Rows returned by the safety check; shown to the operator on failure.
_DUP_EMAIL_SQL = sa.text("""
    SELECT lower(email) AS email, COUNT(*) AS n,
           string_agg(code, ', ' ORDER BY code) AS codes
    FROM customers
    WHERE email IS NOT NULL
    GROUP BY lower(email)
    HAVING COUNT(*) > 1
    ORDER BY n DESC
    LIMIT 20
""")

_DUP_PHONE_SQL = sa.text("""
    SELECT phone, COUNT(*) AS n,
           string_agg(code, ', ' ORDER BY code) AS codes
    FROM customers
    WHERE phone IS NOT NULL
    GROUP BY phone
    HAVING COUNT(*) > 1
    ORDER BY n DESC
    LIMIT 20
""")

# Whitespace in emails would bypass the unique constraint on
# `lower(email)` while still matching `find_by_email()` after stripping.
_WS_EMAIL_SQL = sa.text("""
    SELECT code, email
    FROM customers
    WHERE email IS NOT NULL AND email != btrim(email)
    LIMIT 20
""")


def _assert_no_blockers() -> None:
    """Fail loudly (before touching data) if the unique indexes cannot
    be created. Runs inside the Alembic migration transaction; on raise,
    nothing is changed.
    """
    conn = op.get_bind()

    dups = conn.execute(_DUP_EMAIL_SQL).fetchall()
    if dups:
        details = "\n".join(
            f"  • {row.email!r}  → {row.n} rows: {row.codes}"
            for row in dups
        )
        raise RuntimeError(
            "Cannot create uq_customers_email_lower — duplicate emails exist.\n"
            "Merge or rename the following customers, then re-run:\n"
            f"{details}"
        )

    dups = conn.execute(_DUP_PHONE_SQL).fetchall()
    if dups:
        details = "\n".join(
            f"  • {row.phone!r}  → {row.n} rows: {row.codes}"
            for row in dups
        )
        raise RuntimeError(
            "Cannot create uq_customers_phone — duplicate phones exist.\n"
            "Merge or rename the following customers, then re-run:\n"
            f"{details}"
        )

    ws = conn.execute(_WS_EMAIL_SQL).fetchall()
    if ws:
        details = "\n".join(
            f"  • {row.code}: {row.email!r}" for row in ws
        )
        raise RuntimeError(
            "Cannot create uq_customers_email_lower — emails with leading/"
            "trailing whitespace would bypass the unique constraint.\n"
            "Trim the following rows first (UPDATE customers SET email = "
            "btrim(email) WHERE ...):\n"
            f"{details}"
        )


def upgrade() -> None:
    # ── 1. Safety gate — no schema change yet ─────────────────────
    _assert_no_blockers()

    # ── 2. Create new unique indexes (before dropping old ones) ───
    # `postgresql_where` gives a partial index — multiple NULL emails
    # or phones must remain allowed.
    with op.get_context().autocommit_block():
        op.execute(sa.text("""
            CREATE UNIQUE INDEX CONCURRENTLY uq_customers_email_lower
            ON customers (lower(email))
            WHERE email IS NOT NULL
        """))

    with op.get_context().autocommit_block():
        op.execute(sa.text("""
            CREATE UNIQUE INDEX CONCURRENTLY uq_customers_phone
            ON customers (phone)
            WHERE phone IS NOT NULL
        """))

    # ── 3. Drop redundant single-column indexes ───────────────────
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_customers_email",
            table_name="customers",
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_customers_phone",
            table_name="customers",
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_customers_status",
            table_name="customers",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    # ── Recreate the redundant indexes ────────────────────────────
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_customers_status",
            "customers",
            ["status"],
            unique=False,
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.create_index(
            "ix_customers_phone",
            "customers",
            ["phone"],
            unique=False,
            postgresql_concurrently=True,
        )

    with op.get_context().autocommit_block():
        op.create_index(
            "ix_customers_email",
            "customers",
            ["email"],
            unique=False,
            postgresql_concurrently=True,
        )

    # ── Drop the unique indexes ───────────────────────────────────
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "DROP INDEX CONCURRENTLY IF EXISTS uq_customers_phone"
        ))

    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "DROP INDEX CONCURRENTLY IF EXISTS uq_customers_email_lower"
        ))