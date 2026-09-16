from threading import Lock
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.graph import build_graph, run_generation
from app.agent.llm import CallUsage, GenerationModelConfig, invoke_structured
from app.agent.metrics import (
    DatabaseMetricsReporter,
    StageMetrics,
    stage_metrics,
    summarize_job_metrics,
)
from app.agent.run import run_generation_job
from app.agent.schemas import EvaluationResult, ScreeningDecision
from app.agent.stage import StageAttempt, StageOutcome, run_stage_with_retries
from app.models import GenerationJob, GenerationStageMetric
from tests.test_agent_graph import (
    _passing_lesson_content,
    _passing_overview,
    _passing_unit_outline,
)

ALLOWED = ScreeningDecision(allowed=True)


class RecordingMetrics:
    def __init__(self):
        self.stages: list[StageMetrics] = []
        self._lock = Lock()

    def record_stage(self, metrics: StageMetrics) -> None:
        with self._lock:
            self.stages.append(metrics)


class FakeMessage:
    def __init__(self, usage):
        self.usage_metadata = usage


class FakeStructuredModel:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def with_structured_output(self, schema, include_raw=False):
        assert include_raw is True
        return self

    def invoke(self, messages):
        self.calls += 1
        return self._result


def _fake_model(result):
    model = FakeStructuredModel(result)
    return patch("app.agent.llm.get_model", return_value=model), model


def _job(**overrides) -> GenerationJob:
    values = {
        "id": "job-1",
        "owner_user_id": "user-1",
        "status": "running",
        "topic": "t",
        "audience": "a",
        "num_units": 1,
        "lessons_per_unit": 1,
    }
    values.update(overrides)
    return GenerationJob(**values)


def test_invoke_structured_records_usage_and_returns_parsed():
    parsed = EvaluationResult(passed=True, score=5, feedback="good")
    raw = FakeMessage(
        {
            "input_tokens": 120,
            "output_tokens": 30,
            "input_token_details": {"cache_read": 100, "cache_creation": 20},
        }
    )
    patcher, model = _fake_model({"parsed": parsed, "raw": raw, "parsing_error": None})
    calls: list[CallUsage] = []

    with patcher:
        result = invoke_structured(
            schema=EvaluationResult,
            messages=[],
            tier="fast",
            model_config=GenerationModelConfig(provider="anthropic"),
            purpose="evaluate",
            calls=calls,
        )

    assert result is parsed
    assert model.calls == 1
    assert calls == [
        CallUsage(
            purpose="evaluate",
            tier="fast",
            input_tokens=120,
            output_tokens=30,
            cache_read_tokens=100,
            cache_creation_tokens=20,
        )
    ]


def test_invoke_structured_raises_on_parsing_error_and_still_records_usage():
    raw = FakeMessage({"input_tokens": 10, "output_tokens": 1})
    patcher, _ = _fake_model(
        {"parsed": None, "raw": raw, "parsing_error": ValueError("bad json")}
    )
    calls: list[CallUsage] = []

    with patcher, pytest.raises(ValueError, match="did not return a valid"):
        invoke_structured(
            schema=EvaluationResult,
            messages=[],
            tier="standard",
            model_config=GenerationModelConfig(provider="anthropic"),
            purpose="generate",
            calls=calls,
        )

    assert len(calls) == 1
    assert calls[0].input_tokens == 10


def test_run_stage_with_retries_carries_calls_into_the_outcome():
    calls = [CallUsage(purpose="generate", tier="fast", input_tokens=5)]
    outcome = run_stage_with_retries(
        generate=lambda tier, feedback: "content",
        check=lambda content: [],
        evaluate=lambda content: EvaluationResult(passed=True, score=5, feedback="ok"),
        default_tier="fast",
        calls=calls,
    )

    assert outcome.calls == calls


def test_stage_metrics_reads_attempts_scores_and_problems():
    outcome = StageOutcome(
        content="x",
        passed=True,
        attempts=[
            StageAttempt(
                attempt=1, tier="fast", content="x", problems=["bad"], evaluation=None
            ),
            StageAttempt(
                attempt=2,
                tier="standard",
                content="x",
                problems=[],
                evaluation=EvaluationResult(passed=True, score=4, feedback="ok"),
            ),
        ],
        calls=[CallUsage(purpose="generate", tier="fast", input_tokens=7)],
    )

    metrics = stage_metrics("lesson_content", outcome)

    assert metrics.attempts == 2
    assert metrics.detail[0]["problems"] == ["bad"]
    assert metrics.detail[0]["score"] is None
    assert metrics.detail[1]["score"] == 4
    assert metrics.totals()["input_tokens"] == 7


