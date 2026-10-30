"""Owner-scoped validated local integration evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0005_integrations'
down_revision='0004_pairing'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('integration_snapshots',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('kind',sa.String(30),primary_key=True),
        sa.Column('id',sa.String(36),nullable=False),
        sa.Column('origin',sa.String(500),nullable=False),
        sa.Column('items',JSONB(),nullable=False),
        sa.Column('details',JSONB(),nullable=False),
        sa.Column('fetched_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('error',sa.String(500),nullable=True))


def downgrade():op.drop_table('integration_snapshots')
