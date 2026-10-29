"""Expiring, single-use host pairing invitations; credentials remain hashed."""
from alembic import op
import sqlalchemy as sa
revision = '0004_pairing'
down_revision = '0003_taskdock'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('pairing_invitations',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False))
    op.create_index('ix_pairing_invitations_owner_id', 'pairing_invitations', ['owner_id'])

    from sqlalchemy.dialects import postgresql
    op.create_table('offline_operations',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('operation_id',sa.String(36),primary_key=True),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('result',postgresql.JSONB(),nullable=False))


def downgrade():
    op.drop_table('offline_operations')
    op.drop_table('pairing_invitations')
