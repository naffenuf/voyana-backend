"""add_is_ordered_to_tours

Revision ID: f4e3d2c1b0a9
Revises: 81ca9bb36d8e
Create Date: 2026-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f4e3d2c1b0a9'
down_revision = '81ca9bb36d8e'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_ordered column to tours table
    # Default to false for backwards compatibility (existing tours stay optimized)
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_ordered', sa.Boolean(), nullable=False, server_default='false')
        )


def downgrade():
    # Remove is_ordered column from tours table
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.drop_column('is_ordered')
