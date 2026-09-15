"""add forked_from_id to courses

Revision ID: 3a7d9c2e1f4b
Revises: 8f93cd467323
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a7d9c2e1f4b'
down_revision: Union[str, Sequence[str], None] = '8f93cd467323'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "courses",
        sa.Column("forked_from_id", sa.String(), nullable=True),
    )
    # SET NULL, not CASCADE: a fork is an independent course and must
    # survive its source being deleted.
    op.create_foreign_key(
        "fk_courses_forked_from_id_courses",
        "courses",
        "courses",
        ["forked_from_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_courses_forked_from_id_courses", "courses", type_="foreignkey"
    )
    op.drop_column("courses", "forked_from_id")
