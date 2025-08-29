"""AcademicYear model connected with semesters

Revision ID: 285c33728f1c
Revises: cf9b9f088eea
Create Date: 2025-08-27 18:45:41.687362
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '285c33728f1c'
down_revision = 'cf9b9f088eea'
branch_labels = None
depends_on = None

FK_NAME = "fk_semesters_academic_year_id_academic_years"

def upgrade():
    # Use batch_alter_table for SQLite safety; fine on Postgres too.
    with op.batch_alter_table('semesters', schema=None) as batch_op:
        # Match the model: nullable=True to avoid failing on existing rows.
        batch_op.add_column(sa.Column('academic_year_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            FK_NAME,
            'academic_years',
            ['academic_year_id'],
            ['id'],
            ondelete=None,
            onupdate=None
        )
        # Optional: index for the FK
        batch_op.create_index('ix_semesters_academic_year_id', ['academic_year_id'])

def downgrade():
    with op.batch_alter_table('semesters', schema=None) as batch_op:
        batch_op.drop_index('ix_semesters_academic_year_id')
        batch_op.drop_constraint(FK_NAME, type_='foreignkey')
        batch_op.drop_column('academic_year_id')
