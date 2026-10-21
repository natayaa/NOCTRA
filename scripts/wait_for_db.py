"""
Wait for Postgres to accept connections.

Usage: python -m scripts.wait_for_db
Exits 0 on success, 1 on timeout.
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg

from app.core.config import settings


async def wait(retries: int = 30, delay: float = 1.0) -> int:
    for attempt in range(1, retries + 1):
        try:
            conn = await asyncpg.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                timeout=5,
            )
            await conn.close()
            print(f"[wait_for_db] connected after {attempt} attempt(s)")
            return 0
        except Exception as exc:
            print(f"[wait_for_db] attempt {attempt}/{retries}: {exc}")
            if attempt < retries:
                await asyncio.sleep(delay)

    print("[wait_for_db] giving up", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(wait()))