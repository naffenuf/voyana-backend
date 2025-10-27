"""Consolidate status and remove is_public

Revision ID: c9e4f5a6b7d8
Revises: 961a9c623460
Create Date: 2025-10-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'c9e4f5a6b7d8'
down_revision = '961a9c623460'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Migrate existing data
    # Tours with is_public=true become status='published'
    op.execute(text("""
        UPDATE tours
        SET status = 'published',
            published_at = COALESCE(published_at, updated_at)
        WHERE is_public = true
    """))

    # Tours with is_public=false AND status='live' become status='ready'
    op.execute(text("""
        UPDATE tours
        SET status = 'ready'
        WHERE is_public = false AND status = 'live'
    """))

    # Step 2: Drop is_public column
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.drop_column('is_public')


def downgrade():
    # Add is_public column back
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))

    # Restore data from status
    # Tours with status='published' get is_public=true
    op.execute(text("""
        UPDATE tours
        SET is_public = true
        WHERE status = 'published'
    """))

    # Tours with status='ready' revert to status='live'
    op.execute(text("""
        UPDATE tours
        SET status = 'live'
        WHERE status = 'ready'
    """))
