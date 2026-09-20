"""create JARVIS schema

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('users',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('email',sa.String(255),nullable=False),sa.Column('password_hash',sa.String(255),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_users_email','users',['email'],unique=True)
    op.create_table('notes',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('title',sa.String(200),nullable=False),sa.Column('content',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False))
    op.create_index('ix_notes_user_id','notes',['user_id'])
    op.create_table('chat_messages',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('role',sa.String(20),nullable=False),sa.Column('content',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_chat_messages_user_id','chat_messages',['user_id'])
    op.create_table('subjects',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('name',sa.String(100),nullable=False),sa.Column('code',sa.String(30),nullable=False),sa.Column('daily_minutes',sa.Integer(),nullable=False),sa.Column('exam_date',sa.Date(),nullable=True),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_subjects_user_id','subjects',['user_id'])
    op.create_table('study_tasks',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('subject_id',sa.Integer(),sa.ForeignKey('subjects.id'),nullable=True),sa.Column('title',sa.String(200),nullable=False),sa.Column('task_date',sa.Date(),nullable=False),sa.Column('minutes',sa.Integer(),nullable=False),sa.Column('completed',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_study_tasks_user_id','study_tasks',['user_id'])
    op.create_table('study_events',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('event_type',sa.String(40),nullable=False),sa.Column('minutes',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_study_events_user_id','study_events',['user_id']);op.create_index('ix_study_events_event_type','study_events',['event_type']);op.create_index('ix_study_events_created_at','study_events',['created_at'])
    op.create_table('flashcards',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('question',sa.Text(),nullable=False),sa.Column('answer',sa.Text(),nullable=False),sa.Column('document_id',sa.String(100),nullable=True),sa.Column('review_count',sa.Integer(),nullable=False),sa.Column('last_reviewed_at',sa.DateTime(),nullable=True),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_flashcards_user_id','flashcards',['user_id'])

def downgrade():
    op.drop_table('flashcards');op.drop_table('study_events');op.drop_table('study_tasks');op.drop_table('subjects');op.drop_table('chat_messages');op.drop_table('notes');op.drop_table('users')