def test_database_reporter_writes_one_row_per_stage(db_session):
    db_session.add(_job())
    db_session.commit()
    reporter = DatabaseMetricsReporter(
        "job-1", sessionmaker(bind=db_session.get_bind())
    )

    reporter.record_stage(
        StageMetrics(
            stage="overview",
            passed=True,
            attempts=2,
            detail=[{"attempt": 1, "score": 3}],
            calls=[
                CallUsage(
                    purpose="generate",
                    tier="standard",
                    input_tokens=100,
                    output_tokens=50,
                    cache_read_tokens=80,
                ),
                CallUsage(purpose="evaluate", tier="fast", input_tokens=20),
            ],
        )
    )

    row = db_session.query(GenerationStageMetric).one()
    assert (row.stage, row.passed, row.attempts) == ("overview", True, 2)
    assert (row.input_tokens, row.output_tokens, row.cache_read_tokens) == (120, 50, 80)
    assert row.detail["attempts"] == [{"attempt": 1, "score": 3}]
    assert [call["purpose"] for call in row.detail["calls"]] == [
        "generate",
        "evaluate",
    ]


def test_database_reporter_never_raises():
    def broken_session():
        raise RuntimeError("database is down")

    DatabaseMetricsReporter("job-1", broken_session).record_stage(
        StageMetrics(stage="overview", passed=True, attempts=1)
    )


def test_summarize_job_metrics_aggregates_stages_and_tokens(db_session):
    db_session.add(_job())
    db_session.commit()
    reporter = DatabaseMetricsReporter(
        "job-1", sessionmaker(bind=db_session.get_bind())
    )
    reporter.record_stage(
        StageMetrics(
            stage="overview",
            passed=True,
            attempts=1,
            calls=[CallUsage(purpose="generate", tier="standard", input_tokens=10)],
        )
    )
    reporter.record_stage(
        StageMetrics(
            stage="lesson_content",
            passed=False,
            attempts=3,
            calls=[
                CallUsage(purpose="generate", tier="strong", output_tokens=5),
                CallUsage(purpose="evaluate", tier="fast", input_tokens=2),
            ],
        )
    )

    summary = summarize_job_metrics(db_session, "job-1")

    assert summary["stages"] == {
        "overview": {"runs": 1, "attempts": 1, "not_passed": 0},
        "lesson_content": {"runs": 1, "attempts": 3, "not_passed": 1},
    }
    assert summary["calls"] == {"generate": 2, "evaluate": 1}
    assert summary["tokens"]["input_tokens"] == 12
    assert summary["tokens"]["output_tokens"] == 5
    assert "recorded_at" in summary


def test_graph_records_one_stage_per_call():
    reporter = RecordingMetrics()
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
        metrics=reporter,
        graph=graph,
    )

    stages = [metrics.stage for metrics in reporter.stages]
    assert stages.count("overview") == 1
    assert stages.count("unit_outline") == 2
    assert stages.count("lesson_content") == 6


def test_run_generation_job_stores_a_metrics_summary(db_session):
    db_session.add(_job(status="pending"))
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())

    def fake_run_generation(**kwargs):
        kwargs["metrics"].record_stage(
            StageMetrics(
                stage="overview",
                passed=True,
                attempts=1,
                calls=[CallUsage(purpose="generate", tier="standard", input_tokens=9)],
            )
        )
        raise RuntimeError("stop after the overview")

    with (
        patch("app.agent.run.SessionLocal", factory),
        patch("app.agent.run.run_generation", fake_run_generation),
        patch("app.agent.run.screen_topic", return_value=ALLOWED),
    ):
        run_generation_job("job-1")

    db_session.expire_all()
    job = db_session.get(GenerationJob, "job-1")
    assert job.status == "failed"
    assert job.metrics["stages"]["overview"] == {
        "runs": 1,
        "attempts": 1,
        "not_passed": 0,
    }
    assert job.metrics["tokens"]["input_tokens"] == 9
