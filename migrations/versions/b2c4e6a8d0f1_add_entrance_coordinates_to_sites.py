"""Add entrance coordinates to sites

Entrance coordinates are the routing destination for sites whose stored
latitude/longitude is a building centroid. The centroid columns are left
untouched: they remain the display position and the routing fallback.

Revision ID: b2c4e6a8d0f1
Revises: 34761a2fc060
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c4e6a8d0f1'
down_revision = '34761a2fc060'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sites', sa.Column('entrance_lat', sa.Float(), nullable=True))
    op.add_column('sites', sa.Column('entrance_lng', sa.Float(), nullable=True))
    # Which SearchDestinations field supplied the coordinate:
    # 'preferred_entrance', 'sole_entrance', or 'walk_navigation_point'.
    op.add_column('sites', sa.Column('entrance_source', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('sites', 'entrance_source')
    op.drop_column('sites', 'entrance_lng')
    op.drop_column('sites', 'entrance_lat')
