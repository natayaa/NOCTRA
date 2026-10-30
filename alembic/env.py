"""
Alembic environment for NOCTRA Autoworks.

The database URL is derived from the application settings (`.env` is the
single source of truth), so no credentials are stored in `alembic.ini`.

Two optional environment overrides exist for automation:

    ALEMBIC_DATABASE_URL   Full SQLAlchemy URL. Defaults to the URL built
                           from `.env` — handy for one-off checks against a
                           staging database without editing `.env`.
    ALEMBIC_SCHEMA         Apply/compare migrations in an isolated schema.
                           Used by `make migrate-check` to validate the
                           whole chain on a throwaway schema instead of
                           touching real tables.

Offline mode (`alembic upgrade head --sql`) uses the synchronous URL and
emits SQL with literal binds, so a DBA can review it before execution.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Register every model. `models_registry` is the single import point used by
# the app, tests, and Alembic — a new model only needs to be added there.
import app.core.models_registry  # noqa: F401

config = context.config

# `ALEMBIC_DATABASE_URL` wins over the configuration derived from `.env`.
_database_url = os.getenv("ALEMBIC_DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", _database_url)

# Optional isolated schema (e.g. `noctra_mig_check`). Empty/unset = default.
_schema = (os.getenv("ALEMBIC_SCHEMA") or "").strip() or None
_connect_args: dict = {}
if _schema:
    _connect_args = {"server_settings": {"search_path": f"{_schema},public"}}

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    """Exclude scratch tables (`_` prefix) from autogenerate and checks.

    `alembic_version` is filtered explicitly because Alembic only skips it
    automatically when it lives in the default schema; with
    `ALEMBIC_SCHEMA` it otherwise shows up as a removed table.
    """
    if type_ == "table":
        if name == "alembic_version" or name.startswith("_"):
            return False
    return True


def process_revision_directives(context_, revision, directives):
    """Never write an empty autogenerate revision."""
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
    if _schema:
        # Keep `alembic_version` beside the migrated tables when running in
        # an isolated schema.
        opts["version_table_schema"] = _schema
    if connection is not None:
        opts["connection"] = connection
    return opts


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
        version_table_schema=_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


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
        connect_args=_connect_args,
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
