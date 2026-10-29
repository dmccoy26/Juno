from alembic import context
from juno.database import engine_for
from juno.models import Base

def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.config.attributes.get('connection') is not None:
    migrate(context.config.attributes['connection'])
else:
    with engine_for().connect() as connection:
        migrate(connection)
