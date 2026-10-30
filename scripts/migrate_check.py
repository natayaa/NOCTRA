"""Validate the migration chain on a throwaway schema.

Runs the *entire* Alembic chain from an empty schema in the test
database, then runs `alembic check` against the ORM metadata. This
proves two things a normal `alembic check` cannot:

- a fresh installation can still reach `head` (history is not broken);
- migrated tables match the models (no drift hidden by a database that
  was originally built with `create_all`).

Usage:
    python -m scripts.migrate_check
    python -m scripts.migrate_check --keep   # inspect the schema afterwards

The scratch schema is dropped on exit. The script refuses to run against
a database whose name does not end in `_test` unless --database is given
explicitly.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback
import uuid
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config
from asyncpg import exceptions as pg_exc

ROOT = Path(__file__).resolve().parents[1]


async def _connect(database: str) -> asyncpg.Connection:
    from app.core.config import settings

    return await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=database,
        timeout=10,
    )


async def _create_schema(database: str, schema: str) -> None:
    conn = await _connect(database)
    try:
        await conn.execute(f'CREATE SCHEMA "{schema}"')
    finally:
        await conn.close()


async def _drop_schema(database: str, schema: str) -> None:
    conn = await _connect(database)
    try:
        await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    finally:
        await conn.close()


def _alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    # Absolute paths so the script works from any CWD.
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        help="Database to create the scratch schema in "
             "(default: <POSTGRES_DB>_test)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the scratch schema after the check (for debugging).",
    )
    args = parser.parse_args(argv)

    from app.core.config import settings

    configured = settings.POSTGRES_DB
    test_db = args.database or (
        configured if configured.endswith("_test") else f"{configured}_test"
    )
    if not test_db.endswith("_test") and args.database is None:
        print("refusing to run against a non-test database", file=sys.stderr)
        return 2

    schema = f"noctra_mig_check_{uuid.uuid4().hex[:8]}"
    database_url = settings.database_url.rsplit("/", 1)[0] + f"/{test_db}"

    async def prepare() -> None:
        conn = await _connect(test_db)
        await conn.close()
        await _create_schema(test_db, schema)

    try:
        asyncio.run(prepare())
    except pg_exc.InvalidCatalogNameError:
        print(
            f"test database '{test_db}' does not exist — run `make test-db` "
            "or pass --database",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(f"cannot create scratch schema: {exc}", file=sys.stderr)
        return 2

    # env.py reads these before building the engine.
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    os.environ["ALEMBIC_SCHEMA"] = schema

    failed = False
    cfg = _alembic_config()
    try:
        print(f"[migrate-check] upgrading schema {schema} on {test_db} …")
        command.upgrade(cfg, "head")
        print("[migrate-check] checking for drift …")
        command.check(cfg)
        print("[migrate-check] OK — chain reaches head and matches the models")
    except Exception as exc:  # Alembic logs the details itself
        failed = True
        print(f"[migrate-check] FAILED: {type(exc).__name__}", file=sys.stderr)
        traceback.print_exc()
    finally:
        if args.keep:
            print(f"[migrate-check] kept schema {schema}")
        else:
            try:
                asyncio.run(_drop_schema(test_db, schema))
                print(f"[migrate-check] dropped schema {schema}")
            except Exception as exc:
                print(
                    f"[migrate-check] could not drop schema {schema}: {exc}",
                    file=sys.stderr,
                )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
