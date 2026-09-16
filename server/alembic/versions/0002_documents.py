"""add document ownership metadata

Revision ID: 0002_documents
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision='0002_documents'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        'documents',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('document_id',sa.String(length=100),nullable=False),
        sa.Column('filename',sa.String(length=255),nullable=False),
        sa.Column('pages',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index('ix_documents_user_id','documents',['user_id'])
    op.create_index('ix_documents_document_id','documents',['document_id'],unique=True)

def downgrade():
    op.drop_index('ix_documents_document_id',table_name='documents')
    op.drop_index('ix_documents_user_id',table_name='documents')
    op.drop_table('documents')
