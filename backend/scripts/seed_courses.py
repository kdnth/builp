"""Load the bundled frontend course fixtures into the database.

Run with: uv run python scripts/seed_courses.py
"""

import json
from pathlib import Path

from app.database import SessionLocal
from app.models import Course as CourseModel
from app.schemas.course import Course

FRONTEND_COURSES_DIR = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "courses"
)


def seed() -> None:
    db = SessionLocal()
    try:
        for path in sorted(FRONTEND_COURSES_DIR.glob("*.json")):
            data = json.loads(path.read_text())
            course = Course.model_validate(data)

            if db.get(CourseModel, course.id) is not None:
                print(f"skip (already exists): {course.id} {course.title}")
                continue

            db.add(
                CourseModel(
                    id=course.id,
                    title=course.title,
                    data=course.model_dump(mode="json"),
                    owner_user_id=None,
                )
            )
            db.commit()
            print(f"seeded: {course.id} {course.title}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
