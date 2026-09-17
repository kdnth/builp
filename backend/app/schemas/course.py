from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Field names below match the course JSON contract shared with the frontend
# (frontend/src/schemas/course.ts) exactly, camelCase included, so the two
# schemas stay easy to compare side by side. The backend is the source of
# truth: it never trusts the frontend's own validation.

CodeLanguage = Literal["javascript", "python"]
CourseType = Literal["programming", "general"]


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
    language: CodeLanguage = "javascript"
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
    explanation: str | None = None
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
    explanation: str | None = None
    text: str = Field(min_length=1)
    blanks: list[Blank] = Field(min_length=1)


class MultipleChoiceActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["multipleChoice"]
    id: str = Field(min_length=1)
    description: str | None = None
    explanation: str | None = None
    passage: str | None = Field(
        default=None, description="Markdown shown above the question."
    )
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2)
    optionExplanations: list[str] | None = None
    correctIndex: int = Field(ge=0)


class OrderingActivity(BaseModel):
    """`items` are stored in the correct order. The viewer shuffles them."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["ordering"]
    id: str = Field(min_length=1)
    description: str | None = None
    explanation: str | None = None
    basis: str = Field(
        min_length=1, description="What the order follows, e.g. 'chronological'."
    )
    items: list[str] = Field(min_length=3, max_length=8)


class CategorizeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)


class CategorizeActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["categorize"]
    id: str = Field(min_length=1)
    description: str | None = None
    explanation: str | None = None
    categories: list[str] = Field(min_length=2, max_length=4)
    items: list[CategorizeItem] = Field(min_length=3, max_length=8)


class NumericActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["numeric"]
    id: str = Field(min_length=1)
    description: str | None = None
    explanation: str | None = None
    question: str = Field(min_length=1)
    answer: float
    tolerance: float = Field(default=0, ge=0)
    unit: str | None = None


InteractiveActivity = Annotated[
    MatchingActivity
    | FillBlankActivity
    | MultipleChoiceActivity
    | OrderingActivity
    | CategorizeActivity
    | NumericActivity,
    Field(discriminator="type"),
]


class InteractivePractice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    activities: list[InteractiveActivity] = Field(min_length=1)


class WrittenPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["written"]
    written: WrittenLesson


class CodePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["code"]
    practice: CodePractice


class InteractivePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["interactive"]
    practice: InteractivePractice


LessonPage = Annotated[
    WrittenPage | CodePage | InteractivePage,
    Field(discriminator="kind"),
]


class Lesson(BaseModel):
    """A lesson is an ordered list of pages. Courses written before pages
    existed carry `writtenLesson` and the two practice lists instead, and
    `lesson_pages` turns either shape into the same list."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    pages: list[LessonPage] | None = None
    writtenLesson: WrittenLesson | None = None
    codePractices: list[CodePractice] = []
    interactivePractices: list[InteractivePractice] = []

    @model_validator(mode="after")
    def _has_content(self) -> "Lesson":
        if self.pages is not None:
            if not self.pages:
                raise ValueError("pages cannot be empty")
        elif self.writtenLesson is None:
            raise ValueError("a lesson needs pages, or a writtenLesson")
        return self


class Unit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    lessons: list[Lesson] = Field(min_length=1)


class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    courseType: CourseType = "programming"
    units: list[Unit] = Field(min_length=1)
    forkedFromId: str | None = None


class CourseSummary(BaseModel):
    id: str
    title: str
    course_type: CourseType = "programming"
    unit_count: int
    lesson_count: int
    tags: list[str] = []
    owner_user_id: str | None = None
    saved: bool = False


class PaginatedCourses(BaseModel):
    items: list[CourseSummary]
    total: int


class CourseDetail(Course):
    """Course content plus the DB-side metadata that was never part of the
    JSON contract: tags and authorship. Kept separate from Course itself so
    the upload/generation path (which only ever produces course content)
    doesn't need to know these fields exist."""

    tags: list[str] = []
    owner_user_id: str | None = None
    saved: bool = False


class UpdateTagsRequest(BaseModel):
    tags: list[str]


def summarize(
    course: Course,
    *,
    tags: list[str],
    owner_user_id: str | None,
    saved: bool = False,
) -> CourseSummary:
    lesson_count = sum(len(unit.lessons) for unit in course.units)
    return CourseSummary(
        id=course.id,
        title=course.title,
        course_type=course.courseType,
        unit_count=len(course.units),
        lesson_count=lesson_count,
        tags=tags,
        owner_user_id=owner_user_id,
        saved=saved,
    )


def lesson_pages(lesson: Lesson) -> list[LessonPage]:
    """The pages of a lesson, in order, whichever shape it was written in."""
    if lesson.pages:
        return lesson.pages

    pages: list[LessonPage] = []
    if lesson.writtenLesson is not None:
        pages.append(WrittenPage(kind="written", written=lesson.writtenLesson))
    pages += [
        CodePage(kind="code", practice=practice) for practice in lesson.codePractices
    ]
    pages += [
        InteractivePage(kind="interactive", practice=practice)
        for practice in lesson.interactivePractices
    ]
    return pages
