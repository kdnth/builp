from datetime import UTC, datetime, timedelta
from threading import Lock
from unittest.mock import patch

from sqlalchemy.orm import sessionmaker

from app.agent.graph import build_graph, run_generation
from app.agent.progress import DatabaseProgressReporter
from app.agent.run import run_generation_job
from app.agent.schemas import ScreeningDecision
from app.models import GenerationJob
from tests.test_agent_graph import (
    _passing_lesson_content,
    _passing_overview,
    _passing_unit_outline,
)


class RecordingReporter:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []
        self._lock = Lock()

    def stage(self, stage):
        with self._lock:
            self.calls.append(("stage", stage))

    def set_lessons_total(self, total):
        with self._lock:
            self.calls.append(("total", total))

    def lesson_completed(self):
        with self._lock:
            self.calls.append(("lesson", None))


def _job(**overrides) -> GenerationJob:
    values = {
        "id": "job-1",
        "owner_user_id": "user-1",
        "status": "running",
        "topic": "t",
        "audience": "a",
        "num_units": 2,
        "lessons_per_unit": 2,
        "lessons_total": 4,
    }
    values.update(overrides)
    return GenerationJob(**values)


def test_graph_reports_stages_and_every_completed_lesson():
    reporter = RecordingReporter()
    graph = build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=_passing_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )
    run_generation(
        topic="t",
        audience="a",
        num_units=2,
        lessons_per_unit=3,
        progress=reporter,
        graph=graph,
    )

    stages = [value for kind, value in reporter.calls if kind == "stage"]
    assert stages[0] == "units"
    assert "lessons" in stages
    assert stages[-1] == "assembling"
    assert [kind for kind, _ in reporter.calls].count("lesson") == 6
    assert ("total", 6) in reporter.calls


def test_graph_reports_the_real_lesson_total_when_an_outline_is_short():
    def uneven_outline(**kwargs):
        outcome = _passing_unit_outline(**kwargs)
        if kwargs["unit"].title == "Unit 2":
            outcome.content.lessons.pop()
        return outcome

    reporter = RecordingReporter()
    graph = build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=uneven_outline,
        lesson_content_fn=_passing_lesson_content,
    )
    run_generation(
        topic="t",
        audience="a",
        num_units=2,
        lessons_per_unit=2,
        progress=reporter,
        graph=graph,
    )

    assert ("total", 3) in reporter.calls
    assert [kind for kind, _ in reporter.calls].count("lesson") == 3


def test_database_reporter_updates_the_job_row(db_session):
    db_session.add(_job(updated_at=datetime.now(UTC) - timedelta(hours=1)))
    db_session.commit()
    before = db_session.get(GenerationJob, "job-1").updated_at

    reporter = DatabaseProgressReporter(
        "job-1", sessionmaker(bind=db_session.get_bind())
    )
    reporter.stage("lessons")
    reporter.set_lessons_total(3)
    reporter.lesson_completed()
    reporter.lesson_completed()

    db_session.expire_all()
    job = db_session.get(GenerationJob, "job-1")
    assert job.stage == "lessons"
    assert job.lessons_total == 3
    assert job.lessons_completed == 2
    assert job.updated_at > before


def test_database_reporter_never_raises(db_session):
    def broken_session():
        raise RuntimeError("database is down")

    reporter = DatabaseProgressReporter("job-1", broken_session)
    reporter.stage("lessons")
    reporter.lesson_completed()


def test_run_generation_job_sets_initial_progress_and_reports(db_session):
    db_session.add(_job(status="pending", lessons_total=None))
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())
    seen_progress = {}

    def fake_run_generation(**kwargs):
        with factory() as db:
            job = db.get(GenerationJob, "job-1")
            seen_progress.update(
                status=job.status,
                stage=job.stage,
                lessons_total=job.lessons_total,
                lessons_completed=job.lessons_completed,
            )
        kwargs["progress"].lesson_completed()
        raise RuntimeError("stop after progress check")

    with (
        patch("app.agent.run.SessionLocal", factory),
        patch("app.agent.run.run_generation", fake_run_generation),
        patch(
            "app.agent.run.screen_topic",
            return_value=ScreeningDecision(allowed=True),
        ),
    ):
        run_generation_job("job-1")

    assert seen_progress == {
        "status": "running",
        "stage": "outline",
        "lessons_total": 4,
        "lessons_completed": 0,
    }
    db_session.expire_all()
    job = db_session.get(GenerationJob, "job-1")
    assert job.lessons_completed == 1
    assert job.status == "failed"
