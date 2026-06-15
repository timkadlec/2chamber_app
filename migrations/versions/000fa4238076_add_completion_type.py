"""add completion_type to subjects

Revision ID: 000fa4238076
Revises: 08ccec5cf685
Create Date: 2026-05-28 10:53:42.159534

"""
from alembic import op
import sqlalchemy as sa

revision = '000fa4238076'
down_revision = '08ccec5cf685'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completion_type', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('subjects', schema=None) as batch_op:
        batch_op.drop_column('completion_type')
