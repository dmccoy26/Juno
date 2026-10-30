"""Recurring schedules, staff status and local planning reservations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0007_schedules'
down_revision='0006_planning'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('schedule_state',
        sa.Column('owner_id',sa.String(36),sa.ForeignKey('owners.id'),primary_key=True),
        sa.Column('data',JSONB(),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():op.drop_table('schedule_state')
