"""Prompt construction.

Each stage's system message is built from stable, reused context (the
overview, a unit's outline) via `cached_system_message`. Anthropic gets
prompt cache breakpoints on that stable prefix; other providers fall back
to plain system messages. The per-call instruction (which unit, which
lesson, retry feedback) goes in a separate, uncached human message, since
it's different on every call and caching it would do nothing but add
overhead.
"""

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agent.llm import SupportedProvider, cached_system_message
from app.agent.schemas import CourseOverview, LessonContent, UnitOutline, UnitSummary
from app.schemas.course import CodeLanguage

LANGUAGE_NAMES: dict[CodeLanguage, str] = {
    "javascript": "JavaScript",
    "python": "Python",
}


def _feedback_block(feedback: str | None) -> str:
    if not feedback:
        return ""
    return (
        f"\n\nYour previous attempt had problems. Fix these specifically:\n{feedback}"
    )


def render_overview(overview: CourseOverview) -> str:
    lines = [
        f"# {overview.title}",
        "",
        overview.description,
        "",
        f"Audience: {overview.audience}",
        "",
        "Units:",
    ]
    for index, unit in enumerate(overview.units, start=1):
        lines.append(f"{index}. {unit.title} - {unit.goal}")
    return "\n".join(lines)


def render_unit_outline(unit: UnitSummary, outline: UnitOutline) -> str:
    lines = [f"## {unit.title}", unit.goal, "", "Lessons:"]
    for index, lesson in enumerate(outline.lessons, start=1):
        extras = []
        if lesson.include_code_practice:
            extras.append("code practice")
        extras.extend(lesson.interactive_activity_types)
        extra_text = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"{index}. {lesson.title} - {lesson.goal}{extra_text}")
    return "\n".join(lines)


# --- Stage 1: course overview --------------------------------------------

OVERVIEW_SYSTEM = """You design programming course curricula. Given a topic \
and audience, you produce a course overview: a title, a short learner-\
facing description, an audience statement, and an ordered list of units \
that build on each other logically. Do not write lesson-level detail yet, \
only unit-level scope."""


def overview_generate_prompt(
    *,
    topic: str,
    audience: str,
    num_units: int,
    language: CodeLanguage,
    feedback: str | None,
) -> list[BaseMessage]:
    human = (
        f"Topic: {topic}\n"
        f"Audience: {audience}\n"
        f"Programming language: {LANGUAGE_NAMES[language]}\n"
        f"Number of units: exactly {num_units}. Not fewer, not more.\n"
        "Produce the course overview." + _feedback_block(feedback)
    )
    return [SystemMessage(content=OVERVIEW_SYSTEM), HumanMessage(content=human)]


OVERVIEW_EVAL_SYSTEM = """You are a strict curriculum reviewer. You judge a \
generated course overview against three criteria:

1. Topic coverage: do the units, together, actually cover the stated topic \
   at a reasonable depth for the stated audience?
2. Scope: is each unit an appropriately sized chunk, not too broad or too \
   narrow, and not overlapping with another unit?
3. Logical progression: does each unit build on knowledge from the units \
   before it, in a sensible order?

Score 1-5. Pass only if the overview is genuinely usable as-is; a 3 should \
still fail. Be specific in feedback: name the unit and the exact problem."""


def overview_evaluate_prompt(overview: CourseOverview) -> list[BaseMessage]:
    return [
        SystemMessage(content=OVERVIEW_EVAL_SYSTEM),
        HumanMessage(content=render_overview(overview)),
    ]


# --- Stage 2: unit outline (one call per unit) ---------------------------

UNIT_OUTLINE_SYSTEM = """You write the lesson-level outline for one unit of \
a course. You are given the full course overview for context. Produce an \
ordered list of lessons for just this one unit. Each lesson needs a title, \
a one-sentence goal (what the learner can do afterward), whether it should \
include a runnable code practice, and which interactive activity types (if \
any) fit it. Not every lesson needs every activity type; use judgment."""


