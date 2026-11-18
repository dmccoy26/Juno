"""Private work bookmarks; additive and separate from operational evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0020_work_support'
down_revision='0019_routine_delivery_ledger'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('work_bookmarks',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('first_action',sa.Text,nullable=False),
        sa.Column('finish_point',sa.Text,nullable=False),
        sa.Column('where_stopped',sa.Text,nullable=False),
        sa.Column('blocker',sa.Text,nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('source_ref',JSONB,nullable=True),
        sa.Column('resume_count',sa.Integer,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_work_bookmarks_owner_id','work_bookmarks',['owner_id'])
    op.create_table('work_support',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('revision',sa.Integer,nullable=False),
        sa.Column('current_id',sa.String(36),nullable=True),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('work_support_operations',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('operation_id',sa.String(36),primary_key=True),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('bookmark_id',sa.String(36),nullable=False),
        sa.Column('revision',sa.Integer,nullable=False),
        sa.Column('command',sa.String(20),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    for name in ('work_bookmarks','work_support','work_support_operations'):
        if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM '+name+')')).scalar():
            raise RuntimeError('Export work bookmarks before downgrade; automatic loss is prohibited.')
    for name in ('work_support_operations','work_support','work_bookmarks'):op.drop_table(name)
