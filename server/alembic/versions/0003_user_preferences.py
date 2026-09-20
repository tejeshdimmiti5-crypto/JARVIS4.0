"""add user preferences
Revision ID: 0003_user_preferences
Revises: 0002_documents
"""
from alembic import op
import sqlalchemy as sa
revision='0003_user_preferences'
down_revision='0002_documents'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('user_preferences',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('daily_minutes',sa.Integer(),nullable=False,server_default='120'),sa.Column('focus_subject',sa.String(length=100),nullable=False,server_default=''),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_user_preferences_user_id','user_preferences',['user_id'],unique=True)

def downgrade():
    op.drop_index('ix_user_preferences_user_id',table_name='user_preferences')
    op.drop_table('user_preferences')
