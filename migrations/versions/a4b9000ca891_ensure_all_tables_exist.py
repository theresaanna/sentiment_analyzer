"""ensure_all_tables_exist

Revision ID: a4b9000ca891
Revises: 52ae8f7268db
Create Date: 2025-09-12 10:21:18.541762

This migration ensures all tables needed for production are created,
including Channel, Video, UserChannel, and SentimentFeedback tables.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'a4b9000ca891'
down_revision = '52ae8f7268db'
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create Channel table
    if 'channel' not in existing_tables:
        op.create_table('channel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yt_channel_id', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('handle', sa.String(255), nullable=True),
        sa.Column('uploads_playlist_id', sa.String(255), nullable=True),
        sa.Column('latest_video_id', sa.String(64), nullable=True),
        sa.Column('video_count', sa.Integer(), default=0),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('yt_channel_id')
        )
        op.create_index(op.f('ix_channel_yt_channel_id'), 'channel', ['yt_channel_id'], unique=True)
        op.create_index(op.f('ix_channel_handle'), 'channel', ['handle'], unique=False)

    # Create Video table
    if 'video' not in existing_tables:
        op.create_table('video',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('yt_video_id', sa.String(64), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('views', sa.Integer(), default=0),
        sa.Column('likes', sa.Integer(), default=0),
        sa.Column('comments', sa.Integer(), default=0),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['channel_id'], ['channel.id']),
        sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('yt_video_id')
        )
        op.create_index(op.f('ix_video_yt_video_id'), 'video', ['yt_video_id'], unique=True)
        op.create_index(op.f('ix_video_channel_id'), 'video', ['channel_id'], unique=False)
        op.create_index(op.f('ix_video_published_at'), 'video', ['published_at'], unique=False)

    # Create UserChannel table
    if 'user_channel' not in existing_tables:
        op.create_table('user_channel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['channel_id'], ['channel.id']),
        sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'channel_id', name='uq_user_channel')
        )
        op.create_index(op.f('ix_user_channel_user_id'), 'user_channel', ['user_id'], unique=False)
        op.create_index(op.f('ix_user_channel_channel_id'), 'user_channel', ['channel_id'], unique=False)

    # Create SentimentFeedback table
    if 'sentiment_feedback' not in existing_tables:
        op.create_table('sentiment_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('video_id', sa.String(64), nullable=False),
        sa.Column('comment_id', sa.String(128), nullable=True),
        sa.Column('comment_text', sa.Text(), nullable=False),
        sa.Column('comment_author', sa.String(255), nullable=True),
        sa.Column('predicted_sentiment', sa.String(20), nullable=False),
        sa.Column('corrected_sentiment', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('session_id', sa.String(128), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('used_for_training', sa.Boolean(), default=False),
        sa.Column('training_batch', sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'video_id', 'comment_text', name='uq_user_comment_feedback'),
            sa.UniqueConstraint('session_id', 'video_id', 'comment_text', name='uq_session_comment_feedback')
        )
        op.create_index(op.f('ix_sentiment_feedback_user_id'), 'sentiment_feedback', ['user_id'], unique=False)
        op.create_index(op.f('ix_sentiment_feedback_video_id'), 'sentiment_feedback', ['video_id'], unique=False)
        op.create_index(op.f('ix_sentiment_feedback_comment_id'), 'sentiment_feedback', ['comment_id'], unique=False)
        op.create_index(op.f('ix_sentiment_feedback_created_at'), 'sentiment_feedback', ['created_at'], unique=False)
        op.create_index(op.f('ix_sentiment_feedback_used_for_training'), 'sentiment_feedback', ['used_for_training'], unique=False)
        op.create_index('idx_training_queries', 'sentiment_feedback', ['used_for_training', 'created_at'], unique=False)


def downgrade():
    # Get database connection to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop SentimentFeedback table and indexes
    if 'sentiment_feedback' in existing_tables:
        op.drop_index('idx_training_queries', table_name='sentiment_feedback')
        op.drop_index(op.f('ix_sentiment_feedback_used_for_training'), table_name='sentiment_feedback')
        op.drop_index(op.f('ix_sentiment_feedback_created_at'), table_name='sentiment_feedback')
        op.drop_index(op.f('ix_sentiment_feedback_comment_id'), table_name='sentiment_feedback')
        op.drop_index(op.f('ix_sentiment_feedback_video_id'), table_name='sentiment_feedback')
        op.drop_index(op.f('ix_sentiment_feedback_user_id'), table_name='sentiment_feedback')
        op.drop_table('sentiment_feedback')
    
    # Drop UserChannel table and indexes
    if 'user_channel' in existing_tables:
        op.drop_index(op.f('ix_user_channel_channel_id'), table_name='user_channel')
        op.drop_index(op.f('ix_user_channel_user_id'), table_name='user_channel')
        op.drop_table('user_channel')
    
    # Drop Video table and indexes
    if 'video' in existing_tables:
        op.drop_index(op.f('ix_video_published_at'), table_name='video')
        op.drop_index(op.f('ix_video_channel_id'), table_name='video')
        op.drop_index(op.f('ix_video_yt_video_id'), table_name='video')
        op.drop_table('video')
    
    # Drop Channel table and indexes
    if 'channel' in existing_tables:
        op.drop_index(op.f('ix_channel_handle'), table_name='channel')
        op.drop_index(op.f('ix_channel_yt_channel_id'), table_name='channel')
        op.drop_table('channel')
