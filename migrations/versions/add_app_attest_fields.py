"""Add App Attest fields to device_registrations

Revision ID: add_app_attest_fields
Revises: (previous migration)
Create Date: 2025-11-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_app_attest_fields'
down_revision = '668d72fddf9a'  # Add device_registrations table for device binding
branch_labels = None
depends_on = None


def upgrade():
    """Add App Attest fields to device_registrations table."""
    # Add new columns for App Attest
    op.add_column('device_registrations', sa.Column('app_attest_key_id', sa.String(256), nullable=True))
    op.add_column('device_registrations', sa.Column('attestation_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('device_registrations', sa.Column('attestation_verified_at', sa.DateTime(), nullable=True))
    op.add_column('device_registrations', sa.Column('last_assertion_at', sa.DateTime(), nullable=True))


def downgrade():
    """Remove App Attest fields from device_registrations table."""
    # Remove columns in reverse order
    op.drop_column('device_registrations', 'last_assertion_at')
    op.drop_column('device_registrations', 'attestation_verified_at')
    op.drop_column('device_registrations', 'attestation_verified')
    op.drop_column('device_registrations', 'app_attest_key_id')
