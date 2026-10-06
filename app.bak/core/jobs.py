"""
Minimal in-process background task runner.

For Phase 1 we only need fire-and-forget jobs (emails, audit fan-out,
notifications). When you outgrow this, swap for Arq or Dramatiq with Redis.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from core.logging import log

Job = Callable[..., Awaitable[None]]


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[Job, tuple, dict[str, Any]]] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._worker:
            await self._worker
            self._worker = None

    async def enqueue(self, job: Job, *args: Any, **kwargs: Any) -> None:
        await self._queue.put((job, args, kwargs))

    async def _run(self) -> None:
        while not self._shutdown.is_set():
            try:
                job, args, kwargs = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except TimeoutError:
                continue
            try:
                await job(*args, **kwargs)
            except Exception:
                log.exception("background_job_failed", job=getattr(job, "__name__", str(job)))
            finally:
                self._queue.task_done()


queue = JobQueue()