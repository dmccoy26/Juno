"""Revision-checked planning facts; TaskDock remains authoritative for tasks."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0006_planning'
down_revision='0005_integrations'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('planning_state',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('data',JSONB(),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))


def downgrade():
    op.drop_table('planning_state')
