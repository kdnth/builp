from unittest.mock import patch

import pytest

from app.agent.budget import (
    DEFAULT_LESSON_TOKENS,
    DEFAULT_SCREENING_TOKENS,
    DEFAULT_UNIT_TOKENS,
    TokenBudget,
    TokenBudgetExceeded,
    job_token_budget,
)
from app.agent.graph import build_graph, run_generation
from app.agent.llm import CallUsage, GenerationModelConfig, invoke_structured
from app.agent.run import run_generation_job
from app.agent.schemas import EvaluationResult, ScreeningDecision
from app.agent.stage import run_stage_with_retries
from app.models import GenerationJob
from tests.factories import make_lesson_summary, make_overview

MODEL_CONFIG = GenerationModelConfig(provider="anthropic")


def _usage(
    input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_creation_tokens=0
):
    return CallUsage(
        purpose="generate",
        tier="standard",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
    )


def test_budget_allows_spend_under_the_limit():
    budget = TokenBudget(limit=1000)
    budget.record(_usage(input_tokens=400, output_tokens=200))
    assert budget.spent == 600


def test_budget_raises_once_spend_crosses_the_limit():
    budget = TokenBudget(limit=1000)
    budget.record(_usage(input_tokens=400, output_tokens=200))

    with pytest.raises(TokenBudgetExceeded) as excinfo:
        budget.record(_usage(input_tokens=300, output_tokens=200))

    assert excinfo.value.spent == 1100
    assert excinfo.value.limit == 1000
    assert "1,100" in str(excinfo.value) and "1,000" in str(excinfo.value)


def test_budget_counts_cache_creation_but_not_cache_read():
    budget = TokenBudget(limit=1000)
    budget.record(_usage(input_tokens=100, output_tokens=50, cache_read_tokens=5000))
    assert budget.spent == 150

    with pytest.raises(TokenBudgetExceeded):
        budget.record(
            _usage(input_tokens=500, output_tokens=500, cache_creation_tokens=1)
        )


def test_job_token_budget_matches_the_documented_defaults():
    assert job_token_budget(1, 2) == (
        DEFAULT_SCREENING_TOKENS + DEFAULT_UNIT_TOKENS + 2 * DEFAULT_LESSON_TOKENS
    )
    assert job_token_budget(3, 4) == (
        DEFAULT_SCREENING_TOKENS + 3 * DEFAULT_UNIT_TOKENS + 12 * DEFAULT_LESSON_TOKENS
    )


def test_job_token_budget_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("COURSE_GEN_TOKEN_BUDGET_SCREENING", "1")
    monkeypatch.setenv("COURSE_GEN_TOKEN_BUDGET_PER_UNIT", "2")
    monkeypatch.setenv("COURSE_GEN_TOKEN_BUDGET_PER_LESSON", "3")

    assert job_token_budget(2, 5) == 1 + 2 * 2 + 3 * 2 * 5


def test_invoke_structured_reports_usage_to_the_budget():
    class FakeModel:
        def with_structured_output(self, schema, include_raw=False):
            return self

        def invoke(self, messages):
            usage = {
                "input_tokens": 100,
                "output_tokens": 50,
                "input_token_details": {},
            }
            raw = type("Raw", (), {"usage_metadata": usage})()
            return {
                "parsed": EvaluationResult(passed=True, score=5, feedback="ok"),
                "raw": raw,
                "parsing_error": None,
            }

    budget = TokenBudget(limit=1000)
    with patch("app.agent.llm.get_model", return_value=FakeModel()):
        invoke_structured(
            schema=EvaluationResult,
            messages=[],
            tier="fast",
            model_config=MODEL_CONFIG,
            purpose="evaluate",
            calls=[],
            budget=budget,
        )

    assert budget.spent == 150


def test_exceeding_the_budget_during_generate_stops_the_retry_loop_immediately():
    budget = TokenBudget(limit=100)
    call_count = 0

    def generate(tier, feedback):
        nonlocal call_count
        call_count += 1
        budget.record(_usage(input_tokens=200))
        return "unreachable"

    with pytest.raises(TokenBudgetExceeded):
        run_stage_with_retries(
            generate=generate,
            check=lambda content: [],
            evaluate=lambda content: EvaluationResult(
                passed=True, score=5, feedback="x"
            ),
            default_tier="standard",
            max_attempts=3,
        )

    # it stopped on the first over-budget call.
    assert call_count == 1


