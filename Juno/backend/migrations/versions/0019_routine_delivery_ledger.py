"""Durable routine rule history and occurrence outbox; live execution stays off."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0019_routine_delivery_ledger'
down_revision = '0018_recurring_routines'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recurring_routines', sa.Column('target_scope', JSONB, nullable=True))
    op.add_column('recurring_routines', sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recurring_routines', sa.Column('last_planned_date', sa.Date, nullable=True))
    op.create_table('routine_rule_versions',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('routine_id', sa.String(36), sa.ForeignKey('recurring_routines.id'), primary_key=True),
        sa.Column('revision', sa.Integer, primary_key=True),
        sa.Column('definition', JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False))
    op.execute("INSERT INTO routine_rule_versions SELECT owner_id,id,revision,definition,status,'preserved_at_upgrade',updated_at FROM recurring_routines")
    op.create_table('routine_occurrences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('routine_id', sa.String(36), sa.ForeignKey('recurring_routines.id'), nullable=False),
        sa.Column('rule_revision', sa.Integer, nullable=False),
        sa.Column('local_date', sa.Date, nullable=False),
        sa.Column('period_key', sa.String(30), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('target_scope', JSONB, nullable=False),
        sa.Column('payload', JSONB, nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=False),
        sa.Column('operation_id', sa.String(36), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(300), nullable=False),
        sa.Column('lease_id', sa.String(36), nullable=True),
        sa.Column('lease_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('task_id', sa.String(500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_routine_occurrences_owner_id','routine_occurrences',['owner_id'])
    op.create_index('ix_routine_occurrences_routine_id','routine_occurrences',['routine_id'])


def downgrade():
    connection = op.get_bind()
    for table in ('routine_occurrences','routine_rule_versions'):
        if connection.execute(sa.text('SELECT EXISTS(SELECT 1 FROM '+table+')')).scalar():
            raise RuntimeError('Export routine history before downgrade; automatic data loss of delivery identities is prohibited.')
    if connection.execute(sa.text('SELECT EXISTS(SELECT 1 FROM recurring_routines WHERE target_scope IS NOT NULL OR activated_at IS NOT NULL OR last_planned_date IS NOT NULL)')).scalar():
        raise RuntimeError('Export routine delivery state before downgrade; automatic data loss is prohibited.')
    op.drop_table('routine_occurrences')
    op.drop_table('routine_rule_versions')
    for column in ('last_planned_date','activated_at','target_scope'):
        op.drop_column('recurring_routines', column)
