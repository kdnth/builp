"""create saved_courses table

Revision ID: 6c1e4a9f2b7d
Revises: 3a7d9c2e1f4b
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c1e4a9f2b7d'
down_revision: Union[str, Sequence[str], None] = '3a7d9c2e1f4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "saved_courses",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "course_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("saved_courses")
