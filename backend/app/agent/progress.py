"""Progress reporting for a running generation job.

graph.py reports through the ProgressReporter protocol, so tests can record
calls in memory. The database reporter writes each update in its own short
session, because LangGraph runs parallel branches on separate threads.
"""

import logging
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import GenerationJob
from app.schemas.generation import GenerationStage

logger = logging.getLogger(__name__)


class ProgressReporter(Protocol):
    def stage(self, stage: GenerationStage) -> None: ...

    def adjust_lessons_total(self, delta: int) -> None: ...

    def lesson_completed(self) -> None: ...


class NoopProgressReporter:
    def stage(self, stage: GenerationStage) -> None:
        pass

    def adjust_lessons_total(self, delta: int) -> None:
        pass

    def lesson_completed(self) -> None:
        pass


class DatabaseProgressReporter:
    def __init__(self, job_id: str, session_factory: Callable[[], Session]):
        self._job_id = job_id
        self._session_factory = session_factory

    def stage(self, stage: GenerationStage) -> None:
        self._update(stage=stage)

    def adjust_lessons_total(self, delta: int) -> None:
        self._update(lessons_total=GenerationJob.lessons_total + delta)

    def lesson_completed(self) -> None:
        self._update(lessons_completed=GenerationJob.lessons_completed + 1)

    def _update(self, **values: object) -> None:
        # Progress is only for display, so a failed write must not fail the job.
        try:
            with self._session_factory() as db:
                db.execute(
                    update(GenerationJob)
                    .where(GenerationJob.id == self._job_id)
                    .values(**values)
                )
                db.commit()
        except Exception:
            logger.exception("Could not record progress for job %s", self._job_id)
