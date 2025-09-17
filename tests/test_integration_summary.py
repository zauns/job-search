"""
Summary test demonstrating the integration tests without mocks
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from job_matching_app.services.job_listing_service import JobListingService
from job_matching_app.services.data_freshness_checker import DataFreshnessChecker
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.database import Base


class TestIntegrationSummary:
    """Summary of integration tests demonstrating real functionality without mocks"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()
    
    @pytest.fixture
    def job_service(self, db_session):
        """Create JobListingService with test database"""
        return JobListingService(db_session=db_session)
    
    @pytest.fixture
    def sample_jobs(self, db_session):
        """Create sample jobs in the database"""
        jobs = []
        for i in range(5):
            job = JobListing(
                title=f"Python Developer {i+1}",
                company=f"Tech Company {i+1}",
                location="São Paulo, SP",
                remote_type=RemoteType.REMOTE if i % 2 == 0 else RemoteType.ONSITE,
                experience_level=ExperienceLevel.SENIOR if i % 2 == 0 else ExperienceLevel.JUNIOR,
                technologies=["python", "django"],
                description=f"Job description {i+1}",
                source_url=f"https://indeed.com/job{i+1}",
                application_url=f"https://indeed.com/apply{i+1}",
                source_site="indeed",
                scraped_at=datetime.utcnow() - timedelta(hours=i)
            )
            db_session.add(job)
            jobs.append(job)
        
        db_session.commit()
        return jobs
    
    def test_real_database_operations(self, job_service, sample_jobs):
        """Test that we can perform real database operations without mocks"""
        # Test pagination with real database
        jobs, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            auto_scrape=False, per_page=3
        )
        
        assert len(jobs) == 3  # First page
        assert total_count == 5  # Total jobs
        assert total_pages == 2  # 5 jobs / 3 per page = 2 pages
        assert scraping_result is None  # No scraping triggered
        
        # Test search with real database
        search_results, search_count, _, _ = job_service.search_jobs("Python", auto_scrape=False)
        assert search_count == 5  # All jobs contain "Python"
        
        # Test filtering with real database
        filter_results, filter_count, _, _ = job_service.get_job_listings_paginated(
            filters={'remote_type': RemoteType.REMOTE}, auto_scrape=False
        )
        assert filter_count == 3  # Jobs with even indices are remote
    
    def test_data_freshness_detection_real(self, db_session):
        """Test real data freshness detection without mocks"""
        freshness_checker = DataFreshnessChecker(db_session=db_session)
        
        # Empty database should be stale
        assert freshness_checker.is_data_stale() is True
        assert freshness_checker.get_total_job_count() == 0
        assert freshness_checker.should_auto_scrape() is True
        
        # Add fresh job
        fresh_job = JobListing(
            title="Fresh Job",
            company="Fresh Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python"],
            description="Fresh job description",
            source_url="https://indeed.com/fresh",
            application_url="https://indeed.com/apply/fresh",
            source_site="indeed",
            scraped_at=datetime.utcnow() - timedelta(hours=1)  # 1 hour ago
        )
        db_session.add(fresh_job)
        db_session.commit()
        
        # Now should not be stale
        assert freshness_checker.is_data_stale(threshold_hours=24) is False
        assert freshness_checker.get_total_job_count() == 1
        assert freshness_checker.should_auto_scrape(job_count_threshold=1) is False
    
    def test_automatic_scraping_trigger_integration(self, job_service):
        """Test that automatic scraping is properly integrated"""
        # Mock only the actual web scraping to avoid network calls
        with patch.object(job_service.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 3,
                'jobs_saved': 3,
                'errors': []
            }
            
            # Request jobs from empty database - should trigger scraping
            jobs, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
                auto_scrape=True, keywords=['python']
            )
            
            # Verify scraping was triggered
            mock_scrape.assert_called_once()
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
            assert scraping_result['jobs_found'] == 3
    
    def test_error_scenarios_without_mocks(self, job_service):
        """Test error scenarios with real error handling"""
        # Test with invalid job ID
        job = job_service.get_job_by_id(999999)
        assert job is None
        
        # Test empty search results
        search_results, search_count, _, _ = job_service.search_jobs(
            "very-unlikely-search-term-12345", auto_scrape=False
        )
        assert search_count == 0
        assert len(search_results) == 0
        
        # Test pagination edge cases
        jobs, total_count, total_pages, _ = job_service.get_job_listings_paginated(
            page=999, per_page=10, auto_scrape=False
        )
        assert len(jobs) == 0  # No jobs on non-existent page
        assert total_count == 0  # Empty database
        assert total_pages == 0