"""Add scraping session table

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scraping_sessions table
    op.create_table('scraping_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('jobs_found', sa.Integer(), nullable=False),
        sa.Column('jobs_saved', sa.Integer(), nullable=False),
        sa.Column('errors', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('running', 'completed', 'failed', 'cancelled', name='scrapingstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraping_sessions_id'), 'scraping_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_scraping_sessions_status'), 'scraping_sessions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('scraping_sessions')