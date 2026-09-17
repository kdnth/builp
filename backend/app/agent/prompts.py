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
from app.agent.schemas import (
    CodePracticePolicy,
    CourseBrief,
    CourseOverview,
    LessonContent,
    LessonProfile,
    UnitOutline,
    UnitSummary,
)
from app.schemas.course import CodeLanguage, CourseType
from app.schemas.generation import CodePracticeChoice, LearnerLevel, ReadingStyle

LANGUAGE_NAMES: dict[str, str] = {
    "javascript": "JavaScript",
    "python": "Python",
}

PROFILE_GUIDANCE: dict[LessonProfile, str] = {
    "conceptual": "This is a concept lesson. Define each term precisely, "
    "contrast it with the idea it is most often confused with, and give one "
    "example and one non-example. A categorize activity suits it well.",
    "procedural": "This is a procedure lesson. Give the steps in order, say "
    "when each step applies, and call out the step learners skip most often. "
    "An ordering activity suits it well.",
    "quantitative": "This is a quantitative lesson. State each formula "
    "plainly, then work one full example step by step with units on every "
    "line. Keep the numbers small enough to check by hand. A numeric "
    "activity suits it well.",
    "narrative": "This is a narrative lesson. Give dates, the people or "
    "groups involved, and cause and effect. Where historians disagree, say "
    "that it is contested instead of picking one side. An ordering activity "
    "on a timeline suits it well.",
    "language": "This is a language lesson. Show the target language with "
    "its translation, keep sentences short, and mark gender, accents, and "
    "register where they matter.",
    "programming": "This is a programming lesson. Show short runnable "
    "examples and explain what each line does.",
}

READING_STYLE_PLAN: dict[ReadingStyle, str] = {
    "single": "Write the lesson as one section that holds the whole "
    "explanation, and put every activity in that one section. The learner "
    "reads it all, then practices. Up to 8 activities.",
    "interleaved": "Split the lesson into 2 to 4 sections, each with its own "
    "short heading. After a section that introduces something worth "
    "checking, add 1 or 2 activities that test that section only, not the "
    "whole lesson. The last section ends the lesson, and may end with a "
    "longer set of activities that reviews the whole lesson.",
}

PROFILE_REVIEW_CRITERIA: dict[LessonProfile, str] = {
    "conceptual": "definitions are precise, and the contrast with nearby "
    "ideas is correct",
    "procedural": "the steps are in the right order, complete, and safe to follow",
    "quantitative": "every worked example is correct step by step, and units "
    "are consistent",
    "narrative": "dates, names, and cause and effect are correct, and "
    "contested views are named as contested",
    "language": "the target language is correct, and it matches the dialect "
    "and register the course states",
    "programming": "code examples run as described",
}


def _course_type_label(course_type: CourseType) -> str:
    return "programming" if course_type == "programming" else "general subject"


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


def render_brief(brief: CourseBrief) -> str:
    lines = [
        f"Domain: {brief.domain}",
        "Objectives:",
        *[f"- {objective}" for objective in brief.learning_objectives],
    ]
    if brief.prerequisites:
        lines += ["Assumed knowledge:", *[f"- {item}" for item in brief.prerequisites]]
    if brief.glossary:
        lines += [
            "Glossary, use these words with these meanings:",
            *[f"- {term.term}: {term.definition}" for term in brief.glossary],
        ]
    if brief.misconceptions:
        lines += [
            "Common misconceptions, good material for wrong options:",
            *[f"- {item}" for item in brief.misconceptions],
        ]
    if brief.conventions:
        lines.append(f"Conventions: {brief.conventions}")
    if brief.sensitivity != "none":
        lines.append(
            f"This subject touches {brief.sensitivity} decisions. Teach the "
            "general subject. Never give advice for one person's own case."
        )
    return "\n".join(lines)


def render_course_map(
    overview: CourseOverview,
    outlines: list[tuple[UnitSummary, UnitOutline]],
    *,
    current: tuple[int, int] | None = None,
) -> str:
    """Every unit with its lessons, so a lesson knows what the others teach."""
    lines = ["Course map:"]
    for unit_index, (unit, outline) in enumerate(outlines, start=1):
        lines.append(f"Unit {unit_index}: {unit.title} - {unit.goal}")
        for lesson_index, lesson in enumerate(outline.lessons, start=1):
            marker = (
                "  <- you are writing this lesson"
                if current == (unit_index, lesson_index)
                else ""
            )
            lines.append(
                f"  {unit_index}.{lesson_index} {lesson.title} - {lesson.goal}{marker}"
            )
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

