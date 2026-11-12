"""Save reviewed Dean meeting follow-ups."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0014_dean_follow_up'
down_revision = '0013_operational_evidence'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dean_follow_ups',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('meeting_day', sa.Date(), primary_key=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('items', JSONB(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table('dean_follow_ups')
