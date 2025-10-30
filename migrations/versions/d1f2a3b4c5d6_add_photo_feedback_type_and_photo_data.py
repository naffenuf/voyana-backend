"""Add photo feedback type and photo_data field

Revision ID: d1f2a3b4c5d6
Revises: c9e4f5a6b7d8
Create Date: 2025-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1f2a3b4c5d6'
down_revision = 'c9e4f5a6b7d8'
branch_labels = None
depends_on = None


def upgrade():
    # Add photo_data column to feedback table
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('photo_data', sa.Text(), nullable=True))

    # Note: feedback_type validation is handled at application level
    # The 'photo' type will be added to allowed values: 'issue', 'rating', 'comment', 'suggestion', 'photo'
    # Constraint: photo feedback should only be used with site_id (not tour_id)
    # This constraint will be enforced by application logic


def downgrade():
    # Remove photo_data column
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_column('photo_data')
