from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.run import run_generation_job
from app.agent.schemas import ScreeningDecision
from app.models import GenerationJob, GenerationStageMetric
from app.schemas.generation import CreateGenerationJobRequest

REFUSED = ScreeningDecision(
    allowed=False,
    category="individual_medical_advice",
    reason="This asks for advice on your own treatment, which a generated "
    "course cannot give. A course on how the medicine works is fine.",
)


def _job(**overrides) -> GenerationJob:
    values = {
        "id": "job-1",
        "owner_user_id": "user-1",
        "status": "pending",
        "topic": "t",
        "audience": "a",
        "num_units": 1,
        "lessons_per_unit": 1,
    }
    values.update(overrides)
    return GenerationJob(**values)


def _run(db_session, decision):
    db_session.add(_job())
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())
    generated = []

    def fake_run_generation(**kwargs):
        generated.append(kwargs)
        raise RuntimeError("stop after screening")

    with (
        patch("app.agent.run.SessionLocal", factory),
        patch("app.agent.run.run_generation", fake_run_generation),
        patch("app.agent.run.screen_topic", return_value=decision) as screen,
    ):
        run_generation_job("job-1")

    db_session.expire_all()
    return db_session.get(GenerationJob, "job-1"), generated, screen


def test_a_refused_topic_stops_before_any_generation(db_session):
    job, generated, _ = _run(db_session, REFUSED)

    assert job.status == "refused"
    assert job.refusal_category == "individual_medical_advice"
    assert "own treatment" in job.refusal_reason
    assert job.error is None
    assert generated == []


def test_screening_is_recorded_as_a_stage(db_session):
    _run(db_session, REFUSED)

    stages = [row.stage for row in db_session.query(GenerationStageMetric).all()]
    assert stages == ["screening"]


def test_an_allowed_topic_continues_to_generation(db_session):
    job, generated, screen = _run(db_session, ScreeningDecision(allowed=True))

    assert job.status == "failed"
    assert len(generated) == 1
    assert screen.call_count == 1


def test_a_refused_job_does_not_use_the_daily_credit(client, db_session):
    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
        db_session.get(GenerationJob, first.json()["id"]).status = "refused"
        db_session.commit()

        second = client.post(
            "/api/generation-jobs", json={"topic": "x2", "audience": "y2"}
        )

    assert second.status_code == 201


def test_a_failed_job_still_uses_the_daily_credit(client, db_session):
    with patch("app.routers.generation.run_generation_job"):
        first = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        )
        db_session.get(GenerationJob, first.json()["id"]).status = "failed"
        db_session.commit()

        second = client.post(
            "/api/generation-jobs", json={"topic": "x2", "audience": "y2"}
        )

    assert second.status_code == 429


def test_refusal_fields_are_returned_by_the_api(client, db_session):
    with patch("app.routers.generation.run_generation_job"):
        job_id = client.post(
            "/api/generation-jobs", json={"topic": "x", "audience": "y"}
        ).json()["id"]
    job = db_session.get(GenerationJob, job_id)
    job.status = "refused"
    job.refusal_category = "operational_harm"
    job.refusal_reason = "No."
    db_session.commit()

    body = client.get(f"/api/generation-jobs/{job_id}").json()
    assert body["status"] == "refused"
    assert body["refusal_category"] == "operational_harm"
    assert body["refusal_reason"] == "No."


def test_programming_course_rejects_a_missing_language():
    with pytest.raises(ValueError, match="javascript or python"):
        CreateGenerationJobRequest(topic="t", audience="a", language="none")


def test_programming_course_defaults_to_javascript_and_one_long_read():
    request = CreateGenerationJobRequest(topic="t", audience="a")
    assert request.language == "javascript"
    assert request.reading_style == "single"
    assert request.course_type == "programming"
    assert request.level == "beginner"


def test_general_course_defaults_to_auto_language_and_quick_checks():
    request = CreateGenerationJobRequest(topic="t", audience="a", course_type="general")
    assert request.language == "auto"
    assert request.reading_style == "interleaved"


def test_general_course_can_forbid_or_fix_code_practice():
    assert (
        CreateGenerationJobRequest(
            topic="t", audience="a", course_type="general", language="none"
        ).language
        == "none"
    )
    assert (
        CreateGenerationJobRequest(
            topic="t", audience="a", course_type="general", language="python"
        ).language
        == "python"
    )


def test_context_fields_have_a_length_limit():
    with pytest.raises(ValueError):
        CreateGenerationJobRequest(topic="t", audience="a", notes="x" * 1001)
    with pytest.raises(ValueError):
        CreateGenerationJobRequest(topic="t", audience="a", learning_goals="x" * 1001)


def test_user_context_is_stored_and_returned(client, db_session):
    with patch("app.routers.generation.run_generation_job"):
        body = client.post(
            "/api/generation-jobs",
            json={
                "topic": "Macroeconomics",
                "audience": "students",
                "course_type": "general",
                "learning_goals": "read a supply curve",
                "level": "intermediate",
                "notes": "UK spelling",
            },
        ).json()

    assert body["course_type"] == "general"
    assert body["language"] == "auto"
    assert body["reading_style"] == "interleaved"
    assert body["level"] == "intermediate"
    assert body["learning_goals"] == "read a supply curve"
    assert body["notes"] == "UK spelling"

    stored = db_session.get(GenerationJob, body["id"])
    assert stored.course_type == "general"
    assert stored.notes == "UK spelling"
