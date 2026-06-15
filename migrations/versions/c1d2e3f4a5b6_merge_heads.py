"""merge heads: 000fa4238076 + b6d5df76e27c

Revision ID: c1d2e3f4a5b6
Revises: 000fa4238076, b6d5df76e27c
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = ('000fa4238076', 'b6d5df76e27c')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
