"""Indefinite reports and independently reviewed repair history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0010_repair_history'
down_revision='0009_worker_portal'
branch_labels=None
depends_on=None


def upgrade():
    # Zero denotes indefinite retention. No age-based report deletion remains.
    op.execute('UPDATE worker_portals SET retention_days=0')
    op.add_column('worker_reports',sa.Column('repair_context',JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")))
    op.alter_column('worker_reports','repair_context',server_default=None)
    op.create_index('ix_worker_reports_correction_of','worker_reports',['correction_of'])
    op.create_index('ix_worker_reports_owner_submitted','worker_reports',['owner_id','submitted_at'])


def downgrade():
    op.drop_index('ix_worker_reports_owner_submitted',table_name='worker_reports')
    op.drop_index('ix_worker_reports_correction_of',table_name='worker_reports')
    op.drop_column('worker_reports','repair_context')
    # Do not invent an expiry policy during downgrade.
