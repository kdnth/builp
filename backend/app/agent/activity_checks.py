"""Answerability checks for generated interactive activities.

Every activity must have exactly one defensible answer. The failure these
catch looks like this real generated activity:

    subtract = {{blank}} a, b: a {{blank}} b
    result = subtract(10, {{blank}})

The third blank accepted "0" through "9", because the lesson never says
what that argument should be. A long `accepted` list is the model working
around a blank that should not exist.

These checks run at generation time only. The course schema stays
permissive, so courses that already exist and hand-written uploads do not
break.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from app.agent.schemas import (
    GeneratedActivity,
    GeneratedCategorizeActivity,
    GeneratedFillBlankActivity,
    GeneratedMatchingActivity,
    GeneratedMultipleChoiceActivity,
    GeneratedOrderingActivity,
)

BLANK_TOKEN = "{{blank}}"
MAX_BLANKS = 3
MAX_ACCEPTED = 4
MIN_GROUNDED_LENGTH = 3
VARIANT_RATIO = 0.7

_PUNCTUATION_MAP = {
    ord("−"): "-",
    ord("–"): "-",
    ord("—"): "-",
    ord("‘"): "'",
    ord("’"): "'",
    ord("“"): '"',
    ord("”"): '"',
}


def normalize(value: str) -> str:
    """Lowercase, strip accents, unify dashes and quotes, collapse spaces."""
    text = unicodedata.normalize("NFKD", value.translate(_PUNCTUATION_MAP))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().strip().strip(".,;:!?").split())


def _as_number(value: str) -> float | None:
    try:
        return float(value.replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def _is_variant(first: str, second: str) -> bool:
    if not first or not second:
        return False
    if first == second or first in second or second in first:
        return True
    return SequenceMatcher(None, first, second).ratio() >= VARIANT_RATIO


def variant_groups(values: list[str]) -> list[list[str]]:
    """Group writings of the same answer. More than one group means the
    entries are different answers, not variants."""
    groups: list[list[str]] = []
    for value in values:
        for group in groups:
            if any(_is_variant(value, member) for member in group):
                group.append(value)
                break
        else:
            groups.append([value])
    return groups


def check_fill_blank_answerability(
    activity: GeneratedFillBlankActivity,
) -> list[str]:
    problems: list[str] = []

    if len(activity.blanks) > MAX_BLANKS:
        problems.append(
            f"fillBlank has {len(activity.blanks)} blanks, at most {MAX_BLANKS} "
            "are allowed"
        )

    segments = activity.text.split(BLANK_TOKEN)
    for index, segment in enumerate(segments[1:-1], start=1):
        if not re.search(r"\w", segment):
            problems.append(
                f"fillBlank blanks {index} and {index + 1} have no word between "
                "them, so the sentence does not say what belongs in each"
            )

    for index, blank in enumerate(activity.blanks, start=1):
        accepted = [value for value in blank.accepted if value.strip()]
        numbers = {
            number
            for number in (_as_number(value) for value in accepted)
            if number is not None
        }
        if len(numbers) > 1:
            problems.append(
                f"fillBlank blank {index} accepts several different numbers "
                f"({', '.join(sorted(accepted))}), so the learner is free to "
                "choose. Blank a token the lesson determines, or write the "
                "value into the template."
            )
            continue

        if len(accepted) > MAX_ACCEPTED:
            problems.append(
                f"fillBlank blank {index} has {len(accepted)} accepted answers, "
                f"at most {MAX_ACCEPTED} are allowed. List only different "
                "writings of one answer."
            )

        groups = variant_groups([normalize(value) for value in accepted])
        if len(groups) > 1:
            examples = ", ".join(group[0] for group in groups[:3])
            problems.append(
                f"fillBlank blank {index} accepts answers that are not the same "
                f"answer written differently ({examples}). Each blank needs "
                "exactly one defensible answer."
            )

    return problems


def check_multiple_choice_quality(
    activity: GeneratedMultipleChoiceActivity,
) -> list[str]:
    problems: list[str] = []
    options = [normalize(option) for option in activity.options]

    if len(set(options)) != len(options):
        problems.append("multipleChoice has options that repeat")

    if not 0 <= activity.correct_index < len(activity.options):
        return problems

    correct = activity.options[activity.correct_index]
    others = [
        option
        for index, option in enumerate(activity.options)
        if index != activity.correct_index
    ]
    if others:
        longest_other = max(len(option) for option in others)
        average_other = sum(len(option) for option in others) / len(others)
        if len(correct) > longest_other and len(correct) > 1.5 * average_other:
            problems.append(
                "multipleChoice gives away the answer: the correct option is "
                "much longer than every wrong option"
            )

    haystack = normalize(f"{activity.question} {activity.description or ''}")
    needle = normalize(correct)
    if len(needle) >= 4 and needle in haystack:
        problems.append(
            "multipleChoice gives away the answer: the correct option appears "
            "in the question or description"
        )

    return problems


def check_ordering_answerability(activity: GeneratedOrderingActivity) -> list[str]:
    problems: list[str] = []
    if len({normalize(item) for item in activity.items}) != len(activity.items):
        problems.append("ordering repeats an item, so the order is not one order")
    if not activity.basis.strip():
        problems.append("ordering has no basis, so nothing says which order is correct")
    return problems


def check_categorize_answerability(
    activity: GeneratedCategorizeActivity,
) -> list[str]:
    problems: list[str] = []
    categories = {normalize(category) for category in activity.categories}

    for item in activity.items:
        if normalize(item.category) not in categories:
            problems.append(
                f'categorize puts "{item.text}" in category "{item.category}", '
                f"which is not one of {', '.join(activity.categories)}"
            )

    used = {normalize(item.category) for item in activity.items}
    unused = [
        category for category in activity.categories if normalize(category) not in used
    ]
    if unused:
        problems.append(
            f"categorize has no item for {', '.join(unused)}, so the category "
            "is only a distractor"
        )

    if len({normalize(item.text) for item in activity.items}) != len(activity.items):
        problems.append("categorize repeats an item")

    return problems


def check_option_explanations(
    activity: GeneratedMultipleChoiceActivity,
) -> list[str]:
    if activity.option_explanations is None:
        return []
    if len(activity.option_explanations) != len(activity.options):
        return [
            "multipleChoice has "
            f"{len(activity.option_explanations)} option explanations for "
            f"{len(activity.options)} options. Write one for each, or none."
        ]
    return []


def _grounded(answer: str, lesson_text: str) -> bool:
    normalized = normalize(answer)
    if len(normalized) < MIN_GROUNDED_LENGTH or not any(
        char.isalpha() for char in normalized
    ):
        return True
    return normalized in lesson_text


def check_activity_grounding(
    activity: GeneratedActivity,
    written_lesson_markdown: str,
) -> list[str]:
    """Every answer must come from the lesson, not from outside knowledge."""
    lesson_text = normalize(written_lesson_markdown)
    problems: list[str] = []

    if isinstance(activity, GeneratedFillBlankActivity):
        for index, blank in enumerate(activity.blanks, start=1):
            answer = blank.accepted[0] if blank.accepted else ""
            if not _grounded(answer, lesson_text):
                problems.append(
                    f'fillBlank blank {index} expects "{answer}", which the '
                    "written lesson never mentions"
                )
    elif isinstance(activity, GeneratedCategorizeActivity):
        for category in activity.categories:
            if not _grounded(category, lesson_text):
                problems.append(
                    f'categorize uses the category "{category}", which the '
                    "written lesson never mentions"
                )
    elif isinstance(activity, GeneratedMatchingActivity):
        for pair in activity.pairs:
            if not _grounded(pair.term, lesson_text):
                problems.append(
                    f'matching uses the term "{pair.term}", which the written '
                    "lesson never mentions"
                )

    return problems
