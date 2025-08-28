"""
Tests for database models
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from job_matching_app.database import Base
from job_matching_app.models import (
    Resume, JobListing, AdaptedResumeDraft, JobMatch,
    RemoteType, ExperienceLevel
)


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_resume(db_session):
    """Create a sample resume for testing"""
    resume = Resume(
        filename="test_resume.tex",
        latex_content="\\documentclass{article}\\begin{document}Test Resume\\end{document}",
        extracted_keywords=["python", "sql", "machine learning"],
        user_keywords=["django", "postgresql"]
    )
    db_session.add(resume)
    db_session.commit()
    return resume


@pytest.fixture
def sample_job_listing(db_session):
    """Create a sample job listing for testing"""
    job = JobListing(
        title="Senior Python Developer",
        company="Tech Corp",
        location="San Francisco, CA",
        remote_type=RemoteType.HYBRID,
        experience_level=ExperienceLevel.SENIOR,
        technologies=["python", "django", "postgresql", "redis"],
        description="We are looking for a senior Python developer...",
        source_url="https://example.com/job/123",
        application_url="https://example.com/apply/123",
        source_site="example",
        scraped_at=datetime.utcnow()
    )
    db_session.add(job)
    db_session.commit()
    return job


class TestResume:
    """Test Resume model"""
    
    def test_create_resume(self, db_session):
        """Test creating a resume"""
        resume = Resume(
            filename="resume.tex",
            latex_content="\\documentclass{article}\\begin{document}Resume\\end{document}",
            extracted_keywords=["python", "sql"],
            user_keywords=["django"]
        )
        
        db_session.add(resume)
        db_session.commit()
        
        assert resume.id is not None
        assert resume.filename == "resume.tex"
        assert resume.created_at is not None
        assert resume.updated_at is not None
    
    def test_all_keywords_property(self, sample_resume):
        """Test all_keywords property combines extracted and user keywords"""
        all_keywords = sample_resume.all_keywords
        expected = ["python", "sql", "machine learning", "django", "postgresql"]
        
        # Convert to sets for comparison (order doesn't matter)
        assert set(all_keywords) == set(expected)
    
    def test_add_user_keyword(self, db_session, sample_resume):
        """Test adding user keyword"""
        sample_resume.add_user_keyword("flask")
        db_session.commit()
        
        assert "flask" in sample_resume.user_keywords
        assert "flask" in sample_resume.all_keywords
    
    def test_add_duplicate_user_keyword(self, db_session, sample_resume):
        """Test adding duplicate user keyword doesn't create duplicates"""
        original_count = len(sample_resume.user_keywords)
        sample_resume.add_user_keyword("django")  # Already exists
        db_session.commit()
        
        assert len(sample_resume.user_keywords) == original_count
    
    def test_remove_user_keyword(self, db_session, sample_resume):
        """Test removing user keyword"""
        sample_resume.remove_user_keyword("django")
        db_session.commit()
        
        assert "django" not in sample_resume.user_keywords
        assert "django" not in sample_resume.all_keywords


class TestJobListing:
    """Test JobListing model"""
    
    def test_create_job_listing(self, db_session):
        """Test creating a job listing"""
        job = JobListing(
            title="Python Developer",
            company="Test Company",
            location="Remote",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.MID,
            technologies=["python", "django"],
            description="Job description",
            source_url="https://example.com/job",
            source_site="example",
            scraped_at=datetime.utcnow()
        )
        
        db_session.add(job)
        db_session.commit()
        
        assert job.id is not None
        assert job.title == "Python Developer"
        assert job.remote_type == RemoteType.REMOTE
        assert job.experience_level == ExperienceLevel.MID
    
    def test_display_location_remote(self, sample_job_listing):
        """Test display_location for remote job"""
        sample_job_listing.remote_type = RemoteType.REMOTE
        assert "Remote" in sample_job_listing.display_location
    
    def test_display_location_hybrid(self, sample_job_listing):
        """Test display_location for hybrid job"""
        sample_job_listing.remote_type = RemoteType.HYBRID
        assert "Hybrid" in sample_job_listing.display_location
        assert sample_job_listing.location in sample_job_listing.display_location
    
    def test_display_tags(self, sample_job_listing):
        """Test display_tags property"""
        tags = sample_job_listing.display_tags
        
        assert "Hybrid" in tags  # remote_type
        assert "Senior" in tags  # experience_level
        assert len([tag for tag in tags if tag in sample_job_listing.technologies]) >= 1


