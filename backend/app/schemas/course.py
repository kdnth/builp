from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Field names below match the course JSON contract shared with the frontend
# (frontend/src/schemas/course.ts) exactly, camelCase included, so the two
# schemas stay easy to compare side by side. The backend is the source of
# truth: it never trusts the frontend's own validation.


class TestCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    input: list[Any]
    expectedOutput: Any


class WrittenLesson(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    markdown: str


class FunctionCodePractice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["function"]
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    functionSignature: str = Field(min_length=1)
    description: str
    testSuite: list[TestCase] = Field(min_length=1)


class ComponentCodePractice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["component"]
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    starterFiles: dict[str, str]
    dependencies: dict[str, str]


CodePractice = Annotated[
    FunctionCodePractice | ComponentCodePractice,
    Field(discriminator="type"),
]


class MatchingPair(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class MatchingActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["matching"]
    id: str = Field(min_length=1)
    description: str | None = None
    pairs: list[MatchingPair] = Field(min_length=1)


class Blank(BaseModel):
    model_config = ConfigDict(extra="ignore")

    position: int = Field(ge=0)
    accepted: list[str] = Field(min_length=1)


class FillBlankActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["fillBlank"]
    id: str = Field(min_length=1)
    description: str | None = None
    text: str = Field(min_length=1)
    blanks: list[Blank] = Field(min_length=1)


class MultipleChoiceActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["multipleChoice"]
    id: str = Field(min_length=1)
    description: str | None = None
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2)
    correctIndex: int = Field(ge=0)


InteractiveActivity = Annotated[
    MatchingActivity | FillBlankActivity | MultipleChoiceActivity,
    Field(discriminator="type"),
]


class InteractivePractice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    activities: list[InteractiveActivity] = Field(min_length=1)


class Lesson(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    writtenLesson: WrittenLesson
    codePractices: list[CodePractice]
    interactivePractices: list[InteractivePractice]


class Unit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    lessons: list[Lesson] = Field(min_length=1)


class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    units: list[Unit] = Field(min_length=1)


class CourseSummary(BaseModel):
    id: str
    title: str
    unit_count: int
    lesson_count: int


def summarize(course: Course) -> CourseSummary:
    lesson_count = sum(len(unit.lessons) for unit in course.units)
    return CourseSummary(
        id=course.id,
        title=course.title,
        unit_count=len(course.units),
        lesson_count=lesson_count,
    )
