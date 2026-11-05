"""Read-only operational references and recommendation feedback."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0013_operational_evidence'
down_revision='0012_daily_planning'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('operational_state',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('data',JSONB(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))


def downgrade():
    op.drop_table('operational_state')
