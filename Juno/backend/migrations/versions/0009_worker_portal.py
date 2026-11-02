"""Separate worker identities, explicit grants and attributed reviewable reports."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0009_worker_portal'
down_revision='0008_memory_origin'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('worker_portals',sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),sa.Column('enabled',sa.Boolean(),nullable=False),sa.Column('retention_days',sa.Integer(),nullable=False))
    op.create_table('workers',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),sa.Column('name',sa.String(300),nullable=False),sa.Column('active',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_workers_owner_id','workers',['owner_id'])
    op.create_table('worker_invitations',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('worker_id',sa.String(36),sa.ForeignKey('workers.id'),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('used',sa.Boolean(),nullable=False))
    op.create_index('ix_worker_invitations_worker_id','worker_invitations',['worker_id'])
    op.create_table('worker_sessions',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('worker_id',sa.String(36),sa.ForeignKey('workers.id'),nullable=False),sa.Column('csrf_hash',sa.String(64),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_worker_sessions_worker_id','worker_sessions',['worker_id'])
    op.create_table('worker_grants',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),sa.Column('worker_id',sa.String(36),sa.ForeignKey('workers.id'),nullable=False),sa.Column('workspace_id',sa.String(500),nullable=False),sa.Column('task_id',sa.String(500),nullable=False),sa.Column('policy_hash',sa.String(64),nullable=False),sa.Column('excerpt',JSONB,nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    for key in ('owner_id','worker_id'):op.create_index('ix_worker_grants_'+key,'worker_grants',[key])
    op.create_table('worker_reports',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),sa.Column('worker_id',sa.String(36),sa.ForeignKey('workers.id'),nullable=False),sa.Column('grant_id',sa.String(36),sa.ForeignKey('worker_grants.id'),nullable=True),sa.Column('correction_of',sa.String(36),sa.ForeignKey('worker_reports.id',ondelete='SET NULL'),nullable=True),sa.Column('request_key',sa.String(100),nullable=False),sa.Column('payload_hash',sa.String(64),nullable=False),sa.Column('data',JSONB,nullable=False),sa.Column('review',sa.String(30),nullable=False),sa.Column('review_note',sa.Text(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('applied',JSONB,nullable=False),sa.Column('submitted_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('worker_id','request_key',name='uq_worker_report_request'))
    for key in ('owner_id','worker_id'):op.create_index('ix_worker_reports_'+key,'worker_reports',[key])


def downgrade():
    for table in ('worker_reports','worker_grants','worker_sessions','worker_invitations','workers','worker_portals'):op.drop_table(table)
