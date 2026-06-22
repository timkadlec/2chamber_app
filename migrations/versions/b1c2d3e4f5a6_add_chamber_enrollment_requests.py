"""add chamber enrollment requests

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    existing = sa_inspect(op.get_bind()).get_table_names()

    if 'chamber_enrollment_requests' not in existing:
        op.create_table(
            'chamber_enrollment_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('semester_id', sa.Integer(), nullable=True),
            sa.Column('future_year', sa.Integer(), nullable=True),
            sa.Column('teacher_id', sa.Integer(), nullable=True),
            sa.Column('wants_to_stay', sa.Boolean(), nullable=False),
            sa.Column('stay_ensemble_id', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('submission_date', sa.Date(), nullable=True),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_by_id', sa.String(), nullable=True),
            sa.CheckConstraint("status IN ('pending','approved','rejected')", name='ck_cer_status'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['stay_ensemble_id'], ['ensembles.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_cer_student_semester', 'chamber_enrollment_requests', ['student_id', 'semester_id'])

    if 'chamber_enrollment_request_players' not in existing:
        op.create_table(
            'chamber_enrollment_request_players',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('player_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['request_id'], ['chamber_enrollment_requests.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('request_id', 'player_id', name='uq_cer_player'),
        )


def downgrade():
    op.drop_table('chamber_enrollment_request_players')
    op.drop_index('ix_cer_student_semester', table_name='chamber_enrollment_requests')
    op.drop_table('chamber_enrollment_requests')
