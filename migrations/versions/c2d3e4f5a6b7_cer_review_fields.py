"""add review fields and target semester to chamber_enrollment_requests

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    existing_cols = {
        col['name']
        for col in sa_inspect(op.get_bind()).get_columns('chamber_enrollment_requests')
    }

    if 'reviewed_by_id' not in existing_cols:
        op.add_column('chamber_enrollment_requests',
            sa.Column('reviewed_by_id', sa.String(), nullable=True))
        op.create_foreign_key(
            'fk_cer_reviewed_by', 'chamber_enrollment_requests',
            'users', ['reviewed_by_id'], ['id'], ondelete='SET NULL')

    if 'reviewed_at' not in existing_cols:
        op.add_column('chamber_enrollment_requests',
            sa.Column('reviewed_at', sa.DateTime(), nullable=True))

    if 'review_comment' not in existing_cols:
        op.add_column('chamber_enrollment_requests',
            sa.Column('review_comment', sa.Text(), nullable=True))

    if 'target_semester_id' not in existing_cols:
        op.add_column('chamber_enrollment_requests',
            sa.Column('target_semester_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_cer_target_semester', 'chamber_enrollment_requests',
            'semesters', ['target_semester_id'], ['id'], ondelete='SET NULL')

    if 'result_ensemble_id' not in existing_cols:
        op.add_column('chamber_enrollment_requests',
            sa.Column('result_ensemble_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_cer_result_ensemble', 'chamber_enrollment_requests',
            'ensembles', ['result_ensemble_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('fk_cer_result_ensemble', 'chamber_enrollment_requests', type_='foreignkey')
    op.drop_column('chamber_enrollment_requests', 'result_ensemble_id')
    op.drop_constraint('fk_cer_target_semester', 'chamber_enrollment_requests', type_='foreignkey')
    op.drop_column('chamber_enrollment_requests', 'target_semester_id')
    op.drop_column('chamber_enrollment_requests', 'review_comment')
    op.drop_column('chamber_enrollment_requests', 'reviewed_at')
    op.drop_constraint('fk_cer_reviewed_by', 'chamber_enrollment_requests', type_='foreignkey')
    op.drop_column('chamber_enrollment_requests', 'reviewed_by_id')
