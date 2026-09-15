"""Structured output shapes for each generation stage.

These are what the LLM is forced to produce (via with_structured_output),
not the final Course JSON shape. Ids, positions, and other bookkeeping the
model has no reason to get right are assigned by code after generation, in
app/agent/assemble.py.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, JsonValue, WithJsonSchema


def _parse_json_encoded_value(value: object) -> object:
    """Accept native JSON values or JSON-encoded strings.

    OpenAI's structured-output validator requires every schema node to have a
    `type`. Pydantic's JsonValue emits `{}` / a typeless `$ref`, which OpenAI
    rejects. The LLM-facing schema is therefore `type: string`; this
    validator turns those strings back into JSON values for the rest of the
    pipeline. Native Python values (used by tests and non-OpenAI paths)
    pass through unchanged.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


# LLM schema: a JSON string. Python type: any JSON value.
JsonEncodedValue = Annotated[
    JsonValue,
    BeforeValidator(_parse_json_encoded_value),
    WithJsonSchema(
        {
            "type": "string",
            "description": (
                "JSON-encoded value. Examples: '3', '\"hello\"', 'true', "
                "'null', '[1, 2]', '{\"a\": 1}'."
            ),
        }
    ),
]

# --- Stage 1: course overview -----------------------------------------


class UnitSummary(BaseModel):
    title: str
    goal: str = Field(
        description="What this unit covers, and why it comes at this point "
        "in the course."
    )


class CourseOverview(BaseModel):
    title: str
    description: str = Field(description="A short, learner-facing course summary.")
    audience: str = Field(
        description="Who this course is for, and what (if anything) they "
        "should already know."
    )
    units: list[UnitSummary] = Field(
        description="Ordered list of units, in the order a learner should take them.",
        min_length=1,
    )


# --- Stage 2: unit outline (one call per unit) -------------------------


class LessonSummary(BaseModel):
    title: str
    goal: str = Field(
        description="What the learner should be able to do after this lesson."
    )
    include_code_practice: bool = Field(
        description="Whether this lesson should include a runnable code exercise."
    )
    interactive_activity_types: list[
        Literal["matching", "fillBlank", "multipleChoice"]
    ] = Field(
        description="Which interactive activity types this lesson should "
        "include, in the order they should appear. Can be empty."
    )


class UnitOutline(BaseModel):
    lessons: list[LessonSummary] = Field(min_length=1)


# --- Stage 3: lesson content (one call per lesson) ----------------------


class GeneratedTestCase(BaseModel):
    input: list[JsonEncodedValue] = Field(
        description="Function arguments, each JSON-encoded as a string. "
        "Examples: '1', '\"hello\"', 'true', '[1, 2]'."
    )
    expected_output: JsonEncodedValue = Field(
        description="JSON-encoded expected return value from calling the "
        "reference solution with `input`. Examples: '3', 'true', "
        "'\"ok\"', '[1, 2]'."
    )


class GeneratedFunctionPractice(BaseModel):
    type: Literal["function"] = "function"
    title: str
    function_signature: str = Field(
        description="e.g. 'add(a, b)', 'isPalindrome(s)', or 'is_palindrome(s)'."
    )
    description: str = Field(description="Instructions shown to the learner.")
    reference_solution: str = Field(
        description="A complete, correct function in the course's programming "
        "language that implements function_signature. Used only to check the "
        "test suite is internally consistent. Never shown to the learner."
    )
    test_suite: list[GeneratedTestCase] = Field(min_length=2)


class GeneratedMatchingPair(BaseModel):
    term: str
    definition: str


class GeneratedMatchingActivity(BaseModel):
    type: Literal["matching"] = "matching"
    description: str | None = None
    pairs: list[GeneratedMatchingPair] = Field(min_length=3)


class GeneratedBlank(BaseModel):
    accepted: list[str] = Field(
        min_length=1,
        description="Acceptable answers for this blank, most likely first.",
    )


class GeneratedFillBlankActivity(BaseModel):
    type: Literal["fillBlank"] = "fillBlank"
    description: str | None = None
    text: str = Field(
        description="The passage with each blank written as {{blank}}, in "
        "order. The number of {{blank}} tokens must equal the number of "
        "entries in `blanks`."
    )
    blanks: list[GeneratedBlank] = Field(min_length=1)


class GeneratedMultipleChoiceActivity(BaseModel):
    type: Literal["multipleChoice"] = "multipleChoice"
    description: str | None = None
    question: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(
        description="Index into `options` of the correct answer."
    )


GeneratedActivity = Annotated[
    GeneratedMatchingActivity
    | GeneratedFillBlankActivity
    | GeneratedMultipleChoiceActivity,
    Field(discriminator="type"),
]


class LessonContent(BaseModel):
    written_lesson_markdown: str = Field(
        description="The full written lesson, in markdown."
    )
    code_practice: GeneratedFunctionPractice | None = Field(
        default=None,
        description="A runnable code exercise for this lesson, if the "
        "lesson calls for one.",
    )
    interactive_activities: list[GeneratedActivity] = Field(
        description="1 to 3 interactive check-for-understanding activities.",
        max_length=3,
    )


# --- Evaluation (shared shape across all three stages) ------------------


class EvaluationResult(BaseModel):
    passed: bool
    score: int = Field(ge=1, le=5)
    feedback: str = Field(
        description="Specific and actionable. If passed, briefly say what's "
        "good. If not, say exactly what to fix."
    )
