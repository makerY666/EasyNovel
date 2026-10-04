"""Canonical setting changes participate in impact protection."""
from alembic import op
from sqlalchemy import inspect, Column, String
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None


def upgrade():
    columns={c['name']:c for c in inspect(op.get_bind()).get_columns('impacts')}
    with op.batch_alter_table('impacts') as batch:
        if 'source_record_id' not in columns:
            batch.add_column(Column('source_record_id',String,nullable=True))
        for name in ('source_chapter_id','version_id'):
            if not columns[name]['nullable']:
                batch.alter_column(name,existing_type=String,nullable=True)


def downgrade():
    raise RuntimeError('Restore a pre-migration backup instead of discarding impact records.')
