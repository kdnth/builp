"""add course type to courses

Revision ID: e1c7b4d9a206
Revises: d8a3c1b5e7f9
Create Date: 2026-09-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1c7b4d9a206'
down_revision: Union[str, Sequence[str], None] = 'd8a3c1b5e7f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Every stored course today is a programming course.
    op.add_column(
        "courses",
        sa.Column(
            "course_type", sa.String(), nullable=False, server_default="programming"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("courses", "course_type")