class TestAdaptedResumeDraft:
    """Test AdaptedResumeDraft model"""
    
    def test_create_adapted_resume_draft(self, db_session, sample_resume, sample_job_listing):
        """Test creating an adapted resume draft"""
        draft = AdaptedResumeDraft(
            original_resume_id=sample_resume.id,
            job_id=sample_job_listing.id,
            adapted_latex_content="\\documentclass{article}\\begin{document}Adapted Resume\\end{document}",
            is_user_edited=False
        )
        
        db_session.add(draft)
        db_session.commit()
        
        assert draft.id is not None
        assert draft.original_resume_id == sample_resume.id
        assert draft.job_id == sample_job_listing.id
        assert not draft.is_user_edited
    
    def test_mark_as_edited(self, db_session, sample_resume, sample_job_listing):
        """Test marking draft as user-edited"""
        draft = AdaptedResumeDraft(
            original_resume_id=sample_resume.id,
            job_id=sample_job_listing.id,
            adapted_latex_content="Content",
            is_user_edited=False
        )
        
        db_session.add(draft)
        db_session.commit()
        
        draft.mark_as_edited()
        db_session.commit()
        
        assert draft.is_user_edited
        assert draft.status == "User Modified"
    
    def test_status_property(self, db_session, sample_resume, sample_job_listing):
        """Test status property"""
        draft = AdaptedResumeDraft(
            original_resume_id=sample_resume.id,
            job_id=sample_job_listing.id,
            adapted_latex_content="Content",
            is_user_edited=False
        )
        
        assert draft.status == "AI Generated"
        
        draft.mark_as_edited()
        assert draft.status == "User Modified"


class TestJobMatch:
    """Test JobMatch model"""
    
    def test_create_job_match(self, db_session, sample_resume, sample_job_listing):
        """Test creating a job match"""
        match = JobMatch(
            resume_id=sample_resume.id,
            job_listing_id=sample_job_listing.id,
            compatibility_score=0.75,
            matching_keywords=["python", "sql"],
            missing_keywords=["django", "redis"],
            algorithm_version=1
        )
        
        db_session.add(match)
        db_session.commit()
        
        assert match.id is not None
        assert match.compatibility_score == 0.75
        assert match.resume_id == sample_resume.id
        assert match.job_listing_id == sample_job_listing.id
    
    def test_compatibility_percentage(self, db_session, sample_resume, sample_job_listing):
        """Test compatibility percentage calculation"""
        match = JobMatch(
            resume_id=sample_resume.id,
            job_listing_id=sample_job_listing.id,
            compatibility_score=0.756,
            matching_keywords=["python"],
            missing_keywords=["django"]
        )
        
        assert match.compatibility_percentage == 75.6
    
    def test_match_quality(self, db_session, sample_resume, sample_job_listing):
        """Test match quality assessment"""
        # Test excellent match
        match = JobMatch(
            resume_id=sample_resume.id,
            job_listing_id=sample_job_listing.id,
            compatibility_score=0.85,
            matching_keywords=["python"],
            missing_keywords=[]
        )
        assert match.match_quality == "Excellent"
        
        # Test good match
        match.compatibility_score = 0.65
        assert match.match_quality == "Good"
        
        # Test fair match
        match.compatibility_score = 0.45
        assert match.match_quality == "Fair"
        
        # Test poor match
        match.compatibility_score = 0.25
        assert match.match_quality == "Poor"
    
    def test_keyword_match_ratio(self, db_session, sample_resume, sample_job_listing):
        """Test keyword match ratio calculation"""
        match = JobMatch(
            resume_id=sample_resume.id,
            job_listing_id=sample_job_listing.id,
            compatibility_score=0.75,
            matching_keywords=["python", "sql"],  # 2 matching
            missing_keywords=["django", "redis"]  # 2 missing
        )
        
        # 2 matching out of 4 total = 0.5
        assert match.keyword_match_ratio == 0.5


class TestModelRelationships:
    """Test model relationships"""
    
    def test_resume_adapted_drafts_relationship(self, db_session, sample_resume, sample_job_listing):
        """Test resume to adapted drafts relationship"""
        draft = AdaptedResumeDraft(
            original_resume_id=sample_resume.id,
            job_id=sample_job_listing.id,
            adapted_latex_content="Content"
        )
        
        db_session.add(draft)
        db_session.commit()
        
        # Test relationship
        assert len(sample_resume.adapted_drafts) == 1
        assert sample_resume.adapted_drafts[0].id == draft.id
        assert draft.original_resume.id == sample_resume.id
    
    def test_job_listing_matches_relationship(self, db_session, sample_resume, sample_job_listing):
        """Test job listing to matches relationship"""
        match = JobMatch(
            resume_id=sample_resume.id,
            job_listing_id=sample_job_listing.id,
            compatibility_score=0.75,
            matching_keywords=["python"],
            missing_keywords=["django"]
        )
        
        db_session.add(match)
        db_session.commit()
        
        # Test relationship
        assert len(sample_job_listing.job_matches) == 1
        assert sample_job_listing.job_matches[0].id == match.id
        assert match.job_listing.id == sample_job_listing.id