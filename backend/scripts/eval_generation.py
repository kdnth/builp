"""Run the golden set and write a report.

This calls the real model with the key in ANTHROPIC_API_KEY, so it costs
money. Run it after a prompt or pipeline change, not in CI.

    uv run python scripts/eval_generation.py --dry-run
    uv run python scripts/eval_generation.py --yes
    uv run python scripts/eval_generation.py --yes --only ww1-causes,bike-tire
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from app.agent.evaluation import (
    GOLDEN_TOPICS,
    SCREENING_CASES,
    TopicResult,
    build_report,
    run_topic,
    summarize,
)
from app.agent.llm import GenerationModelConfig
from app.agent.screening import screen_topic

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--units", type=int, default=1)
    parser.add_argument("--lessons", type=int, default=2, help="lessons per unit")
    parser.add_argument("--only", help="comma-separated topic ids")
    parser.add_argument("--skip-screening", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="plan only, no calls")
    parser.add_argument("--yes", action="store_true", help="confirm the API spend")
    parser.add_argument("--out", type=Path, help="output directory")
    return parser.parse_args(argv)


def _estimated_calls(topic_count: int, units: int, lessons: int, screening: int) -> int:
    per_topic = 1 + 2 + 2 * units + 3 * units * lessons
    return topic_count * per_topic + screening


def _stage_dict(stage) -> dict[str, object]:
    return {
        "stage": stage.stage,
        "profile": stage.profile,
        "passed": stage.passed,
        "attempts": stage.attempts,
        "detail": stage.detail,
        "calls": [call.as_dict() for call in stage.calls],
        "generate_errors": stage.generate_errors,
    }


def _result_dict(result: TopicResult) -> dict[str, object]:
    return {
        "id": result.topic.id,
        "topic": result.topic.topic,
        "expected_profile": result.topic.expected_profile,
        "allowed": result.allowed,
        "refusal_reason": result.refusal_reason,
        "error": result.error,
        "seconds": round(result.seconds, 1),
        "stages": [_stage_dict(stage) for stage in result.stages],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    topics = list(GOLDEN_TOPICS)
    if args.only:
        wanted = {name.strip() for name in args.only.split(",")}
        unknown = wanted - {topic.id for topic in topics}
        if unknown:
            print(f"Unknown topic ids: {', '.join(sorted(unknown))}")
            print(f"Known: {', '.join(topic.id for topic in topics)}")
            return 2
        topics = [topic for topic in topics if topic.id in wanted]

    screening_cases = [] if args.skip_screening else list(SCREENING_CASES)
    estimate = _estimated_calls(
        len(topics), args.units, args.lessons, len(screening_cases)
    )
    print(
        f"{len(topics)} topic(s), {args.units} unit(s) x {args.lessons} lesson(s) "
        f"each, {len(screening_cases)} screening case(s)."
    )
    print(f"About {estimate} model calls before retries. Retries add more.")
    for topic in topics:
        print(f"  - {topic.id}: {topic.topic} (expects {topic.expected_profile})")

    if args.dry_run:
        return 0

    load_dotenv(BACKEND_DIR / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Add it to backend/.env.")
        return 2
    if not args.yes:
        print("This spends API credit. Run again with --yes to continue.")
        return 2

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or BACKEND_DIR / "eval-runs" / stamp
    (out_dir / "courses").mkdir(parents=True, exist_ok=True)
    model_config = GenerationModelConfig(provider="anthropic")

    results: list[TopicResult] = []
    for index, topic in enumerate(topics, start=1):
        print(f"[{index}/{len(topics)}] {topic.id} ...", flush=True)
        result = run_topic(
            topic,
            units=args.units,
            lessons_per_unit=args.lessons,
            model_config=model_config,
        )
        status = result.error or ("refused" if not result.allowed else "ok")
        print(f"    {status} in {result.seconds:.0f}s", flush=True)
        if result.course is not None:
            (out_dir / "courses" / f"{topic.id}.json").write_text(
                result.course.model_dump_json(indent=2)
            )
        results.append(result)

    screening = []
    for case in screening_cases:
        try:
            decision = screen_topic(
                topic=case.topic,
                audience=case.audience,
                learning_goals=None,
                notes=None,
                model_config=model_config,
                calls=[],
            )
            screening.append((case, decision, None))
        except Exception as exc:
            screening.append((case, None, f"{type(exc).__name__}: {exc}"))

    report = build_report(
        results, screening, units=args.units, lessons_per_unit=args.lessons
    )
    (out_dir / "report.md").write_text(report)
    (out_dir / "results.json").write_text(
        json.dumps(
            {
                "units": args.units,
                "lessons_per_unit": args.lessons,
                "summary": summarize(results),
                "topics": [_result_dict(result) for result in results],
                "screening": [
                    {
                        "topic": case.topic,
                        "expect_allowed": case.expect_allowed,
                        "decision": decision.model_dump() if decision else None,
                        "error": error,
                    }
                    for case, decision, error in screening
                ],
            },
            indent=2,
        )
    )
    print(f"\nReport: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
