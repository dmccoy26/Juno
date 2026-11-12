"""Store reviewable weekly email drafts for department chairs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0015_chairs_drafts'
down_revision = '0014_dean_follow_up'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chairs_drafts',
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('owners.id'), primary_key=True),
        sa.Column('week_start', sa.Date(), primary_key=True),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('coverage', JSONB(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table('chairs_drafts')
