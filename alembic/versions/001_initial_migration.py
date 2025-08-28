"""Initial migration with all models

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create resumes table
    op.create_table('resumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('latex_content', sa.Text(), nullable=False),
        sa.Column('extracted_keywords', sa.JSON(), nullable=False),
        sa.Column('user_keywords', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resumes_id'), 'resumes', ['id'], unique=False)

    # Create job_listings table
    op.create_table('job_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('remote_type', sa.Enum('remote', 'onsite', 'hybrid', name='remotetype'), nullable=True),
        sa.Column('experience_level', sa.Enum('intern', 'junior', 'mid', 'senior', 'lead', 'manager', name='experiencelevel'), nullable=True),
        sa.Column('technologies', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=False),
        sa.Column('application_url', sa.String(length=1000), nullable=True),
        sa.Column('source_site', sa.String(length=100), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_listings_id'), 'job_listings', ['id'], unique=False)
    op.create_index(op.f('ix_job_listings_title'), 'job_listings', ['title'], unique=False)
    op.create_index(op.f('ix_job_listings_company'), 'job_listings', ['company'], unique=False)
    op.create_index(op.f('ix_job_listings_remote_type'), 'job_listings', ['remote_type'], unique=False)
    op.create_index(op.f('ix_job_listings_experience_level'), 'job_listings', ['experience_level'], unique=False)
    op.create_index(op.f('ix_job_listings_source_site'), 'job_listings', ['source_site'], unique=False)
    op.create_index(op.f('ix_job_listings_scraped_at'), 'job_listings', ['scraped_at'], unique=False)

    # Create adapted_resume_drafts table
    op.create_table('adapted_resume_drafts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_resume_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('adapted_latex_content', sa.Text(), nullable=False),
        sa.Column('is_user_edited', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['job_listings.id'], ),
        sa.ForeignKeyConstraint(['original_resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_adapted_resume_drafts_id'), 'adapted_resume_drafts', ['id'], unique=False)
    op.create_index(op.f('ix_adapted_resume_drafts_original_resume_id'), 'adapted_resume_drafts', ['original_resume_id'], unique=False)
    op.create_index(op.f('ix_adapted_resume_drafts_job_id'), 'adapted_resume_drafts', ['job_id'], unique=False)

    # Create job_matches table
    op.create_table('job_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.Column('job_listing_id', sa.Integer(), nullable=False),
        sa.Column('compatibility_score', sa.Float(), nullable=False),
        sa.Column('matching_keywords', sa.JSON(), nullable=False),
        sa.Column('missing_keywords', sa.JSON(), nullable=False),
        sa.Column('algorithm_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_listing_id'], ['job_listings.id'], ),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_matches_id'), 'job_matches', ['id'], unique=False)
    op.create_index(op.f('ix_job_matches_resume_id'), 'job_matches', ['resume_id'], unique=False)
    op.create_index(op.f('ix_job_matches_job_listing_id'), 'job_matches', ['job_listing_id'], unique=False)
    op.create_index(op.f('ix_job_matches_compatibility_score'), 'job_matches', ['compatibility_score'], unique=False)


def downgrade() -> None:
    op.drop_table('job_matches')
    op.drop_table('adapted_resume_drafts')
    op.drop_table('job_listings')
    op.drop_table('resumes')