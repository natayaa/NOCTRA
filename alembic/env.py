"""
Alembic environment for NOCTRA Autoworks.

Async-aware. Reads the DB URL from app settings so .env is the single
source of truth. Supports both offline (SQL dump) and online modes.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# ────────────────────────────────────────────────────────────
# Model imports — REQUIRED for autogenerate to see every table.
# Any module that defines a Base subclass must be imported here.
# ────────────────────────────────────────────────────────────
from app.modules.auth import models as _auth_models          # noqa: F401
from app.modules.rbac import models as _rbac_models          # noqa: F401
from app.modules.audit import models as _audit_models        # noqa: F401
from app.modules.settings import models as _settings_models  # noqa: F401

import app.core.models_registry  # noqa: F401

# ── Phase 2a — uncomment when the model files exist ─────────
# from app.modules.customers import models as _customer_models  # noqa: F401
# from app.modules.vehicles import models as _vehicle_models    # noqa: F401

# ------------------------------------------------------------
# Alembic config
# ------------------------------------------------------------
config = context.config

# Inject the DB URL from app settings (overrides alembic.ini's empty value).
config.set_main_option("sqlalchemy.url", settings.database_url)

# Python logging config from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def include_object(object_, name, type_, reflected, compare_to) -> bool:
    """
    Skip tables/objects we never want migrated.
    Currently: anything prefixed with `_` (scratch tables).
    """
    if type_ == "table" and name.startswith("_"):
        return False
    return True


def process_revision_directives(context_, revision, directives):
    """
    Prevent empty autogenerate migrations from being written.
    """
    if getattr(config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected.")


def _common_options(connection: Connection | None = None) -> dict:
    opts: dict = {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
        "include_schemas": False,
        "include_object": include_object,
        "process_revision_directives": process_revision_directives,
    }
    if connection is not None:
        opts["connection"] = connection
    return opts


# ------------------------------------------------------------
# Offline — emit SQL without a live connection
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    context.configure(
        url=settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------
# Online — connect and apply
# ------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(**_common_options(connection))
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()