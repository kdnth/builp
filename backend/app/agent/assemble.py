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


def assemble_lesson(title: str, content: gen.LessonContent) -> course_schema.Lesson:
    written_lesson = course_schema.WrittenLesson(
        id=_new_id(), title=title, markdown=content.written_lesson_markdown
    )

    code_practices: list[course_schema.FunctionCodePractice] = []
    if content.code_practice is not None:
        cp = content.code_practice
        code_practices.append(
            course_schema.FunctionCodePractice(
                type="function",
                id=_new_id(),
                title=cp.title,
                functionSignature=cp.function_signature,
                description=cp.description,
                testSuite=[
                    course_schema.TestCase(
                        input=tc.input, expectedOutput=tc.expected_output
                    )
                    for tc in cp.test_suite
                ],
            )
        )

    activities: list[
        course_schema.MatchingActivity
        | course_schema.FillBlankActivity
        | course_schema.MultipleChoiceActivity
    ] = []
    for activity in content.interactive_activities:
        if isinstance(activity, gen.GeneratedMatchingActivity):
            activities.append(
                course_schema.MatchingActivity(
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
            )
        elif isinstance(activity, gen.GeneratedFillBlankActivity):
            activities.append(
                course_schema.FillBlankActivity(
                    type="fillBlank",
                    id=_new_id(),
                    description=activity.description,
                    text=activity.text,
                    blanks=[
                        course_schema.Blank(position=index, accepted=blank.accepted)
                        for index, blank in enumerate(activity.blanks)
                    ],
                )
            )
        elif isinstance(activity, gen.GeneratedMultipleChoiceActivity):
            activities.append(
                course_schema.MultipleChoiceActivity(
                    type="multipleChoice",
                    id=_new_id(),
                    description=activity.description,
                    question=activity.question,
                    options=activity.options,
                    correctIndex=activity.correct_index,
                )
            )

    interactive_practices = (
        [
            course_schema.InteractivePractice(
                id=_new_id(), title=f"{title} Practice", activities=activities
            )
        ]
        if activities
        else []
    )

    return course_schema.Lesson(
        id=_new_id(),
        title=title,
        writtenLesson=written_lesson,
        codePractices=code_practices,
        interactivePractices=interactive_practices,
    )


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
