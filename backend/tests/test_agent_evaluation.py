import importlib.util
from pathlib import Path

from app.agent.evaluation import (
    GOLDEN_TOPICS,
    SCREENING_CASES,
    GoldenTopic,
    ScreeningCase,
    TopicResult,
    build_report,
    classify_failed_attempt,
    decision_hints,
    run_topic,
    summarize,
)
from app.agent.graph import build_graph
from app.agent.llm import CallUsage, GenerationModelConfig
from app.agent.metrics import StageMetrics
from app.agent.schemas import ScreeningDecision
from tests.test_agent_graph import (
    _passing_lesson_content,
    _passing_overview,
    _passing_unit_outline,
)

MODEL_CONFIG = GenerationModelConfig(provider="anthropic")
TOPIC = GoldenTopic(
    id="stub", topic="Testing", audience="beginners", expected_profile="programming"
)


def _allow(**kwargs):
    return ScreeningDecision(allowed=True)


def _lesson(
    profile: str,
    attempts: list[dict],
    passed: bool = True,
    calls: list[CallUsage] | None = None,
    generate_errors: list[str] | None = None,
) -> StageMetrics:
    return StageMetrics(
        stage="lesson_content",
        passed=passed,
        attempts=len(attempts),
        detail=attempts,
        profile=profile,
        calls=calls or [],
        generate_errors=generate_errors or [],
    )


def _fail(problems=None, score=None, feedback=None) -> dict:
    return {
        "problems": problems or [],
        "score": score,
        "feedback": feedback,
        "passed": False,
    }


def _pass(score: int) -> dict:
    return {"problems": [], "score": score, "feedback": "good", "passed": True}


def test_failed_attempts_are_classified_by_cause():
    assert (
        classify_failed_attempt(_fail(["fillBlank blank 3 accepts several numbers"]))
        == "activity check"
    )
    assert (
        classify_failed_attempt(_fail(["reference solution fails its own tests"]))
        == "code check"
    )
    assert (
        classify_failed_attempt(_fail(["lesson 2 uses profile 'x'"])) == "other check"
    )
    assert (
        classify_failed_attempt(
            _fail(score=2, feedback="A reader who only had this lesson could not ...")
        )
        == "solver"
    )
    assert classify_failed_attempt(_fail(score=3, feedback="too shallow")) == "judge"
    assert classify_failed_attempt(_fail()) == "unreadable output"


def test_hints_report_the_activity_share_of_failed_attempts():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        stages=[
            _lesson(
                "conceptual",
                [
                    _fail(["multipleChoice has options that repeat"]),
                    _fail(score=2, feedback="A reader who only had this lesson ..."),
                    _pass(4),
                ],
            ),
            _lesson(
                "narrative",
                [_fail(["categorize repeats an item"]), _fail(score=3), _pass(4)],
            ),
        ],
    )

    summary = summarize([result])
    hints = decision_hints(summary)

    assert summary["failed_lesson_attempts"] == 4
    assert summary["activity_share"] == 0.75
    assert "3 of 4 failed" in hints[0]
    assert "75%" in hints[0]


def test_hints_count_the_narrow_retry_calls_that_actually_ran():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        stages=[
            _lesson(
                "conceptual",
                [_fail(["multipleChoice has options that repeat"]), _pass(4)],
                calls=[
                    CallUsage(purpose="generate", tier="standard"),
                    CallUsage(purpose="generate_activities_fix", tier="standard"),
                ],
            ),
        ],
    )
    summary = summarize([result])
    assert summary["narrow_retries"] == 1
    assert "1 activities-only fix call" in decision_hints(summary)[0]


def test_hints_report_no_failed_attempts_when_a_run_is_clean():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        stages=[_lesson("conceptual", [_pass(5)])],
    )
    hints = decision_hints(summarize([result]))
    assert "no failed lesson attempts" in hints[0]
    assert "not enough profiles" in hints[1]


def test_summarize_counts_generate_exceptions_by_stage():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        stages=[
            StageMetrics(
                stage="overview",
                passed=False,
                attempts=1,
                generate_errors=["attempt 1 (standard): model wrote invalid JSON"],
            ),
            _lesson(
                "conceptual",
                [_pass(5)],
                generate_errors=["attempt 2 (standard): wrote 2 lists for 1 sections"],
            ),
        ],
    )
    summary = summarize([result])

    assert summary["generate_exceptions"] == 2
    assert summary["generate_exceptions_by_stage"] == {
        "overview": 1,
        "lesson_content": 1,
    }
    assert len(summary["generate_error_messages"]) == 2


