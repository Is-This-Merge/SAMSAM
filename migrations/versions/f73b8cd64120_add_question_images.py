"""add question images

Revision ID: f73b8cd64120
Revises: e52bf319d074
"""

from alembic import op
import sqlalchemy as sa


revision = "f73b8cd64120"
down_revision = "e52bf319d074"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("image_data", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("questions", "image_data")
