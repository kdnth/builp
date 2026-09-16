"""add course type and user context to generation jobs

Revision ID: d8a3c1b5e7f9
Revises: c5f1a9b3d7e2
Create Date: 2026-09-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3c1b5e7f9'
down_revision: Union[str, Sequence[str], None] = 'c5f1a9b3d7e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ADDED = (
    ("course_type", sa.String(), False, "programming"),
    ("learning_goals", sa.String(), True, None),
    ("level", sa.String(), False, "beginner"),
    ("notes", sa.String(), True, None),
    ("reading_style", sa.String(), False, "single"),
    ("refusal_category", sa.String(), True, None),
    ("refusal_reason", sa.String(), True, None),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, column_type, nullable, default in _ADDED:
        op.add_column(
            "generation_jobs",
            sa.Column(name, column_type, nullable=nullable, server_default=default),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for name, _, _, _ in reversed(_ADDED):
        op.drop_column("generation_jobs", name)
