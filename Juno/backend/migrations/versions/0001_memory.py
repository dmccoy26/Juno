"""Owner-scoped canonical memory and device credentials."""
from alembic import op
import sqlalchemy as sa

revision = '0001_memory'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('owners', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('label', sa.String(200), nullable=False))
    op.create_table('devices', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
                    sa.Column('label', sa.String(200), nullable=False),
                    sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
                    sa.Column('revoked', sa.Boolean(), nullable=False))
    op.create_index('ix_devices_owner_id', 'devices', ['owner_id'])
    op.create_table('memories', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
                    sa.Column('text', sa.Text(), nullable=False),
                    sa.Column('source', sa.String(500), nullable=False),
                    sa.Column('confidence', sa.String(20), nullable=False),
                    sa.Column('fingerprint', sa.String(64), nullable=False),
                    sa.Column('revision', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
                    sa.UniqueConstraint('owner_id', 'fingerprint'))
    op.create_index('ix_memories_owner_id', 'memories', ['owner_id'])
    op.create_table('memory_suppressions',
                    sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
                    sa.Column('fingerprint', sa.String(64), primary_key=True))
    op.create_table('audit_events', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
                    sa.Column('device_id', sa.String(36), nullable=False),
                    sa.Column('record_id', sa.String(36), nullable=False),
                    sa.Column('action', sa.String(40), nullable=False),
                    sa.Column('revision', sa.Integer(), nullable=False),
                    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_audit_events_owner_id', 'audit_events', ['owner_id'])


def downgrade():
    for table in ['audit_events', 'memory_suppressions', 'memories', 'devices', 'owners']:
        op.drop_table(table)
