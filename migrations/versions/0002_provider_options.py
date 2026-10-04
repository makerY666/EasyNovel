"""Vendor inference options for existing installations."""
from alembic import op
from sqlalchemy import inspect, Column, JSON
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None


def upgrade():
    if 'extra_body' not in {c['name'] for c in inspect(op.get_bind()).get_columns('providers')}:
        op.add_column('providers',Column('extra_body',JSON,nullable=False,server_default='{}'))


def downgrade():
    op.drop_column('providers','extra_body')
