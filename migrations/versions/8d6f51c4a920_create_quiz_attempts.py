"""create quiz attempts

Revision ID: 8d6f51c4a920
Revises: 261e9e244d19
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "8d6f51c4a920"
down_revision = "261e9e244d19"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("quiz_set_id", sa.String(length=36), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["quiz_set_id"], ["quiz_sets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("quiz_attempts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_quiz_attempts_completed_at"),
            ["completed_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_quiz_attempts_quiz_set_id"),
            ["quiz_set_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("quiz_attempts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quiz_attempts_quiz_set_id"))
        batch_op.drop_index(batch_op.f("ix_quiz_attempts_completed_at"))
    op.drop_table("quiz_attempts")
