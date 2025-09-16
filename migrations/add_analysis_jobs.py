"""
Add analysis jobs table for queued sentiment analysis

This migration creates a table to track background analysis jobs
that users can queue for processing larger comment sets.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_analysis_jobs_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create analysis_jobs table
    op.create_table('analysis_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(100), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(20), nullable=False),
        sa.Column('video_title', sa.Text(), nullable=True),
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('channel_name', sa.String(200), nullable=True),
        sa.Column('comment_count_requested', sa.Integer(), nullable=False),
        sa.Column('comment_count_processed', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), nullable=False, default='queued'),
        # Status values: queued, processing, completed, failed, cancelled
        sa.Column('progress', sa.Integer(), default=0),  # 0-100 percentage
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),  # Store full analysis results
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_analysis_jobs_user_id', 'analysis_jobs', ['user_id'])
    op.create_index('idx_analysis_jobs_status', 'analysis_jobs', ['status'])
    op.create_index('idx_analysis_jobs_created_at', 'analysis_jobs', ['created_at'])
    op.create_index('idx_analysis_jobs_job_id', 'analysis_jobs', ['job_id'])

def downgrade():
    op.drop_index('idx_analysis_jobs_job_id', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_created_at', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_status', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_user_id', 'analysis_jobs')
    op.drop_table('analysis_jobs')