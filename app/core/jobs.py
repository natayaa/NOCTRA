"""Minimal in-process background task runner.

For Phase 1 we only need fire-and-forget jobs (emails, audit fan-out,
notifications). When you outgrow this, swap for Arq or Dramatiq with Redis.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import log

Job = Callable[..., Awaitable[None]]


class JobQueue:
    def __init__(self, *, job_timeout: float = 300.0) -> None:
        # 300s covers the worst-case notification job: two sequential sends,
        # each with 1 + SMTP_MAX_RETRIES attempts at SMTP_TIMEOUT_SECONDS
        # (30s) plus exponential backoff (~7s). The previous 60s cap could
        # cancel a send after delivery but before the EmailLog commit,
        # leaving notifications unlogged and unrecoverable.
        self._queue: asyncio.Queue[tuple[Job, tuple, dict[str, Any]]] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._shutdown = asyncio.Event()
        self._job_timeout = job_timeout

    async def start(self) -> None:
        if self._worker is None:
            self._shutdown.clear()  # allow restart after stop()
            self._worker = asyncio.create_task(self._run())

    async def stop(self, *, drain_timeout: float = 5.0) -> None:
        """Signal shutdown, drain remaining jobs up to `drain_timeout`.

        If the worker is stuck on a long job past the deadline, it is
        cancelled — remaining jobs are logged and dropped.
        """
        self._shutdown.set()
        if self._worker is None:
            return
        try:
            await asyncio.wait_for(self._worker, timeout=drain_timeout)
        except asyncio.TimeoutError:
            log.warning(
                "background_worker_drain_timeout",
                pending=self._queue.qsize(),
                drain_timeout=drain_timeout,
            )
            self._worker.cancel()
            try:
                await self._worker
            except (asyncio.CancelledError, Exception):
                pass
        finally:
            self._worker = None

    async def enqueue(self, job: Job, *args: Any, **kwargs: Any) -> None:
        await self._queue.put((job, args, kwargs))

    async def _run(self) -> None:
        while True:
            try:
                job, args, kwargs = await asyncio.wait_for(
                    self._queue.get(), timeout=0.25
                )
            except asyncio.TimeoutError:
                # Only exit once we've been asked to stop AND the queue is
                # empty — otherwise pending jobs would be silently lost.
                if self._shutdown.is_set() and self._queue.empty():
                    return
                continue
            try:
                await asyncio.wait_for(
                    job(*args, **kwargs), timeout=self._job_timeout
                )
            except asyncio.TimeoutError:
                log.warning(
                    "background_job_timeout",
                    job=getattr(job, "__name__", str(job)),
                    timeout=self._job_timeout,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception(
                    "background_job_failed",
                    job=getattr(job, "__name__", str(job)),
                )
            finally:
                self._queue.task_done()


queue = JobQueue()