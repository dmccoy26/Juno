"""Reviewed diary carry-forward provenance and saved weekly Dean drafts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0012_daily_planning'
down_revision='0011_worker_assignments'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('planning_carry',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('operation_id',sa.String(36),primary_key=True),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('diary_id',sa.String(36),sa.ForeignKey('check_ins.id',ondelete='SET NULL'),nullable=True),
        sa.Column('diary_revision',sa.Integer(),nullable=False),sa.Column('diary_day',sa.Date(),nullable=False),
        sa.Column('workspace_id',sa.String(500),nullable=False),sa.Column('task_id',sa.String(500),nullable=False),
        sa.Column('source_quote',sa.Text(),nullable=False),sa.Column('before',JSONB(),nullable=False),
        sa.Column('after',JSONB(),nullable=False),sa.Column('planning_revision',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('dean_drafts',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),nullable=False),
        sa.Column('week_start',sa.Date(),nullable=False),sa.Column('text',sa.Text(),nullable=False),
        sa.Column('basis',JSONB(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('owner_id','week_start',name='uq_dean_draft_owner_week'))
    op.create_index('ix_dean_drafts_owner_id','dean_drafts',['owner_id'])
    op.create_table('dean_draft_operations',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('operation_id',sa.String(36),primary_key=True),sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('receipt',JSONB(),nullable=False))


def downgrade():
    op.drop_table('dean_draft_operations')
    op.drop_index('ix_dean_drafts_owner_id',table_name='dean_drafts')
    op.drop_table('dean_drafts')
    op.drop_table('planning_carry')
