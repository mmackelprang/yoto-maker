"""A tiny background-job runner so slow steps (download, upload) can show progress.

Each job runs on a thread and reports ``stage / percent / message`` that the UI
polls. Deliberately minimal — no queue, no persistence; a local app only ever
has a couple of jobs in flight.
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("yoto_maker.jobs")


@dataclass
class Job:
    id: str
    status: str = "running"  # running | done | error
    stage: str = "start"
    percent: int = 0
    message: str = "Starting…"
    result: Any = None
    error: str | None = None

    def view(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "percent": self.percent,
            "message": self.message,
            "result": self.result if self.status == "done" else None,
            "error": self.error,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, target: Callable[[Callable[..., None]], Any]) -> str:
        """Run ``target(update)`` on a thread. ``update(stage, percent, message)``.

        The target's return value becomes ``job.result``. Exceptions are captured
        as ``job.error`` (the exception's message — kept user-friendly by callers).
        """
        job = Job(id=uuid.uuid4().hex[:12])
        with self._lock:
            self._jobs[job.id] = job

        def update(stage: str | None = None, percent: int | None = None, message: str | None = None) -> None:
            if stage is not None:
                job.stage = stage
            if percent is not None:
                job.percent = max(0, min(100, int(percent)))
            if message is not None:
                job.message = message

        def run() -> None:
            try:
                job.result = target(update)
                job.status = "done"
                job.percent = 100
                if job.stage != "done":
                    job.stage = "done"
            except Exception as exc:  # noqa: BLE001 - surface friendly message
                job.status = "error"
                job.error = str(exc) or "Something went wrong."
                log.exception("Job %s failed: %s", job.id, exc)

        threading.Thread(target=run, daemon=True).start()
        return job.id

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)


_manager = JobManager()


def get_jobs() -> JobManager:
    return _manager
