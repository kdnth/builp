"""add progress to generation_jobs

Revision ID: b2d4c6e8f0a1
Revises: 7e43e169d46d
Create Date: 2026-09-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d4c6e8f0a1'
down_revision: Union[str, Sequence[str], None] = '7e43e169d46d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("generation_jobs", sa.Column("stage", sa.String(), nullable=True))
    op.add_column(
        "generation_jobs", sa.Column("lessons_total", sa.Integer(), nullable=True)
    )
    op.add_column(
        "generation_jobs",
        sa.Column(
            "lessons_completed", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("generation_jobs", "lessons_completed")
    op.drop_column("generation_jobs", "lessons_total")
    op.drop_column("generation_jobs", "stage")
