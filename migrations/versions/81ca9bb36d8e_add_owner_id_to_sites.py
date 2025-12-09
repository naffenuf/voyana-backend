"""add_owner_id_to_sites

Revision ID: 81ca9bb36d8e
Revises: 13cc72f88bd6
Create Date: 2025-12-09 01:38:47.255118

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '81ca9bb36d8e'
down_revision = '13cc72f88bd6'
branch_labels = None
depends_on = None


def upgrade():
    # Add owner_id column to sites table
    with op.batch_alter_table('sites', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('owner_id', sa.Integer(),
                     sa.ForeignKey('users.id', ondelete='CASCADE'),
                     nullable=True)
        )

    # Populate owner_id from first tour that uses each site
    connection = op.get_bind()

    # Get all sites with their first tour's owner (ordered by tour creation date)
    result = connection.execute(sa.text("""
        SELECT DISTINCT ON (ts.site_id)
            ts.site_id,
            t.owner_id
        FROM tour_sites ts
        INNER JOIN tours t ON t.id = ts.tour_id
        ORDER BY ts.site_id, t.created_at ASC
    """))

    # Update each site with the owner from its first tour
    for row in result:
        site_id = row[0]
        owner_id = row[1]
        connection.execute(
            sa.text("UPDATE sites SET owner_id = :owner_id WHERE id = :site_id"),
            {"owner_id": owner_id, "site_id": site_id}
        )

    connection.commit()


def downgrade():
    # Remove owner_id column from sites table
    with op.batch_alter_table('sites', schema=None) as batch_op:
        batch_op.drop_column('owner_id')
