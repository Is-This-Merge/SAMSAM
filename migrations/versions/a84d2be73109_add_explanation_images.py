"""add explanation images

Revision ID: a84d2be73109
Revises: f73b8cd64120
"""

from alembic import op
import sqlalchemy as sa


revision = "a84d2be73109"
down_revision = "f73b8cd64120"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("explanation_image_data", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("questions", "explanation_image_data")
