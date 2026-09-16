"""create feedback_submissions and notifications tables

Revision ID: d1e7b4a9c052
Revises: b2d4c6e8f0a1
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e7b4a9c052'
down_revision: Union[str, Sequence[str], None] = 'b2d4c6e8f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "feedback_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("submitter_user_id", sa.String(), nullable=True),
        sa.Column("submitter_name", sa.String(), nullable=True),
        sa.Column("submitter_email", sa.String(), nullable=True),
        sa.Column("submitter_ip", sa.String(), nullable=True),
        sa.Column("course_id", sa.String(), nullable=True),
        sa.Column(
            "email_delivered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feedback_submissions_kind", "feedback_submissions", ["kind"]
    )
    op.create_index(
        "ix_feedback_submissions_submitter_ip",
        "feedback_submissions",
        ["submitter_ip"],
    )
    op.create_index(
        "ix_feedback_submissions_created_at", "feedback_submissions", ["created_at"]
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(
        "ix_feedback_submissions_created_at", table_name="feedback_submissions"
    )
    op.drop_index(
        "ix_feedback_submissions_submitter_ip", table_name="feedback_submissions"
    )
    op.drop_index("ix_feedback_submissions_kind", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")
