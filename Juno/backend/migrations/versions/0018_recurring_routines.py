"""Owner-scoped recurring routine drafts, independent of task snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0018_recurring_routines'
down_revision = '0017_chat_message_order'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('conversations', sa.Column('meeting_mode', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('conversations', 'meeting_mode', server_default=None)
    op.create_table('recurring_routines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('definition', JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('revision', sa.Integer, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_recurring_routines_owner_id', 'recurring_routines', ['owner_id'])
    op.create_table('report_versions',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('kind', sa.String(20), primary_key=True),
        sa.Column('week_start', sa.Date, primary_key=True),
        sa.Column('revision', sa.Integer, primary_key=True),
        sa.Column('content', JSONB, nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False))
    op.execute("""INSERT INTO report_versions(owner_id,kind,week_start,revision,content,action,saved_at)
        SELECT owner_id,'dean',week_start,revision,jsonb_build_object('text',text,'basis',basis),'preserved_at_upgrade',updated_at FROM dean_drafts""")
    op.execute("""INSERT INTO report_versions(owner_id,kind,week_start,revision,content,action,saved_at)
        SELECT owner_id,'chairs',week_start,revision,jsonb_build_object('subject',subject,'body',body,'emails',emails,'coverage',coverage),'preserved_at_upgrade',CURRENT_TIMESTAMP FROM chairs_drafts""")
    op.create_table('report_reviews',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('kind', sa.String(20), primary_key=True),
        sa.Column('week_start', sa.Date, primary_key=True),
        sa.Column('audience', sa.String(20), primary_key=True),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM recurring_routines)')) or connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM conversations WHERE meeting_mode)')) or connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM report_versions)')) or connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM report_reviews)')):
        raise RuntimeError('Export routine and meeting records before downgrade; automatic data loss is prohibited.')
    op.drop_index('ix_recurring_routines_owner_id', table_name='recurring_routines')
    op.drop_table('recurring_routines')
    op.drop_table('report_versions')
    op.drop_table('report_reviews')
    op.drop_column('conversations', 'meeting_mode')
