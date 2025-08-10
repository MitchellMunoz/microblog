"""Add created_by, completed_by, and completion_date columns to Task

Revision ID: 42edddb675c6
Revises: 3eddadbaa0b6
Create Date: 2025-06-29 23:55:03.134593
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '42edddb675c6'
down_revision = '3eddadbaa0b6'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('completed_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('completion_date', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_task_created_by_user', 'user', ['created_by'], ['id'])
        batch_op.create_foreign_key('fk_task_completed_by_user', 'user', ['completed_by'], ['id'])
        batch_op.drop_column('user_id')

def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint('fk_task_completed_by_user', type_='foreignkey')
        batch_op.drop_constraint('fk_task_created_by_user', type_='foreignkey')
        batch_op.drop_column('completion_date')
        batch_op.drop_column('completed_by')
        batch_op.drop_column('created_by')
