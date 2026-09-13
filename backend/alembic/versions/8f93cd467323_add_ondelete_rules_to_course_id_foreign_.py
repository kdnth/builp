"""add ondelete rules to course_id foreign keys

Revision ID: 8f93cd467323
Revises: ed5b1f61fd31
Create Date: 2026-09-13 14:22:22.233554

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8f93cd467323'
down_revision: Union[str, Sequence[str], None] = 'ed5b1f61fd31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # lesson_progress rows outlive nothing once their course is gone -
    # nothing reads progress for a deleted course - so delete them with it.
    op.drop_constraint(
        "lesson_progress_course_id_fkey", "lesson_progress", type_="foreignkey"
    )
    op.create_foreign_key(
        "lesson_progress_course_id_fkey",
        "lesson_progress",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # generation_jobs rows back the free-credit rate limit and must survive
    # the course being deleted, so only detach the now-dangling link.
    op.drop_constraint(
        "generation_jobs_course_id_fkey", "generation_jobs", type_="foreignkey"
    )
    op.create_foreign_key(
        "generation_jobs_course_id_fkey",
        "generation_jobs",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "generation_jobs_course_id_fkey", "generation_jobs", type_="foreignkey"
    )
    op.create_foreign_key(
        "generation_jobs_course_id_fkey",
        "generation_jobs",
        "courses",
        ["course_id"],
        ["id"],
    )

    op.drop_constraint(
        "lesson_progress_course_id_fkey", "lesson_progress", type_="foreignkey"
    )
    op.create_foreign_key(
        "lesson_progress_course_id_fkey",
        "lesson_progress",
        "courses",
        ["course_id"],
        ["id"],
    )
