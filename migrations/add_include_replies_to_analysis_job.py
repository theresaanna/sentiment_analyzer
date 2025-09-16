"""Add include_replies field to AnalysisJob table

This migration adds a boolean field to track whether reply threads should be included
in the sentiment analysis.
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add include_replies column to analysis_job table."""
    op.add_column('analysis_job', 
        sa.Column('include_replies', sa.Boolean(), nullable=False, server_default='1')
    )


def downgrade():
    """Remove include_replies column from analysis_job table."""
    op.drop_column('analysis_job', 'include_replies')