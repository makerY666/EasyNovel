from alembic import context
from easynovel.database import Base
connection=context.config.attributes.get('connection')
if connection is None:
    raise RuntimeError('Use EasyNovel initialization with an explicit target connection.')
context.configure(connection=connection,target_metadata=Base.metadata,render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
