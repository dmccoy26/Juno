"""TaskDock assignments and complete authorized worker context."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0011_worker_assignments'
down_revision='0010_repair_history'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('workers',sa.Column('assignment_keys',JSONB,nullable=False,server_default=sa.text("'[]'::jsonb")))
    op.alter_column('workers','assignment_keys',server_default=None)
    op.add_column('worker_grants',sa.Column('mode',sa.String(20),nullable=False,server_default='manual'))
    op.alter_column('worker_grants','mode',server_default=None)
    op.add_column('worker_grants',sa.Column('include_all',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.alter_column('worker_grants','include_all',server_default=None)
    op.alter_column('worker_grants','expires_at',nullable=True)


def downgrade():
    op.execute("UPDATE worker_grants SET revoked=true, expires_at=CURRENT_TIMESTAMP WHERE expires_at IS NULL")
    op.alter_column('worker_grants','expires_at',nullable=False)
    op.drop_column('worker_grants','include_all')
    op.drop_column('worker_grants','mode')
    op.drop_column('workers','assignment_keys')