OVERVIEW_SYSTEM = """You design course curricula for any teachable \
subject. Given a topic and audience, you produce a course overview: a \
title, a short learner-facing description, an audience statement, an \
ordered list of units that build on each other logically, and a brief that \
every later writing step will follow. Do not write lesson-level detail \
yet, only unit-level scope.

The brief matters as much as the units. Lessons are written in parallel by \
writers who see the brief but not each other's work, so the brief is what \
keeps their terms, depth, and conventions the same. Write objectives the \
learner can be observed doing, a glossary of the words this course uses, \
and the wrong beliefs learners actually hold about this topic."""


def _code_practice_instruction(
    course_type: CourseType, language: CodePracticeChoice
) -> str:
    if language in ("javascript", "python"):
        return (
            "Code practice: set code_practice_policy to "
            f"'{language}'. Lessons may include runnable {LANGUAGE_NAMES[language]} "
            "exercises."
        )
    if language == "none":
        return (
            "Code practice: set code_practice_policy to 'none'. This course "
            "has no runnable code."
        )
    return (
        "Code practice: you decide. Set code_practice_policy to 'python' or "
        "'javascript' only when writing code would genuinely help learners of "
        "this subject, for example statistics or data work. Otherwise set it "
        "to 'none'."
    )


def overview_generate_prompt(
    *,
    topic: str,
    audience: str,
    num_units: int,
    course_type: CourseType,
    language: CodePracticeChoice,
    level: LearnerLevel,
    learning_goals: str | None,
    notes: str | None,
    feedback: str | None,
) -> list[BaseMessage]:
    lines = [
        f"Topic: {topic}",
        f"Audience: {audience}",
        f"Level: {level}",
        f"Course type: {_course_type_label(course_type)}",
        _code_practice_instruction(course_type, language),
    ]
    if learning_goals:
        lines.append(f"What the learner wants to be able to do: {learning_goals}")
    if notes:
        lines.append(f"Requests from the learner, follow them: {notes}")
    lines.append(f"Number of units: exactly {num_units}. Not fewer, not more.")
    lines.append("Produce the course overview and the brief.")
    human = "\n".join(lines) + _feedback_block(feedback)
    return [SystemMessage(content=OVERVIEW_SYSTEM), HumanMessage(content=human)]


OVERVIEW_EVAL_SYSTEM = """You are a strict curriculum reviewer. You judge a \
generated course overview against five criteria:

1. Topic coverage: do the units, together, actually cover the stated topic \
   at a reasonable depth for the stated audience?
2. Scope: is each unit an appropriately sized chunk, not too broad or too \
   narrow, and not overlapping with another unit?
3. Logical progression: does each unit build on knowledge from the units \
   before it, in a sensible order?
4. Objectives: is each learning objective something the learner can be \
   observed doing, rather than "understand X"?
5. Brief quality: is the glossary correct and free of invented terms, and \
   are the misconceptions ones learners really hold?

Score 1-5. Pass only if the overview is genuinely usable as-is; a 3 should \
still fail. Be specific in feedback: name the unit and the exact problem."""


def overview_evaluate_prompt(overview: CourseOverview) -> list[BaseMessage]:
    return [
        SystemMessage(content=OVERVIEW_EVAL_SYSTEM),
        HumanMessage(content=render_overview(overview)),
    ]


# --- Stage 2: unit outline (one call per unit) ---------------------------

UNIT_OUTLINE_SYSTEM = """You write the lesson-level outline for one unit of \
a course. You are given the course overview and its brief for context. \
Produce an ordered list of lessons for just this one unit. Each lesson \
needs a title, a one-sentence goal (what the learner can do afterward), a \
profile from the brief's lesson_profiles, whether it should include a \
runnable code practice, and which interactive activity types (if any) fit \
it. Not every lesson needs every activity type; use judgment."""


