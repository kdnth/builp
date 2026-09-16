"""Builders for agent objects used across tests."""

from app.agent.schemas import (
    CourseBrief,
    CourseOverview,
    LessonProfile,
    LessonSummary,
    UnitOutline,
    UnitSummary,
)


def make_brief(**overrides) -> CourseBrief:
    values = {
        "domain": "Testing",
        "lesson_profiles": ["programming", "conceptual"],
        "learning_objectives": ["Write a test", "Run a test", "Read a failure"],
        "prerequisites": [],
        "glossary": [{"term": "test", "definition": "a check that code works"}],
        "misconceptions": [],
        "conventions": "",
        "sensitivity": "none",
        "code_practice_policy": "javascript",
    }
    values.update(overrides)
    return CourseBrief(**values)


def make_overview(*, num_units: int = 1, **overrides) -> CourseOverview:
    values = {
        "title": "Course",
        "description": "A course.",
        "audience": "Everyone.",
        "units": [
            UnitSummary(title=f"Unit {index + 1}", goal="Goal.")
            for index in range(num_units)
        ],
        "brief": make_brief(),
    }
    values.update(overrides)
    return CourseOverview(**values)


def make_lesson_summary(
    *,
    title: str = "Lesson",
    profile: LessonProfile = "programming",
    include_code_practice: bool = False,
    activity_types: list[str] | None = None,
) -> LessonSummary:
    return LessonSummary(
        title=title,
        goal="Learn a thing.",
        profile=profile,
        include_code_practice=include_code_practice,
        interactive_activity_types=activity_types or [],
    )


def make_outline(*, num_lessons: int = 1, **kwargs) -> UnitOutline:
    return UnitOutline(
        lessons=[
            make_lesson_summary(title=f"Lesson {index + 1}", **kwargs)
            for index in range(num_lessons)
        ]
    )
