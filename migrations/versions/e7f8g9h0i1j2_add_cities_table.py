"""add cities table

Revision ID: e7f8g9h0i1j2
Revises: a1b516dbc95b
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'a1b516dbc95b'
branch_labels = None
depends_on = None


def upgrade():
    # Create cities table
    op.create_table(
        'cities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('hero_image_url', sa.String(length=1024), nullable=True),
        sa.Column('hero_title', sa.String(length=200), nullable=True),
        sa.Column('hero_subtitle', sa.String(length=200), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('state_province', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_city_location', 'cities', ['name', 'latitude', 'longitude'])
    op.create_index(op.f('ix_cities_name'), 'cities', ['name'], unique=False)

    # Create unique constraint for (name, latitude, longitude)
    op.create_unique_constraint('uq_city_location', 'cities', ['name', 'latitude', 'longitude'])


def downgrade():
    op.drop_constraint('uq_city_location', 'cities', type_='unique')
    op.drop_index('idx_city_location', table_name='cities')
    op.drop_index(op.f('ix_cities_name'), table_name='cities')
    op.drop_table('cities')