def test_exceeding_the_budget_during_evaluate_stops_the_retry_loop_immediately():
    budget = TokenBudget(limit=100)
    evaluate_calls = 0

    def evaluate(content):
        nonlocal evaluate_calls
        evaluate_calls += 1
        budget.record(_usage(input_tokens=200))
        return EvaluationResult(passed=True, score=5, feedback="x")

    with pytest.raises(TokenBudgetExceeded):
        run_stage_with_retries(
            generate=lambda tier, feedback: "content",
            check=lambda content: [],
            evaluate=evaluate,
            default_tier="standard",
            max_attempts=3,
        )

    assert evaluate_calls == 1


def test_the_fan_out_clamp_now_contains_the_incident_on_its_own():
    """Reproduces the incident: a request for 1 unit gets an overview back
    with 6 units instead. The fan-out clamp (added after this incident,
    in app/agent/graph.py) now truncates that before it ever reaches
    unit-outline generation, so this no longer needs the budget backstop
    at all - the two fixes are independent layers, and this shows the
    first one alone already contains the exact shape of what happened."""
    outline_calls = 0
    lesson_calls = 0

    def runaway_overview(*, topic, audience, num_units, budget, **kwargs):
        overview = make_overview(num_units=6)
        return _outcome(overview)

    def counting_unit_outline(*, overview, unit, lessons_per_unit, budget, **kwargs):
        nonlocal outline_calls
        outline_calls += 1
        budget.record(_usage(input_tokens=20_000))
        return _outcome(_outline(lessons_per_unit))

    def counting_lesson_content(*, budget, **kwargs):
        nonlocal lesson_calls
        lesson_calls += 1
        budget.record(_usage(input_tokens=1))
        return _outcome(_lesson_content())

    graph = build_graph(
        overview_fn=runaway_overview,
        unit_outline_fn=counting_unit_outline,
        lesson_content_fn=counting_lesson_content,
    )
    budget = TokenBudget(limit=30_000)

    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=1,
        lessons_per_unit=2,
        budget=budget,
        graph=graph,
    )

    assert len(course.units) == 1
    assert outline_calls == 1
    assert lesson_calls == 2
    assert budget.spent <= 30_000


def test_the_budget_is_still_needed_for_a_compliant_but_costly_job():
    """The clamp only bounds *count*. A request for exactly 1 unit and 2
    lessons that happens to spend heavily on each lesson - deep internal
    retries, for example - still needs the budget as a backstop, since
    nothing about the fan-out itself is wrong here."""

    def compliant_overview(*, num_units, **kwargs):
        return _outcome(make_overview(num_units=num_units))

    def compliant_outline(*, lessons_per_unit, **kwargs):
        return _outcome(_outline(lessons_per_unit))

    def costly_lesson_content(*, budget, **kwargs):
        budget.record(_usage(input_tokens=50_000))
        return _outcome(_lesson_content())

    graph = build_graph(
        overview_fn=compliant_overview,
        unit_outline_fn=compliant_outline,
        lesson_content_fn=costly_lesson_content,
    )
    budget = TokenBudget(limit=60_000)

    with pytest.raises(TokenBudgetExceeded):
        run_generation(
            topic="testing",
            audience="beginners",
            num_units=1,
            lessons_per_unit=2,
            budget=budget,
            graph=graph,
        )

    assert budget.spent > 60_000


def _outcome(content):
    from app.agent.stage import StageOutcome

    return StageOutcome(content=content, passed=True, attempts=[])


def _outline(lessons_per_unit):
    from app.agent.schemas import UnitOutline

    return UnitOutline(
        lessons=[make_lesson_summary(title=f"L{i}") for i in range(lessons_per_unit)]
    )


def _lesson_content():
    from tests.factories import make_lesson_content

    return make_lesson_content(markdown="# x")


def test_run_generation_job_fails_clearly_when_the_budget_is_exceeded(db_session):
    from sqlalchemy.orm import sessionmaker

    db_session.add(
        GenerationJob(
            id="job-budget",
            owner_user_id="user-1",
            status="pending",
            topic="t",
            audience="a",
            num_units=1,
            lessons_per_unit=1,
        )
    )
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())

    def fake_run_generation(**kwargs):
        kwargs["budget"].record(_usage(input_tokens=10**9))

    with (
        patch("app.agent.run.SessionLocal", factory),
        patch("app.agent.run.run_generation", fake_run_generation),
        patch(
            "app.agent.run.screen_topic",
            return_value=ScreeningDecision(allowed=True),
        ),
    ):
        run_generation_job("job-budget")

    db_session.expire_all()
    job = db_session.get(GenerationJob, "job-budget")
    assert job.status == "failed"
    assert "token budget" in job.error
