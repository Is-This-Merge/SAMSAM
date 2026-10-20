"""create quiz collaborators

Revision ID: e52bf319d074
Revises: c41a9b73e215
Create Date: 2026-09-16
"""
from alembic import op
import sqlalchemy as sa

revision = "e52bf319d074"
down_revision = "c41a9b73e215"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_collaborators",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("quiz_set_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("can_edit", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["quiz_set_id"], ["quiz_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quiz_set_id", "user_id", name="uq_quiz_collaborator"),
    )
    with op.batch_alter_table("quiz_collaborators") as batch_op:
        batch_op.create_index("ix_quiz_collaborators_quiz_set_id", ["quiz_set_id"])
        batch_op.create_index("ix_quiz_collaborators_user_id", ["user_id"])


def downgrade():
    with op.batch_alter_table("quiz_collaborators") as batch_op:
        batch_op.drop_index("ix_quiz_collaborators_user_id")
        batch_op.drop_index("ix_quiz_collaborators_quiz_set_id")
    op.drop_table("quiz_collaborators")