def unit_outline_generate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    lessons_per_unit: int,
    language: CodeLanguage,
    feedback: str | None,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    system = cached_system_message(
        f"{UNIT_OUTLINE_SYSTEM}\n\n{render_overview(overview)}",
        provider=provider,
    )
    human = (
        f'Write the outline for this unit: "{unit.title}" - {unit.goal}\n'
        f"Programming language: {LANGUAGE_NAMES[language]}\n"
        f"Exactly {lessons_per_unit} lessons. Not fewer, not more."
        + _feedback_block(feedback)
    )
    return [system, HumanMessage(content=human)]


UNIT_OUTLINE_EVAL_SYSTEM = """You are a strict curriculum reviewer judging \
one unit's lesson outline against two criteria:

1. Coherence with the course overview: does this unit actually deliver on \
   the goal stated for it in the overview, and stay in its lane (not \
   duplicating another unit)?
2. Internal lesson progression: do the lessons within this unit build on \
   each other in a sensible order?

Score 1-5. Pass only if genuinely usable as-is. Be specific: name the \
lesson and the exact problem."""


def unit_outline_evaluate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    system = cached_system_message(
        f"{UNIT_OUTLINE_EVAL_SYSTEM}\n\n{render_overview(overview)}",
        provider=provider,
    )
    human = render_unit_outline(unit, outline)
    return [system, HumanMessage(content=human)]


# --- Stage 3: lesson content (one call per lesson) ------------------------

_CODE_PRACTICE_RULES: dict[CodeLanguage, str] = {
    "javascript": """For a code practice: write function_signature as a plain \
call like 'add(a, b)' or 'isPalindrome(s)'. Write reference_solution as a \
complete, correct JavaScript function implementing it, e.g. \
'function add(a, b) { return a + b }' - this is used only to verify your \
test suite is internally consistent, and is never shown to the learner. \
Write at least 2 test cases that a correct solution would pass, including \
at least one edge case.""",
    "python": """For a code practice: write function_signature as a plain \
call with snake_case names, like 'add(a, b)' or 'is_palindrome(s)'. Write \
reference_solution as a complete, correct Python function implementing \
it, e.g. 'def add(a, b):\\n    return a + b'. Use only the standard library, \
and do not read input or files. This is used only to verify your test \
suite is internally consistent, and is never shown to the learner. Write \
at least 2 test cases that a correct solution would pass, including at \
least one edge case.

The function must return a JSON-compatible value: a number, string, bool, \
None, list, or dict with string keys. Do not return a tuple, set, or \
custom object, and do not return NaN or infinity. The learner's result is \
compared as JSON, so 2.0 matches an expected 2, and dict keys must be in \
the same order as in expected_output.""",
}

_LESSON_CONTENT_SYSTEM_TEMPLATE = """You write the full content for one \
lesson: a written explanation in markdown, an optional runnable code \
practice, and 1-3 interactive activities that check understanding of the \
lesson's goal. Write every code example in {language}.

{code_practice_rules}

Critical constraint: encode every test-case argument and expected_output \
as a JSON string (for example '3', '"hello"', 'true', 'null', '[1, 2]', \
'{{"a": 1}}'). After decoding, each value must be plain JSON (number, \
string, boolean, array, object, or null). Never a function, and never a \
string containing code meant to be parsed as a function (like \
'(n) => n * 2' or 'lambda n: n * 2') - test cases are run by calling the \
solution directly with these exact values, so a stringified callback \
would just be passed as a literal string, not called. This means: do not \
write a code practice whose parameters need to be functions (no \
map-style callback parameters, no comparator functions). Pick a function \
signature for this lesson's concept that only needs plain data values as \
arguments, even if the lesson's written content and interactive \
activities do cover callbacks.

Every activity must have exactly one defensible answer, and the learner \
must be able to find that answer in this lesson. If a reasonable learner \
could give a different answer that is also correct, the activity is wrong, \
even when your answer key is one of the correct answers.

For a fillBlank activity: write text with each blank as the literal \
token {{{{blank}}}}, and provide one entry in blanks for each token, in \
the same order they appear in the text. Blank only a token that the lesson \
and the sentence determine: a keyword, an operator, a term, or a required \
value. Never blank a value the author is free to choose, such as an \
argument in an example call, sample data, or a variable name. Write those \
values into the template instead. Use at most 3 blanks, and always keep a \
word between two blanks. In `accepted`, list only different writings of \
the same answer (upper and lower case, spacing, accents, US and UK \
spelling), never different answers. If a slot could hold several correct \
values, either fix the value in the template or ask about it with a \
multipleChoice activity.

For a multipleChoice activity: exactly one option is defensible. Wrong \
options should be plausible, not obviously silly. Do not make the correct \
option the longest one, and do not repeat the question's wording in it.

Match the difficulty to the lesson goal and the course's stated audience. \
Every activity should actually test the lesson's specific goal, not \
generic trivia."""