def unit_outline_generate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    lessons_per_unit: int,
    feedback: str | None,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    system = cached_system_message(
        f"{UNIT_OUTLINE_SYSTEM}\n\n{render_overview(overview)}\n\n"
        f"{render_brief(overview.brief)}",
        provider=provider,
    )
    policy = overview.brief.code_practice_policy
    code_line = (
        "This course has no code practice, so include_code_practice is always false."
        if policy == "none"
        else f"Code practices use {LANGUAGE_NAMES[policy]}. Use them only for "
        "lessons where writing code is the best way to practice."
    )
    human = (
        f'Write the outline for this unit: "{unit.title}" - {unit.goal}\n'
        f"{code_line}\n"
        "Every lesson's profile must be one of: "
        f"{', '.join(overview.brief.lesson_profiles)}.\n"
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
lesson: the written explanation in markdown sections, an optional runnable \
code practice, and interactive activities that check understanding of the \
lesson's goal. Write code examples in {language}.

{reading_plan}

{profile_guidance}

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
option the longest one, and do not repeat the question's wording in it. \
Use `passage` when the question needs a case, a quote, or a small data \
table to reason about. Use `option_explanations` to say why each option is \
right or wrong, one for every option or none at all.

For an ordering activity: only use it when one order is truly correct, and \
say what decides it in `basis` (for example 'chronological' or 'process \
steps'). Never order things by preference or importance. List `items` in \
the correct order; the learner sees them shuffled.

For a categorize activity: every item belongs in exactly one category, and \
every category gets at least one item. An item that could sit in two \
categories is wrong.

For a numeric activity: the question must contain every number needed. \
Write `answer_expression` as a Python expression that computes the answer \
from those numbers, using only arithmetic and the math module. The server \
runs it and compares it with `answer`. Set `tolerance` when the answer is \
rounded, and name the `unit` when it has one.

Write an `explanation` for every activity: one or two sentences telling \
the learner why the answer is right. The learner reads it after they \
answer, so it should teach, not just repeat the answer.

Match the difficulty to the lesson goal and the course's stated audience. \
Every activity should actually test the lesson's specific goal, not \
generic trivia."""


def lesson_content_system(
    *,
    profile: LessonProfile,
    code_language: CodePracticePolicy,
    reading_style: ReadingStyle,
) -> str:
    """The shared core prompt plus the modules this lesson needs."""
    if code_language == "none":
        code_practice_rules = (
            "This lesson has no code practice. Do not write code_practice."
        )
        example_language = "the language the lesson is about, when it shows code"
    else:
        code_practice_rules = _CODE_PRACTICE_RULES[code_language]
        example_language = LANGUAGE_NAMES[code_language]
    return _LESSON_CONTENT_SYSTEM_TEMPLATE.format(
        language=example_language,
        code_practice_rules=code_practice_rules,
        profile_guidance=PROFILE_GUIDANCE[profile],
        reading_plan=READING_STYLE_PLAN[reading_style],
    )


def lesson_content_generate_prompt(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    course_map: str,
    reading_style: ReadingStyle,
    feedback: str | None,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    lesson = outline.lessons[lesson_index]
    code_language: CodePracticePolicy = (
        overview.brief.code_practice_policy if lesson.include_code_practice else "none"
    )
    system_prompt = lesson_content_system(
        profile=lesson.profile,
        code_language=code_language,
        reading_style=reading_style,
    )
    context = (
        f"{system_prompt}"
        f"\n\nCourse audience: {overview.audience}\n\n"
        f"{render_brief(overview.brief)}\n\n{course_map}"
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
    content: LessonContent,
    provider: SupportedProvider,
) -> list[BaseMessage]:
    lesson = outline.lessons[lesson_index]
    policy = overview.brief.code_practice_policy
    code_line = (
        "This course has no code practice.\n"
        if policy == "none"
        else f"Code practices are written in {LANGUAGE_NAMES[policy]}.\n"
    )
    profile_criteria = PROFILE_REVIEW_CRITERIA[lesson.profile]
    context = (
        f"{LESSON_CONTENT_EVAL_SYSTEM}\n"
        f"For this lesson, also check that {profile_criteria}.\n\n"
        f"{code_line}"
        f"Course audience: {overview.audience}\n\n"
        f"{render_brief(overview.brief)}\n\n"
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


# --- Screening (one fast call before any other work) ----------------------

SCREENING_SYSTEM = """You decide whether a learning platform can generate a \
course on a requested topic. Studying a subject is not the same as doing \
harm with it, so judge the request, not the subject area.

Allow:
- Academic, historical, and scientific study of any subject, including hard \
  ones such as warfare, drugs and their pharmacology, extremism as a \
  subject of study, or the law.
- General professional subjects taught as knowledge: medicine, law, \
  personal finance, nutrition, safety.
- Security topics taught for defense, including how attacks work.

Refuse:
- operational_harm: instructions whose main use is causing harm, such as \
  building weapons or explosives, synthesizing illegal drugs, writing \
  malware, or breaking into systems that are not the learner's.
- individual_medical_advice, individual_legal_advice, \
  individual_financial_advice: the request asks for advice on one person's \
  own case ("what dose should I take", "how do I win my case", "which \
  stocks should I buy") rather than teaching the subject.
- sexual_content: sexual or erotic material.
- hate_or_harassment: content that attacks or demeans a group or a person.

When you refuse, write one clear sentence for the learner. Say what cannot \
be generated and, when a close topic is fine, say so. Do not lecture."""


def screening_prompt(
    *,
    topic: str,
    audience: str,
    learning_goals: str | None,
    notes: str | None,
) -> list[BaseMessage]:
    lines = [f"Topic: {topic}", f"Audience: {audience}"]
    if learning_goals:
        lines.append(f"Learning goals: {learning_goals}")
    if notes:
        lines.append(f"Notes: {notes}")
    return [
        SystemMessage(content=SCREENING_SYSTEM),
        HumanMessage(content="\n".join(lines)),
    ]
