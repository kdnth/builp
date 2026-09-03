"""add tags column to courses

Revision ID: ed5b1f61fd31
Revises: 555b2ef15fdc
Create Date: 2026-09-03 01:31:54.288663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed5b1f61fd31'
down_revision: Union[str, Sequence[str], None] = '555b2ef15fdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills existing rows (there's no NULL state for
    # tags to be in; a course with no tags yet just has an empty list).
    # Left in place rather than dropped after backfill, so any insert
    # path, not just the ORM, gets a safe default.
    op.add_column(
        "courses",
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("courses", "tags")
