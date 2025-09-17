"""
Integration tests for complete scraping workflow without mocks
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from job_matching_app.services.job_listing_service import JobListingService
from job_matching_app.services.data_freshness_checker import DataFreshnessChecker
from job_matching_app.services.scraping_integration_manager import ScrapingIntegrationManager
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.models.scraping_session import ScrapingSession, ScrapingStatus
from job_matching_app.database import Base


class TestScrapingWorkflowIntegration:
    """Integration tests for complete scraping workflow"""
    
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
    def freshness_checker(self, db_session):
        """Create DataFreshnessChecker with test database"""
        return DataFreshnessChecker(db_session=db_session)
    
    @pytest.fixture
    def scraping_manager(self, db_session):
        """Create ScrapingIntegrationManager with test database"""
        return ScrapingIntegrationManager(db_session=db_session)
    
    @pytest.fixture
    def job_service(self, db_session):
        """Create JobListingService with test database"""
        return JobListingService(db_session=db_session)
    
    def test_data_freshness_detection_empty_database(self, freshness_checker):
        """Test data freshness detection with empty database"""
        # Empty database should be considered stale
        assert freshness_checker.is_data_stale() is True
        assert freshness_checker.get_last_scrape_time() is None
        assert freshness_checker.get_total_job_count() == 0
        assert freshness_checker.should_auto_scrape() is True
        
        status = freshness_checker.get_data_freshness_status()
        assert status['has_data'] is False
        assert status['is_stale'] is True
        assert status['should_auto_scrape'] is True
        assert status['total_jobs'] == 0
    
    def test_data_freshness_detection_fresh_data(self, freshness_checker, db_session):
        """Test data freshness detection with fresh data"""
        # Add fresh job data
        fresh_job = JobListing(
            title="Fresh Python Job",
            company="Fresh Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python", "django"],
            description="This is a fresh job posting.",
            source_url="https://indeed.com/fresh-job",
            application_url="https://indeed.com/apply/fresh-job",
            source_site="indeed",
            scraped_at=datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        )
        db_session.add(fresh_job)
        db_session.commit()
        
        # Fresh data should not be stale
        assert freshness_checker.is_data_stale(threshold_hours=24) is False
        assert freshness_checker.get_last_scrape_time() is not None
        assert freshness_checker.get_total_job_count() == 1
        assert freshness_checker.should_auto_scrape(job_count_threshold=1) is False
        
        status = freshness_checker.get_data_freshness_status()
        assert status['has_data'] is True
        assert status['is_stale'] is False
        assert status['total_jobs'] == 1
        assert status['data_age_hours'] < 24
    
    def test_data_freshness_detection_stale_data(self, freshness_checker, db_session):
        """Test data freshness detection with stale data"""
        # Add stale job data
        stale_job = JobListing(
            title="Stale Python Job",
            company="Stale Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python", "django"],
            description="This is a stale job posting.",
            source_url="https://indeed.com/stale-job",
            application_url="https://indeed.com/apply/stale-job",
            source_site="indeed",
            scraped_at=datetime.utcnow() - timedelta(hours=48)  # 48 hours ago
        )
        db_session.add(stale_job)
        db_session.commit()
        
        # Stale data should trigger auto-scraping
        assert freshness_checker.is_data_stale(threshold_hours=24) is True
        assert freshness_checker.get_last_scrape_time() is not None
        assert freshness_checker.get_total_job_count() == 1
        assert freshness_checker.should_auto_scrape() is True
        
        status = freshness_checker.get_data_freshness_status()
        assert status['has_data'] is True
        assert status['is_stale'] is True
        assert status['should_auto_scrape'] is True
        assert status['data_age_hours'] > 24
    
    def test_scraping_session_tracking(self, scraping_manager, db_session):
        """Test scraping session creation and tracking"""
        # Mock the actual scraping to avoid web requests
        with patch.object(scraping_manager.scraping_service, 'scrape_indeed') as mock_indeed:
            with patch.object(scraping_manager.scraping_service, 'scrape_linkedin') as mock_linkedin:
                with patch.object(scraping_manager.scraping_service, 'save_jobs_to_database') as mock_save:
                    
                    # Mock successful scraping
                    mock_jobs = [
                        JobListing(
                            title="Test Job 1",
                            company="Test Company 1",
                            location="São Paulo, SP",
                            remote_type=RemoteType.REMOTE,
                            experience_level=ExperienceLevel.SENIOR,
                            technologies=["python"],
                            description="Test job description",
                            source_url="https://indeed.com/test1",
                            application_url="https://indeed.com/apply/test1",
                            source_site="indeed",
                            scraped_at=datetime.utcnow()
                        )
                    ]
                    
                    mock_indeed.return_value = mock_jobs
                    mock_linkedin.return_value = []
                    mock_save.return_value = 1
                    
                    # Trigger scraping
                    result = scraping_manager.scrape_with_progress(
                        keywords=['python'],
                        location='São Paulo',
                        max_pages=2
                    )
                    
                    # Verify scraping result
                    assert result['scraping_triggered'] is True
                    assert result['jobs_found'] == 1
                    assert result['jobs_saved'] == 1
                    assert len(result['errors']) == 0
                    assert result['success'] is True
                    
                    # Verify scraping session was created
                    sessions = db_session.query(ScrapingSession).all()
                    assert len(sessions) == 1
                    
                    session = sessions[0]
                    assert session.keywords == ['python']
                    assert session.location == 'São Paulo'
                    assert session.status == ScrapingStatus.COMPLETED
                    assert session.jobs_found == 1
                    assert session.jobs_saved == 1
    
    def test_scraping_error_handling_and_session_tracking(self, scraping_manager, db_session):
        """Test error handling during scraping with session tracking"""
        from job_matching_app.services.job_scraping_service import RateLimitError, SiteUnavailableError
        
        # Mock scraping with errors
        with patch.object(scraping_manager.scraping_service, 'scrape_indeed') as mock_indeed:
            with patch.object(scraping_manager.scraping_service, 'scrape_linkedin') as mock_linkedin:
                with patch.object(scraping_manager.scraping_service, 'save_jobs_to_database') as mock_save:
                    
                    # Mock Indeed success and LinkedIn failure
                    mock_jobs = [
                        JobListing(
                            title="Test Job",
                            company="Test Company",
                            location="São Paulo, SP",
                            remote_type=RemoteType.REMOTE,
                            experience_level=ExperienceLevel.SENIOR,
                            technologies=["python"],
                            description="Test job description",
                            source_url="https://indeed.com/test",
                            application_url="https://indeed.com/apply/test",
                            source_site="indeed",
                            scraped_at=datetime.utcnow()
                        )
                    ]
                    
                    mock_indeed.return_value = mock_jobs
                    mock_linkedin.side_effect = RateLimitError("Rate limit exceeded", "linkedin", 300)
                    mock_save.return_value = 1
                    
                    # Trigger scraping
                    result = scraping_manager.scrape_with_progress(
                        keywords=['python'],
                        location='São Paulo',
                        max_pages=2
                    )
                    
                    # Verify partial success
                    assert result['scraping_triggered'] is True
                    assert result['jobs_found'] == 1
                    assert result['jobs_saved'] == 1
                    assert len(result['errors']) == 1
                    assert 'Rate limit exceeded for LinkedIn' in result['errors'][0]
                    
                    # Verify scraping session was created and completed despite errors
                    sessions = db_session.query(ScrapingSession).all()
                    assert len(sessions) == 1
                    
                    session = sessions[0]
                    assert session.status == ScrapingStatus.COMPLETED
                    assert session.jobs_found == 1
                    assert session.jobs_saved == 1
                    assert len(session.errors) > 0
    
    def test_automatic_scraping_integration(self, job_service, db_session):
        """Test automatic scraping integration with job listing service"""
        # Mock the scraping to avoid web requests
        with patch.object(job_service.scraping_manager, 'auto_scrape_if_needed') as mock_auto_scrape:
            mock_auto_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 5,
                'jobs_saved': 5,
                'errors': []
            }
            
            # Request job listings from empty database (should trigger auto-scraping)
            job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
                auto_scrape=True,
                keywords=['python', 'django'],
                location='São Paulo'
            )
            
            # Verify auto-scraping was triggered
            mock_auto_scrape.assert_called_once_with(
                keywords=['python', 'django'],
                location='São Paulo',
                force_scrape=False,
                progress_callback=None
            )
            
            # Verify scraping result is returned
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
            assert scraping_result['jobs_found'] == 5
    
    def test_manual_scraping_with_progress_callback(self, job_service):
        """Test manual scraping with progress callback functionality"""
        progress_events = []
        
        def progress_callback(status, data):
            progress_events.append((status, data))
        
        # Mock the scraping manager
        with patch.object(job_service.scraping_manager, 'scrape_with_progress') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 8,
                'jobs_saved': 7,
                'errors': ['Minor error on one site']
            }
            
            # Trigger manual scraping
            result = job_service.trigger_scraping_with_feedback(
                keywords=['python', 'machine learning'],
                location='Rio de Janeiro',
                max_pages=5,
                progress_callback=progress_callback
            )
            
            # Verify scraping was called with correct parameters
            mock_scrape.assert_called_once_with(
                keywords=['python', 'machine learning'],
                location='Rio de Janeiro',
                max_pages=5,
                progress_callback=progress_callback
            )
            
            # Verify result
            assert result['scraping_triggered'] is True
            assert result['jobs_found'] == 8
            assert result['jobs_saved'] == 7
            assert len(result['errors']) == 1
    
    def test_scraping_status_monitoring(self, scraping_manager, db_session):
        """Test scraping status monitoring functionality"""
        # Add some test data to make status more interesting
        old_job = JobListing(
            title="Old Job",
            company="Old Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python"],
            description="Old job description",
            source_url="https://indeed.com/old",
            application_url="https://indeed.com/apply/old",
            source_site="indeed",
            scraped_at=datetime.utcnow() - timedelta(hours=36)
        )
        db_session.add(old_job)
        db_session.commit()
        
        # Get scraping status
        status = scraping_manager.get_scraping_status()
        
        # Verify status structure
        assert 'data_freshness' in status
        assert 'session_statistics' in status
        assert 'active_sessions' in status
        assert 'scraping_available' in status
        assert 'auto_scrape_enabled' in status
        
        # Verify data freshness info
        assert status['data_freshness']['total_jobs'] == 1
        assert status['data_freshness']['has_data'] is True
        assert status['data_freshness']['is_stale'] is True
        
        # Verify scraping availability
        assert status['scraping_available'] is True
        assert status['active_sessions'] == 0
    
    def test_end_to_end_scraping_workflow(self, job_service, db_session):
        """Test complete end-to-end scraping workflow"""
        # Step 1: Start with empty database
        assert db_session.query(JobListing).count() == 0
        
        # Step 2: Mock successful scraping
        mock_scraped_jobs = [
            JobListing(
                title=f"Python Developer {i}",
                company=f"Company {i}",
                location="São Paulo, SP",
                remote_type=RemoteType.REMOTE if i % 2 == 0 else RemoteType.ONSITE,
                experience_level=ExperienceLevel.SENIOR if i % 2 == 0 else ExperienceLevel.JUNIOR,
                technologies=["python", "django"] if i % 2 == 0 else ["python", "flask"],
                description=f"Job description {i}",
                source_url=f"https://indeed.com/job{i}",
                application_url=f"https://indeed.com/apply{i}",
                source_site="indeed",
                scraped_at=datetime.utcnow()
            )
            for i in range(1, 6)  # 5 jobs
        ]
        
        with patch.object(job_service.scraping_manager, 'auto_scrape_if_needed') as mock_auto_scrape:
            # Mock the auto-scrape to actually add jobs to database
            def mock_auto_scrape_side_effect(*args, **kwargs):
                for job in mock_scraped_jobs:
                    db_session.add(job)
                db_session.commit()
                return {
                    'scraping_triggered': True,
                    'jobs_found': 5,
                    'jobs_saved': 5,
                    'errors': []
                }
            
            mock_auto_scrape.side_effect = mock_auto_scrape_side_effect
            
            # Step 3: Request job listings (should trigger scraping)
            job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
                auto_scrape=True,
                keywords=['python'],
                per_page=3
            )
            
            # Step 4: Verify scraping was triggered and jobs are available
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
            assert scraping_result['jobs_found'] == 5
            
            # Verify jobs are now in database and returned
            assert total_count == 5
            assert len(job_listings) == 3  # First page with 3 items
            assert total_pages == 2  # 5 jobs / 3 per page = 2 pages
            
            # Step 5: Test second page
            job_listings_page2, _, _, scraping_result2 = job_service.get_job_listings_paginated(
                page=2,
                per_page=3,
                auto_scrape=False  # Should not trigger scraping again
            )
            
            assert len(job_listings_page2) == 2  # Remaining 2 jobs
            assert scraping_result2 is None  # No scraping needed
            
            # Step 6: Test search functionality
            search_results, search_count, _, _ = job_service.search_jobs(
                "Python", auto_scrape=False
            )
            
            assert search_count == 5  # All jobs contain "Python"
            
            # Step 7: Test filtering
            filter_results, filter_count, _, _ = job_service.get_job_listings_paginated(
                filters={'remote_type': RemoteType.REMOTE},
                auto_scrape=False
            )
            
            # Should find remote jobs (every even-numbered job)
            expected_remote_count = len([j for j in mock_scraped_jobs if j.remote_type == RemoteType.REMOTE])
            assert filter_count == expected_remote_count
            
            # Step 8: Verify data freshness is now good
            freshness_status = job_service.get_data_freshness_status()
            assert freshness_status['has_data'] is True
            assert freshness_status['total_jobs'] == 5
            assert freshness_status['is_stale'] is False  # Fresh data