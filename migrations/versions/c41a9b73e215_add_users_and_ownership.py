"""add users and ownership

Revision ID: c41a9b73e215
Revises: 8d6f51c4a920
Create Date: 2026-09-16
"""
from alembic import op
import sqlalchemy as sa

revision = "c41a9b73e215"
down_revision = "8d6f51c4a920"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("picture_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_email", ["email"], unique=True)
        batch_op.create_index("ix_users_google_sub", ["google_sub"], unique=True)
    with op.batch_alter_table("quiz_sets") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(length=36)))
        batch_op.create_foreign_key("fk_quiz_sets_owner", "users", ["owner_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_quiz_sets_owner_id", ["owner_id"])
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36)))
        batch_op.create_foreign_key("fk_quiz_attempts_user", "users", ["user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_quiz_attempts_user_id", ["user_id"])


def downgrade():
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.drop_index("ix_quiz_attempts_user_id")
        batch_op.drop_constraint("fk_quiz_attempts_user", type_="foreignkey")
        batch_op.drop_column("user_id")
    with op.batch_alter_table("quiz_sets") as batch_op:
        batch_op.drop_index("ix_quiz_sets_owner_id")
        batch_op.drop_constraint("fk_quiz_sets_owner", type_="foreignkey")
        batch_op.drop_column("owner_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_google_sub")
        batch_op.drop_index("ix_users_email")
    op.drop_table("users")