def test_build_report_lists_generate_exceptions_when_present():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        course=None,
        stages=[
            _lesson(
                "conceptual",
                [_pass(5)],
                generate_errors=["attempt 1 (standard): model wrote invalid JSON"],
            ),
        ],
    )
    report = build_report([result], [], units=1, lessons_per_unit=2)

    assert "## generate() exceptions" in report
    assert "model wrote invalid JSON" in report


def test_build_report_omits_the_generate_exceptions_section_when_clean():
    result = TopicResult(
        topic=TOPIC,
        seconds=1,
        allowed=True,
        course=None,
        stages=[_lesson("conceptual", [_pass(5)])],
    )
    report = build_report([result], [], units=1, lessons_per_unit=2)

    assert "## generate() exceptions" not in report


def test_hints_flag_a_profile_that_scores_clearly_lower():
    stages = [
        _lesson("conceptual", [_pass(5)]),
        _lesson("narrative", [_pass(5)]),
        _lesson("procedural", [_pass(5)]),
        _lesson("quantitative", [_pass(3)]),
    ]
    summary = summarize(
        [TopicResult(topic=TOPIC, seconds=1, allowed=True, stages=stages)]
    )
    routing = decision_hints(summary)[1]

    assert "quantitative (3" in routing
    assert "conceptual" not in routing


def _stub_graph():
    return build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=_passing_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )


def test_run_topic_generates_offline_with_stub_stages():
    result = run_topic(
        TOPIC,
        units=1,
        lessons_per_unit=2,
        model_config=MODEL_CONFIG,
        graph=_stub_graph(),
        screen=_allow,
    )

    assert result.error is None
    assert result.allowed and result.course is not None
    stages = [stage.stage for stage in result.stages]
    assert stages.count("lesson_content") == 2
    lessons = [stage for stage in result.stages if stage.stage == "lesson_content"]
    assert {stage.profile for stage in lessons} == {"programming"}


def test_run_topic_stops_at_a_refusal():
    def refuse(**kwargs):
        return ScreeningDecision(
            allowed=False, category="operational_harm", reason="No."
        )

    result = run_topic(
        TOPIC,
        units=1,
        lessons_per_unit=1,
        model_config=MODEL_CONFIG,
        graph=_stub_graph(),
        screen=refuse,
    )

    assert not result.allowed
    assert result.course is None and result.stages == []
    assert result.refusal_reason == "No."


def test_run_topic_records_an_error_instead_of_raising():
    def broken_overview(**kwargs):
        raise RuntimeError("model is down")

    graph = build_graph(
        overview_fn=broken_overview,
        unit_outline_fn=_passing_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )
    result = run_topic(
        TOPIC,
        units=1,
        lessons_per_unit=1,
        model_config=MODEL_CONFIG,
        graph=graph,
        screen=_allow,
    )

    assert result.error == "RuntimeError: model is down"


def test_report_has_hints_topics_screening_and_activities():
    result = run_topic(
        TOPIC,
        units=1,
        lessons_per_unit=1,
        model_config=MODEL_CONFIG,
        graph=_stub_graph(),
        screen=_allow,
    )
    screening = [
        (
            ScreeningCase("How antibiotics work", "students", True),
            ScreeningDecision(allowed=True),
            None,
        ),
        (
            ScreeningCase("Which stocks should I buy", "me", False),
            ScreeningDecision(allowed=True),
            None,
        ),
    ]

    report = build_report([result], screening, units=1, lessons_per_unit=1)

    assert "## Decision hints" in report
    assert "| stub | ok | programming | 1/1 |" in report
    assert "| Which stocks should I buy | refuse | allow | NO |" in report
    assert "multipleChoice: Is this a test? -> 'Yes'" in report


def test_golden_set_covers_every_profile_and_both_screening_outcomes():
    profiles = {topic.expected_profile for topic in GOLDEN_TOPICS}
    assert profiles == {
        "programming",
        "conceptual",
        "procedural",
        "quantitative",
        "narrative",
        "language",
    }
    assert len({topic.id for topic in GOLDEN_TOPICS}) == len(GOLDEN_TOPICS)
    assert {case.expect_allowed for case in SCREENING_CASES} == {True, False}


def _load_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "eval_generation.py"
    spec = importlib.util.spec_from_file_location("eval_generation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_dry_run_makes_no_calls(capsys):
    assert _load_script().main(["--dry-run"]) == 0
    assert "model calls before retries" in capsys.readouterr().out


def test_script_refuses_to_spend_without_yes(capsys, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert _load_script().main(["--only", "bike-tire"]) == 2
    assert "--yes" in capsys.readouterr().out


def test_script_rejects_unknown_topic_ids(capsys):
    assert _load_script().main(["--only", "nope", "--dry-run"]) == 2
    assert "Unknown topic ids: nope" in capsys.readouterr().out
