"""Persist the chat message that a reviewed memory came from."""
from alembic import op
import sqlalchemy as sa
revision='0008_memory_origin'
down_revision='0007_schedules'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('memories',sa.Column('source_message_id',sa.String(36),nullable=True))
    op.create_foreign_key('fk_memory_source_message','memories','messages',['source_message_id'],['id'],ondelete='SET NULL')
    op.create_unique_constraint('uq_memory_owner_source_message','memories',['owner_id','source_message_id'])
    # Backfill only an unambiguous exact, owner-matched copy from earlier clients.
    op.execute('''WITH matches AS (
        SELECT m.id AS memory_id, msg.id AS message_id,
          count(*) OVER (PARTITION BY m.id) AS memory_matches,
          count(*) OVER (PARTITION BY msg.id) AS message_matches
        FROM memories m JOIN conversations c ON c.owner_id=m.owner_id
          JOIN messages msg ON msg.conversation_id=c.id AND msg.text=m.text
        WHERE msg.role='user' AND msg.status='complete'
    ) UPDATE memories m SET source_message_id=x.message_id FROM matches x
      WHERE m.id=x.memory_id AND x.memory_matches=1 AND x.message_matches=1''')

def downgrade():
    op.drop_constraint('uq_memory_owner_source_message','memories',type_='unique')
    op.drop_constraint('fk_memory_source_message','memories',type_='foreignkey')
    op.drop_column('memories','source_message_id')
