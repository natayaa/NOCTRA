"""
Minimal in-process background task runner.

For Phase 1 we only need fire-and-forget jobs (emails, audit fan-out,
notifications). When you outgrow this, swap for Arq or Dramatiq with Redis.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import log

Job = Callable[..., Awaitable[None]]


class JobQueue:
    def __init__(self, *, job_timeout: float = 60.0) -> None:
        self._queue: asyncio.Queue[tuple[Job, tuple, dict[str, Any]]] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._shutdown = asyncio.Event()
        self._job_timeout = job_timeout

    async def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self, *, drain_timeout: float = 5.0) -> None:
        self._shutdown.set()
        if self._worker:
            await self._worker
            self._worker = None
        # Give pending jobs a short grace period, then drop + log.
        deadline = asyncio.get_event_loop().time() + drain_timeout
        while not self._queue.empty() and asyncio.get_event_loop().time() < deadline:
            try:
                job, _, _ = self._queue.get_nowait()
                log.warning(
                    "background_job_dropped",
                    job=getattr(job, "__name__", str(job)),
                )
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def enqueue(self, job: Job, *args: Any, **kwargs: Any) -> None:
        await self._queue.put((job, args, kwargs))

    async def _run(self) -> None:
        while not self._shutdown.is_set():
            try:
                job, args, kwargs = await asyncio.wait_for(
                    self._queue.get(), timeout=0.25
                )
            except TimeoutError:
                continue
            try:
                await asyncio.wait_for(
                    job(*args, **kwargs), timeout=self._job_timeout
                )
            except TimeoutError:
                log.warning(
                    "background_job_timeout",
                    job=getattr(job, "__name__", str(job)),
                    timeout=self._job_timeout,
                )
            except Exception:
                log.exception(
                    "background_job_failed",
                    job=getattr(job, "__name__", str(job)),
                )
            finally:
                self._queue.task_done()


queue = JobQueue()