"""Keep recipient drafts alongside the original weekly email."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0016_chairs_routing'
down_revision = '0015_chairs_drafts'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chairs_drafts', sa.Column('emails', JSONB(), nullable=False, server_default='{}'))


def downgrade():
    op.drop_column('chairs_drafts', 'emails')
