"""Immutable TaskDock read snapshots and active binding; no stored credentials."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_taskdock'
down_revision = '0002_companion'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('taskdock_snapshots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('origin', sa.String(500), nullable=False),
        sa.Column('info', postgresql.JSONB(), nullable=False),
        sa.Column('items', postgresql.JSONB(), nullable=False),
        sa.Column('sources', postgresql.JSONB(), nullable=False),
        sa.Column('snapshot', sa.Text(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_taskdock_snapshots_owner_id', 'taskdock_snapshots', ['owner_id'])
    op.create_table('taskdock_state',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('active_id', sa.String(36), nullable=True),
        sa.Column('error', sa.String(500), nullable=True))

    op.create_table('taskdock_history',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('snapshot_id', sa.String(36), sa.ForeignKey('taskdock_snapshots.id'), primary_key=True),
        sa.Column('task_id', sa.Text(), primary_key=True),
        sa.Column('kind', sa.String(20), primary_key=True),
        sa.Column('items', postgresql.JSONB(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('taskdock_history')
    op.drop_table('taskdock_state')
    op.drop_table('taskdock_snapshots')
