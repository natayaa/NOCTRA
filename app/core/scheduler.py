"""Minimal in-process daily scheduler.

The app already ships a fire-and-forget job queue for request-scoped
work. The overdue sweep is periodic instead: run once shortly after boot
(catch up after downtime), then every day at a fixed local hour.

One process = one scheduler. Running uvicorn with multiple workers would
run the sweep once per worker; the sweep is idempotent, and reminder
cooldown is enforced in the database via EmailLog, so the worst case is a
few wasted queries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.logging import log

Job = Callable[[object], Awaitable[object]]

_BOOT_DELAY_SECONDS = 5.0


class DailyJob:
    def __init__(
        self,
        job: Job,
        *,
        name: str,
        hour_local: int,
        run_on_start: bool = True,
    ) -> None:
        self._job = job
        self.name = name
        self.hour_local = max(0, min(23, hour_local))
        self.run_on_start = run_on_start
        self._task: asyncio.Task | None = None

    # ── lifecycle ───────────────────────────────────────

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(
                self._loop(), name=f"daily-job:{self.name}"
            )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            self._task = None

    # ── scheduling ──────────────────────────────────────

    def seconds_until_next_run(self, *, now: datetime | None = None) -> float:
        tz = ZoneInfo(settings.APP_TIMEZONE)
        current = now.astimezone(tz) if now else datetime.now(tz)
        target = current.replace(
            hour=self.hour_local, minute=0, second=0, microsecond=0
        )
        if target <= current:
            target += timedelta(days=1)
        return (target - current).total_seconds()

    async def _loop(self) -> None:
        if self.run_on_start:
            # Let startup, migrations, and the pool settle first.
            await asyncio.sleep(_BOOT_DELAY_SECONDS)
            await self.run_once()

        while True:
            delay = self.seconds_until_next_run()
            log.info("daily_job_scheduled", job=self.name, in_seconds=int(delay))
            await asyncio.sleep(delay)
            await self.run_once()

    async def run_once(self) -> None:
        from app.core.database import SessionLocal

        async with SessionLocal() as session:
            try:
                await self._job(session)
                await session.commit()
            except asyncio.CancelledError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                log.exception("daily_job_failed", job=self.name)
