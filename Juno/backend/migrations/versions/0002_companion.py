"""Persistent chat, local model settings and resumable daily check-ins."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002_companion'
down_revision = '0001_memory'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('model_connections',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('base_url', sa.String(500), nullable=False),
        sa.Column('model', sa.String(200), nullable=False))
    op.create_table('conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_conversations_owner_id', 'conversations', ['owner_id'])
    op.create_table('messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_key', sa.BigInteger(), sa.Identity(), unique=True, nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('model_name', sa.String(200), nullable=True),
        sa.Column('meeting_mode', sa.Boolean(), nullable=False),
        sa.Column('context_refs', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('conversation_id', 'request_id', 'role'))
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_table('check_ins',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('diary_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'local_date'))
    op.create_index('ix_check_ins_owner_id', 'check_ins', ['owner_id'])


def downgrade():
    for name in ('check_ins', 'messages', 'conversations', 'model_connections'):
        op.drop_table(name)
