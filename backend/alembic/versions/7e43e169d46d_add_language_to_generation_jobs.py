"""add language to generation_jobs

Revision ID: 7e43e169d46d
Revises: 6c1e4a9f2b7d
Create Date: 2026-09-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e43e169d46d'
down_revision: Union[str, Sequence[str], None] = '6c1e4a9f2b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "generation_jobs",
        sa.Column(
            "language", sa.String(), nullable=False, server_default="javascript"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("generation_jobs", "language")
