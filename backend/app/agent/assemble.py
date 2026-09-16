"""Turn generated stage output into the real Course shape.

The model produces content; code assigns identity. Ids, and blank
positions, are bookkeeping the model has no reason to get right, so they're
assigned here, after generation, not asked for in the schemas in
app/agent/schemas.py.
"""

import uuid

from app.agent import schemas as gen
from app.schemas import course as course_schema


def _new_id() -> str:
    return str(uuid.uuid4())


CourseActivity = (
    course_schema.MatchingActivity
    | course_schema.FillBlankActivity
    | course_schema.MultipleChoiceActivity
)


def _assemble_activity(activity: gen.GeneratedActivity) -> CourseActivity:
    if isinstance(activity, gen.GeneratedMatchingActivity):
        return course_schema.MatchingActivity(
            type="matching",
            id=_new_id(),
            description=activity.description,
            pairs=[
                course_schema.MatchingPair(
                    id=_new_id(), term=pair.term, definition=pair.definition
                )
                for pair in activity.pairs
            ],
        )
    if isinstance(activity, gen.GeneratedFillBlankActivity):
        return course_schema.FillBlankActivity(
            type="fillBlank",
            id=_new_id(),
            description=activity.description,
            text=activity.text,
            blanks=[
                course_schema.Blank(position=index, accepted=blank.accepted)
                for index, blank in enumerate(activity.blanks)
            ],
        )
    return course_schema.MultipleChoiceActivity(
        type="multipleChoice",
        id=_new_id(),
        description=activity.description,
        question=activity.question,
        options=activity.options,
        correctIndex=activity.correct_index,
    )


def _assemble_code_practice(
    practice: gen.GeneratedFunctionPractice, language: course_schema.CodeLanguage
) -> course_schema.FunctionCodePractice:
    return course_schema.FunctionCodePractice(
        type="function",
        id=_new_id(),
        title=practice.title,
        language=language,
        functionSignature=practice.function_signature,
        description=practice.description,
        testSuite=[
            course_schema.TestCase(input=tc.input, expectedOutput=tc.expected_output)
            for tc in practice.test_suite
        ],
    )


def assemble_lesson(
    title: str,
    content: gen.LessonContent,
    language: course_schema.CodeLanguage,
) -> course_schema.Lesson:
    """One page for each written section, a check page after a section that
    has activities, and the code practice after the last section."""
    pages: list[course_schema.LessonPage] = []

    for index, section in enumerate(content.sections):
        pages.append(
            course_schema.WrittenPage(
                kind="written",
                written=course_schema.WrittenLesson(
                    id=_new_id(), title=section.title, markdown=section.markdown
                ),
            )
        )

        is_last_section = index == len(content.sections) - 1
        if is_last_section and content.code_practice is not None:
            pages.append(
                course_schema.CodePage(
                    kind="code",
                    practice=_assemble_code_practice(content.code_practice, language),
                )
            )

        if section.activities:
            pages.append(
                course_schema.InteractivePage(
                    kind="interactive",
                    practice=course_schema.InteractivePractice(
                        id=_new_id(),
                        title=f"{section.title} check",
                        activities=[
                            _assemble_activity(activity)
                            for activity in section.activities
                        ],
                    ),
                )
            )

    return course_schema.Lesson(id=_new_id(), title=title, pages=pages)


def assemble_course(
    overview: gen.CourseOverview,
    unit_lessons: list[list[course_schema.Lesson]],
) -> course_schema.Course:
    """`unit_lessons[i]` are the assembled lessons for `overview.units[i]`,
    in the same order."""
    units = [
        course_schema.Unit(id=_new_id(), title=unit_summary.title, lessons=lessons)
        for unit_summary, lessons in zip(overview.units, unit_lessons, strict=True)
    ]
    return course_schema.Course(id=_new_id(), title=overview.title, units=units)
