"""add generation metrics

Revision ID: c5f1a9b3d7e2
Revises: b2d4c6e8f0a1
Create Date: 2026-09-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5f1a9b3d7e2'
down_revision: Union[str, Sequence[str], None] = 'b2d4c6e8f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("generation_jobs", sa.Column("metrics", sa.JSON(), nullable=True))
    op.create_table(
        "generation_stage_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_creation_tokens", sa.Integer(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generation_stage_metrics_job_id"),
        "generation_stage_metrics",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_generation_stage_metrics_job_id"),
        table_name="generation_stage_metrics",
    )
    op.drop_table("generation_stage_metrics")
    op.drop_column("generation_jobs", "metrics")
