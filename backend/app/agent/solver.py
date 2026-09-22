"""The ambiguity solver: a fast model answers the activities blind.

The model sees the lesson and the activities with no answer key. Two
signals come back:

1. Its answer differs from the key. The key may be wrong, or the lesson
   never teaches the answer.
2. It names another answer that is equally correct. The activity is
   ambiguous.

Signal 2 is the one a plain agreement check would miss. A blank that
accepts "0" through "9" agrees with whatever the model picks.
"""

from app.agent import prompts
from app.agent.activity_checks import normalize, variant_groups
from app.agent.budget import TokenBudget
from app.agent.llm import CallUsage, GenerationModelConfig, invoke_structured
from app.agent.schemas import (
    ActivitySolutions,
    GeneratedActivity,
    GeneratedFillBlankActivity,
    GeneratedMultipleChoiceActivity,
    LessonContent,
    SolvedActivity,
)

BLANK_TOKEN = "{{blank}}"
ANSWER_SEPARATOR = "|"


def _solvable(
    activities: list[GeneratedActivity],
) -> list[tuple[int, GeneratedActivity]]:
    return [
        (number, activity)
        for number, activity in enumerate(activities, start=1)
        if isinstance(
            activity, GeneratedFillBlankActivity | GeneratedMultipleChoiceActivity
        )
    ]


def render_activities(activities: list[tuple[int, GeneratedActivity]]) -> str:
    """The activities as the solver sees them: no accepted answers, no
    correct index."""
    blocks: list[str] = []
    for number, activity in activities:
        lines = [f"Activity {number} ({activity.type})"]
        if activity.description:
            lines.append(activity.description)
        if isinstance(activity, GeneratedMultipleChoiceActivity):
            lines.append(f"Question: {activity.question}")
            lines.extend(f"- {option}" for option in activity.options)
        else:
            text = activity.text
            for index in range(1, len(activity.blanks) + 1):
                text = text.replace(BLANK_TOKEN, f"___({index})___", 1)
            lines.append(f"Text: {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _matches(answer: str, accepted: list[str]) -> bool:
    normalized = normalize(answer)
    return any(
        len(variant_groups([normalized, normalize(value)])) == 1 for value in accepted
    )


def _check_fill_blank(
    number: int, activity: GeneratedFillBlankActivity, solved: SolvedActivity
) -> list[str]:
    problems: list[str] = []
    answers = [part.strip() for part in solved.answer.split(ANSWER_SEPARATOR)]
    if len(answers) == len(activity.blanks):
        for index, (answer, blank) in enumerate(
            zip(answers, activity.blanks, strict=True), start=1
        ):
            if not _matches(answer, blank.accepted):
                problems.append(
                    f"activity {number}, blank {index}: a reader answered "
                    f'"{answer}", but the key accepts '
                    f'"{", ".join(blank.accepted)}". Either the key is wrong, '
                    "or the lesson does not say which answer belongs there."
                )

    alternatives = [
        part.strip()
        for part in solved.other_defensible_answer.split(ANSWER_SEPARATOR)
        if part.strip()
    ]
    if len(alternatives) == len(activity.blanks):
        for index, (alternative, blank) in enumerate(
            zip(alternatives, activity.blanks, strict=True), start=1
        ):
            if not _matches(alternative, blank.accepted):
                problems.append(
                    f'activity {number}, blank {index}: "{alternative}" is also '
                    "defensible, so this blank has more than one correct "
                    "answer. Blank a token the lesson determines, or write the "
                    "value into the template."
                )
    return problems


def _check_multiple_choice(
    number: int, activity: GeneratedMultipleChoiceActivity, solved: SolvedActivity
) -> list[str]:
    problems: list[str] = []
    options = [normalize(option) for option in activity.options]
    correct = activity.options[activity.correct_index]

    chosen = normalize(solved.answer)
    if chosen in options and options.index(chosen) != activity.correct_index:
        problems.append(
            f'activity {number}: a reader chose "{solved.answer}", but the key '
            f'says "{correct}". Either the key is wrong, or the lesson does '
            "not teach the answer."
        )

    alternative = normalize(solved.other_defensible_answer)
    if (
        alternative
        and alternative in options
        and options.index(alternative) != activity.correct_index
    ):
        problems.append(
            f'activity {number}: "{solved.other_defensible_answer}" is also '
            "defensible, so this question has more than one correct option."
        )
    return problems


def solve_activities(
    *,
    content: LessonContent,
    model_config: GenerationModelConfig,
    calls: list[CallUsage],
    budget: TokenBudget | None = None,
) -> list[str]:
    """Problems found by answering the activities without the key. An empty
    list means the solver agreed and saw no second answer."""
    activities = _solvable(content.interactive_activities)
    if not activities:
        return []

    solutions = invoke_structured(
        schema=ActivitySolutions,
        messages=prompts.solver_prompt(
            written_lesson_markdown=content.written_lesson_markdown,
            activities_text=render_activities(activities),
        ),
        tier="fast",
        model_config=model_config,
        purpose="solve",
        calls=calls,
        budget=budget,
    )

    by_number = dict(activities)
    problems: list[str] = []
    for solved in solutions.activities:
        activity = by_number.get(solved.activity_number)
        if isinstance(activity, GeneratedFillBlankActivity):
            problems.extend(_check_fill_blank(solved.activity_number, activity, solved))
        elif isinstance(activity, GeneratedMultipleChoiceActivity):
            problems.extend(
                _check_multiple_choice(solved.activity_number, activity, solved)
            )
    return problems