def lesson_content_system(language: CodeLanguage) -> str:
    return _LESSON_CONTENT_SYSTEM_TEMPLATE.format(
        language=LANGUAGE_NAMES[language],
        code_practice_rules=_CODE_PRACTICE_RULES[language],
    )


def lesson_content_generate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    language: CodeLanguage,
    feedback: str | None,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    lesson = outline.lessons[lesson_index]
    context = (
        f"{lesson_content_system(language)}\n\n"
        f"Course audience: {overview.audience}\n\n"
        f"{render_unit_outline(unit, outline)}"
    )
    system = cached_system_message(context, provider=provider)

    extras = []
    if lesson.include_code_practice:
        extras.append("Include a code practice.")
    else:
        extras.append("Do not include a code practice.")
    if lesson.interactive_activity_types:
        extras.append(
            "Include these interactive activity types, in this order: "
            + ", ".join(lesson.interactive_activity_types)
        )

    human = (
        f'Write the content for this lesson: "{lesson.title}" - {lesson.goal}\n'
        + " ".join(extras)
        + _feedback_block(feedback)
    )
    return [system, HumanMessage(content=human)]


LESSON_CONTENT_EVAL_SYSTEM = """You are a strict reviewer judging one \
lesson's content against four criteria (a code test correctness check \
has already run separately; don't re-check that):

1. Accuracy: is the written content factually correct?
2. Difficulty fit: does it match the lesson's goal and the course's stated \
   audience, not assuming knowledge that hasn't been taught yet?
3. Activity relevance: does each interactive activity actually test the \
   lesson's specific goal, rather than something generic or unrelated?
4. Answerability: does each activity have exactly one defensible answer \
   that a learner can find in this lesson? An activity a reasonable learner \
   could answer differently, and still be right, fails this.

Score 1-5. Pass only if genuinely usable as-is. Be specific: quote the \
problem passage or activity and say exactly what's wrong."""


def lesson_content_evaluate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    language: CodeLanguage,
    content: LessonContent,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    lesson = outline.lessons[lesson_index]
    context = (
        f"{LESSON_CONTENT_EVAL_SYSTEM}\n\n"
        f"Course programming language: {LANGUAGE_NAMES[language]}\n"
        f"Course audience: {overview.audience}\n\n"
        f"{render_unit_outline(unit, outline)}"
    )
    system = cached_system_message(context, provider=provider)
    human = (
        f'Lesson: "{lesson.title}" - {lesson.goal}\n\n'
        f"{content.model_dump_json(indent=2)}"
    )
    return [system, HumanMessage(content=human)]


# --- Activity solver -----------

SOLVER_SYSTEM = """You are a careful learner taking a short quiz. You are \
given one lesson and its activities. The answer key is not shown to you.

For each activity, answer it using only the lesson, then say whether \
another answer would be equally correct.

Answer format:
- multipleChoice: write the exact text of the option you choose.
- fillBlank: write the answers for the blanks in order, separated by ' | '.

Set other_defensible_answer only when a different answer is just as \
correct as yours, for example when the text does not say which value \
belongs in a blank, or when two options are both true. Write that other \
answer in the same format. Leave it empty when the lesson forces one \
answer."""


def solver_prompt(
    *, written_lesson_markdown: str, activities_text: str
) -> list[BaseMessage]:
    human = f"Lesson:\n\n{written_lesson_markdown}\n\nActivities:\n\n{activities_text}"
    return [SystemMessage(content=SOLVER_SYSTEM), HumanMessage(content=human)]
