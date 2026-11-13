"""Advance the chat message identity past existing records."""

from alembic import op

revision = '0017_chat_message_order'
down_revision = '0016_chairs_routing'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        LOCK TABLE messages IN ACCESS EXCLUSIVE MODE;
        DO $$
        DECLARE
            saved_max bigint;
            sequence_next bigint;
        BEGIN
            SELECT max(order_key) INTO saved_max FROM messages;
            SELECT last_value + CASE WHEN is_called THEN 1 ELSE 0 END
                INTO sequence_next FROM messages_order_key_seq;
            IF saved_max >= sequence_next THEN
                EXECUTE format('ALTER TABLE messages ALTER COLUMN order_key RESTART WITH %s', saved_max + 1);
            END IF;
        END $$;
    """)


def downgrade():
    # Message order remains valid on the previous schema.
    pass
