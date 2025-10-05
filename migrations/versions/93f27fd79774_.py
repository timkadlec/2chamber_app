"""replace old StudentChamberApplicationException FK with ChamberException

Revision ID: 93f27fd79774
Revises: 029c9f1c16a0
Create Date: 2025-10-05 15:22:49.446437
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '93f27fd79774'
down_revision = '029c9f1c16a0'
branch_labels = None
depends_on = None


def upgrade():
    # --- 1️⃣ Drop the old FK first ---
    with op.batch_alter_table('ensembles', schema=None) as batch_op:
        batch_op.drop_constraint('ensembles_exception_id_fkey', type_='foreignkey')

    # --- 2️⃣ Ensure the new table exists (should already be created by another migration) ---
    # --- 3️⃣ Copy data from the old table into the new one ---
    op.execute("""
               INSERT INTO chamber_exceptions (id, reason, status, created_at, reviewer_comment, reviewed_at,
                                               reviewed_by_id)
               SELECT id, reason, status, created_at, reviewer_comment, reviewed_at, reviewed_by_id
               FROM student_chamber_application_exceptions;
               """)

    # --- 4️⃣ Now drop the old table ---
    op.drop_table('student_chamber_application_exceptions')

    # --- 5️⃣ Recreate the FK pointing to the new table ---
    with op.batch_alter_table('ensembles', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'ensembles_exception_id_fkey',
            'chamber_exceptions',
            ['exception_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade():
    # --- Reverse the process ---
    with op.batch_alter_table('ensembles', schema=None) as batch_op:
        batch_op.drop_constraint('ensembles_exception_id_fkey', type_='foreignkey')

    # Recreate old table
    op.create_table(
        'student_chamber_application_exceptions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('student_chamber_applications.id', ondelete='CASCADE')),
        sa.Column('reason', sa.String(length=255)),
        sa.Column('status', sa.String(length=255)),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()')),
        sa.Column('created_by_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('reviewed_at', postgresql.TIMESTAMP()),
        sa.Column('reviewed_by_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('reviewer_comment', sa.Text()),
    )

    # Recreate the old FK from ensembles → student_chamber_application_exceptions
    with op.batch_alter_table('ensembles', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'ensembles_exception_id_fkey',
            'student_chamber_application_exceptions',
            ['exception_id'],
            ['id'],
            ondelete='CASCADE'
        )
