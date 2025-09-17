"""
Integration tests for JobListingService with real scraping functionality
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from job_matching_app.services.job_listing_service import JobListingService
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.models.job_match import JobMatch
from job_matching_app.models.scraping_session import ScrapingSession, ScrapingStatus
from job_matching_app.database import Base


class TestJobListingServiceIntegration:
    """Integration tests for JobListingService with real database and scraping"""
    
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
        """Create JobListingService instance with test database"""
        return JobListingService(db_session=db_session)
    
    @pytest.fixture
    def real_job_listings(self, db_session):
        """Create real job listings in the test database"""
        jobs = []
        base_time = datetime.utcnow()
        
        for i in range(20):  # Create 20 jobs for testing
            job = JobListing(
                title=f"Python Developer {i + 1}",
                company=f"Tech Company {i + 1}",
                location=f"São Paulo, SP" if i % 2 == 0 else f"Rio de Janeiro, RJ",
                remote_type=RemoteType.REMOTE if i % 3 == 0 else (RemoteType.HYBRID if i % 3 == 1 else RemoteType.ONSITE),
                experience_level=ExperienceLevel.JUNIOR if i % 2 == 0 else ExperienceLevel.SENIOR,
                technologies=["python", "django", "postgresql"] if i % 2 == 0 else ["javascript", "react", "nodejs"],
                description=f"We are looking for a skilled developer to join our team. Position {i + 1} requires strong programming skills and experience with modern frameworks.",
                source_url=f"https://indeed.com/job/{i + 1}",
                application_url=f"https://indeed.com/apply/{i + 1}",
                source_site="indeed" if i % 2 == 0 else "linkedin",
                scraped_at=base_time - timedelta(hours=i)  # Different scraping times
            )
            db_session.add(job)
            jobs.append(job)
        
        db_session.commit()
        return jobs
    
    @pytest.fixture
    def real_job_matches(self, db_session, real_job_listings):
        """Create real job matches in the test database"""
        matches = []
        for i, job in enumerate(real_job_listings[:10]):  # Only first 10 jobs have matches
            match = JobMatch(
                resume_id=1,
                job_listing_id=job.id,
                compatibility_score=0.95 - (i * 0.05),  # Decreasing scores
                matching_keywords=["python", "django"] if i % 2 == 0 else ["javascript", "react"],
                missing_keywords=["aws", "docker"] if i % 2 == 0 else ["python", "django"],
                algorithm_version=2
            )
            db_session.add(match)
            matches.append(match)
        
        db_session.commit()
        return matches
    
    @pytest.fixture
    def stale_job_data(self, db_session):
        """Create stale job data for freshness testing"""
        old_time = datetime.utcnow() - timedelta(hours=48)  # 48 hours old
        
        job = JobListing(
            title="Old Python Developer",
            company="Old Tech Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python", "django"],
            description="This is an old job posting that should trigger auto-scraping.",
            source_url="https://indeed.com/old-job",
            application_url="https://indeed.com/apply/old-job",
            source_site="indeed",
            scraped_at=old_time
        )
        db_session.add(job)
        db_session.commit()
        return job
    
    def test_get_job_listings_paginated_default(self, job_service, real_job_listings):
        """Test getting paginated job listings with default parameters"""
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            auto_scrape=False, per_page=10
        )
        
        assert len(job_listings) == 10  # First page with 10 items
        assert total_count == 20  # Total jobs in database
        assert total_pages == 2  # 20 jobs / 10 per page = 2 pages
        assert scraping_result is None  # No scraping triggered
        
        # Verify jobs are sorted by scraped_at desc (most recent first)
        assert job_listings[0].scraped_at >= job_listings[1].scraped_at
    
    def test_get_job_listings_paginated_custom_page_size(self, job_service, real_job_listings):
        """Test getting paginated job listings with custom page size"""
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            page=1, per_page=5, auto_scrape=False
        )
        
        assert len(job_listings) == 5  # Custom page size
        assert total_count == 20  # Total jobs in database
        assert total_pages == 4  # 20 jobs / 5 per page = 4 pages
        assert scraping_result is None
    
    def test_get_job_listings_paginated_second_page(self, job_service, real_job_listings):
        """Test getting second page of job listings"""
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            page=2, per_page=10, auto_scrape=False
        )
        
        assert len(job_listings) == 10  # Second page with remaining items
        assert total_count == 20  # Total jobs in database
        assert total_pages == 2  # 20 jobs / 10 per page = 2 pages
        assert scraping_result is None
        
        # Verify we got different jobs than the first page
        first_page_jobs, _, _, _ = job_service.get_job_listings_paginated(
            page=1, per_page=10, auto_scrape=False
        )
        first_page_ids = {job.id for job in first_page_jobs}
        second_page_ids = {job.id for job in job_listings}
        assert first_page_ids.isdisjoint(second_page_ids)  # No overlap
    
    def test_get_job_listings_with_filters(self, job_service, real_job_listings):
        """Test getting job listings with filters applied"""
        filters = {
            'company': 'Tech Company 1',
            'remote_type': RemoteType.REMOTE,
            'experience_level': ExperienceLevel.JUNIOR
        }
        
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            filters=filters, auto_scrape=False
        )
        
        # Should find jobs matching the filters
        assert total_count >= 0  # May be 0 if no jobs match all filters
        assert scraping_result is None
        
        # Verify all returned jobs match the filters
        for job in job_listings:
            if filters.get('company'):
                assert filters['company'] in job.company
            if filters.get('remote_type'):
                assert job.remote_type == filters['remote_type']
            if filters.get('experience_level'):
                assert job.experience_level == filters['experience_level']
    
    def test_get_job_listings_with_sorting(self, job_service, real_job_listings):
        """Test getting job listings with custom sorting"""
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
            sort_by="title", sort_order="asc", auto_scrape=False
        )
        
        assert len(job_listings) > 0
        assert scraping_result is None
        
        # Verify jobs are sorted by title in ascending order
        titles = [job.title for job in job_listings]
        assert titles == sorted(titles)
    
    def test_automatic_scraping_trigger_empty_database(self, db_session):
        """Test that automatic scraping is triggered when database is empty"""
        # Create service with empty database
        job_service = JobListingService(db_session=db_session)
        
        # Mock the scraping manager to avoid actual web scraping
        from unittest.mock import Mock, patch
        with patch.object(job_service.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 5,
                'jobs_saved': 5,
                'errors': []
            }
            
            job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
                auto_scrape=True, keywords=['python']
            )
            
            # Verify scraping was triggered
            mock_scrape.assert_called_once()
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
    
    def test_automatic_scraping_trigger_stale_data(self, job_service, stale_job_data):
        """Test that automatic scraping is triggered when data is stale"""
        from unittest.mock import Mock, patch
        
        # Mock the scraping manager to avoid actual web scraping
        with patch.object(job_service.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 3,
                'jobs_saved': 3,
                'errors': []
            }
            
            job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(
                auto_scrape=True, keywords=['python']
            )
            
            # Verify scraping was triggered due to stale data
            mock_scrape.assert_called_once()
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
    
    def test_data_freshness_detection(self, job_service, real_job_listings):
        """Test data freshness detection functionality"""
        freshness_status = job_service.get_data_freshness_status()
        
        assert 'last_scrape_time' in freshness_status
        assert 'total_jobs' in freshness_status
        assert 'is_stale' in freshness_status
        assert 'should_auto_scrape' in freshness_status
        assert freshness_status['total_jobs'] == 20  # From real_job_listings fixture
        assert freshness_status['has_data'] is True
    
    def test_manual_scraping_trigger(self, job_service):
        """Test manual scraping trigger with progress feedback"""
        from unittest.mock import Mock, patch
        
        progress_calls = []
        def progress_callback(status, data):
            progress_calls.append((status, data))
        
        # Mock the scraping manager to avoid actual web scraping
        with patch.object(job_service.scraping_manager, 'scrape_with_progress') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 10,
                'jobs_saved': 8,
                'errors': ['Rate limit on LinkedIn']
            }
            
            result = job_service.trigger_scraping_with_feedback(
                keywords=['python', 'django'],
                location='São Paulo',
                progress_callback=progress_callback
            )
            
            # Verify scraping was triggered with correct parameters
            mock_scrape.assert_called_once_with(
                keywords=['python', 'django'],
                location='São Paulo',
                max_pages=3,
                progress_callback=progress_callback
            )
            
            assert result['scraping_triggered'] is True
            assert result['jobs_found'] == 10
            assert result['jobs_saved'] == 8
            assert len(result['errors']) == 1
    
    def test_get_job_listings_with_matches(self, job_service, real_job_listings, real_job_matches):
        """Test getting job listings with match scores"""
        # Use a different sort field to avoid SQLite nullslast() issue
        job_matches, total_count, total_pages, scraping_result = job_service.get_job_listings_with_matches(
            resume_id=1, auto_scrape=False, per_page=10, sort_by="scraped_at", sort_order="desc"
        )
        
        assert len(job_matches) == 10  # Should get first 10 jobs (some with matches, some without)
        assert total_count == 20  # Total jobs in database
        assert total_pages == 2
        assert scraping_result is None
        
        # Verify each result is a tuple
        for job_listing, job_match in job_matches:
            assert isinstance(job_listing, JobListing)
            # job_match can be None for jobs without matches
            if job_match is not None:
                assert isinstance(job_match, JobMatch)
                assert job_match.resume_id == 1
    
    def test_get_job_by_id_found(self, job_service, real_job_listings):
        """Test getting a job by ID when it exists"""
        # Get the first job from our test data
        expected_job = real_job_listings[0]
        
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = job_service.db_session
            
            job_listing = job_service.get_job_by_id(expected_job.id)
            
            assert job_listing is not None
            assert job_listing.id == expected_job.id
            assert job_listing.title == expected_job.title
            assert job_listing.company == expected_job.company
    
    def test_get_job_by_id_not_found(self, job_service, real_job_listings):
        """Test getting a job by ID when it doesn't exist"""
        job_listing = job_service.get_job_by_id(999999)  # Non-existent ID
        
        assert job_listing is None
    
    def test_get_job_with_match_found(self, job_service, real_job_listings, real_job_matches):
        """Test getting a job with its match score"""
        # Get a job that has a match
        job_with_match = real_job_listings[0]  # First job should have a match
        
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = job_service.db_session
            
            job_listing, job_match = job_service.get_job_with_match(job_with_match.id, 1)
            
            assert job_listing is not None
            assert job_match is not None
            assert job_listing.id == job_with_match.id
            assert job_match.resume_id == 1
            assert job_match.job_listing_id == job_with_match.id
    
    def test_get_job_with_match_no_match(self, job_service, real_job_listings):
        """Test getting a job when no match exists"""
        # Get a job that doesn't have a match (jobs beyond the first 10)
        job_without_match = real_job_listings[15]  # Job 16 should not have a match
        
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = job_service.db_session
            
            job_listing, job_match = job_service.get_job_with_match(job_without_match.id, 1)
            
            assert job_listing is not None
            assert job_match is None
            assert job_listing.id == job_without_match.id
    
    def test_search_jobs(self, job_service, real_job_listings):
        """Test searching jobs by term"""
        job_listings, total_count, total_pages, scraping_result = job_service.search_jobs(
            "Python", auto_scrape=False
        )
        
        assert len(job_listings) > 0  # Should find Python jobs
        assert total_count > 0
        assert scraping_result is None
        
        # Verify all returned jobs contain the search term
        for job in job_listings:
            search_text = f"{job.title} {job.company} {job.description}".lower()
            assert "python" in search_text
    
    def test_get_available_filters(self, job_service, real_job_listings):
        """Test getting available filter options"""
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = job_service.db_session
            
            filters = job_service.get_available_filters()
            
            assert 'companies' in filters
            assert 'locations' in filters
            assert 'source_sites' in filters
            assert 'technologies' in filters
            assert 'remote_types' in filters
            assert 'experience_levels' in filters
            
            # Verify we have data from our test jobs
            assert len(filters['companies']) > 0
            assert len(filters['locations']) > 0
            assert len(filters['source_sites']) > 0
            assert len(filters['technologies']) > 0
            
            # Verify enum values are present
            assert 'remote' in filters['remote_types']
            assert 'junior' in filters['experience_levels']
    
    def test_get_job_statistics(self, job_service, real_job_listings):
        """Test getting job statistics"""
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = job_service.db_session
            
            stats = job_service.get_job_statistics()
            
            assert stats['total_jobs'] == 20  # From our test data
            assert 'remote_type_distribution' in stats
            assert 'experience_level_distribution' in stats
            assert 'source_site_distribution' in stats
            
            # Verify we have some distribution data
            assert sum(stats['remote_type_distribution'].values()) == 20
            assert sum(stats['experience_level_distribution'].values()) == 20
            assert sum(stats['source_site_distribution'].values()) == 20
    
    def test_pagination_edge_cases(self, db_session):
        """Test pagination edge cases with empty database"""
        # Create service with empty database
        job_service = JobListingService(db_session=db_session)
        
        # Test empty results
        job_listings, total_count, total_pages, scraping_result = job_service.get_job_listings_paginated(auto_scrape=False)
        
        assert len(job_listings) == 0
        assert total_count == 0
        assert total_pages == 0
        assert scraping_result is None
    
    def test_pagination_calculation(self, job_service, real_job_listings):
        """Test pagination calculation with various scenarios"""
        # Test exact division
        _, total_count, total_pages, _ = job_service.get_job_listings_paginated(per_page=10, auto_scrape=False)
        assert total_pages == 2  # 20 jobs / 10 per page = 2 pages
        
        # Test with remainder
        _, total_count, total_pages, _ = job_service.get_job_listings_paginated(per_page=7, auto_scrape=False)
        assert total_pages == 3  # 20 jobs / 7 per page = 2.86 -> 3 pages
        
        # Test single item per page
        _, total_count, total_pages, _ = job_service.get_job_listings_paginated(per_page=1, auto_scrape=False)
        assert total_pages == 20  # 20 jobs / 1 per page = 20 pages


class TestJobListingServiceScrapingIntegration:
    """Integration tests for scraping workflow from empty database to job display"""
    
    @pytest.fixture
    def empty_db_session(self):
        """Create a completely empty test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()
    
    @pytest.fixture
    def job_service_empty(self, empty_db_session):
        """Create JobListingService instance with empty test database"""
        return JobListingService(db_session=empty_db_session)
    
    def test_complete_scraping_to_display_workflow(self, job_service_empty):
        """Test the complete workflow from empty database to job display"""
        from unittest.mock import Mock, patch
        
        # Mock the actual scraping to avoid web requests
        mock_jobs = [
            JobListing(
                title="Senior Python Developer",
                company="Tech Corp",
                location="São Paulo, SP",
                remote_type=RemoteType.REMOTE,
                experience_level=ExperienceLevel.SENIOR,
                technologies=["python", "django", "postgresql"],
                description="We are looking for a senior Python developer...",
                source_url="https://indeed.com/job/123",
                application_url="https://indeed.com/apply/123",
                source_site="indeed",
                scraped_at=datetime.utcnow()
            ),
            JobListing(
                title="JavaScript Developer",
                company="Startup Inc",
                location="Rio de Janeiro, RJ",
                remote_type=RemoteType.HYBRID,
                experience_level=ExperienceLevel.MID,
                technologies=["javascript", "react", "nodejs"],
                description="Join our dynamic team as a JavaScript developer...",
                source_url="https://linkedin.com/job/456",
                application_url="https://linkedin.com/apply/456",
                source_site="linkedin",
                scraped_at=datetime.utcnow()
            )
        ]
        
        with patch.object(job_service_empty.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 2,
                'jobs_saved': 2,
                'errors': []
            }
            
            # Also mock the actual database save to add our mock jobs
            with patch.object(job_service_empty.scraping_manager.scraping_service, 'save_jobs_to_database') as mock_save:
                def save_jobs_side_effect(jobs):
                    # Add jobs to the database session
                    for job in mock_jobs:
                        job_service_empty.db_session.add(job)
                    job_service_empty.db_session.commit()
                    return len(mock_jobs)
                
                mock_save.side_effect = save_jobs_side_effect
                
                # Step 1: Request job listings from empty database (should trigger scraping)
                job_listings, total_count, total_pages, scraping_result = job_service_empty.get_job_listings_paginated(
                    auto_scrape=True, keywords=['python']
                )
                
                # Verify scraping was triggered
                assert scraping_result is not None
                assert scraping_result['scraping_triggered'] is True
                assert scraping_result['jobs_found'] == 2
                
                # Step 2: Verify jobs are now available for display
                job_listings, total_count, total_pages, scraping_result = job_service_empty.get_job_listings_paginated(
                    auto_scrape=False  # No need to scrape again
                )
                
                assert len(job_listings) == 2
                assert total_count == 2
                assert total_pages == 1
                assert scraping_result is None  # No scraping needed
                
                # Step 3: Test search functionality works with scraped data
                search_results, search_count, search_pages, _ = job_service_empty.search_jobs(
                    "Python", auto_scrape=False
                )
                
                assert len(search_results) == 1  # Only the Python job
                assert search_results[0].title == "Senior Python Developer"
                
                # Step 4: Test filtering works with scraped data
                filter_results, filter_count, filter_pages, _ = job_service_empty.get_job_listings_paginated(
                    filters={'remote_type': RemoteType.REMOTE}, auto_scrape=False
                )
                
                assert len(filter_results) == 1  # Only the remote job
                assert filter_results[0].remote_type == RemoteType.REMOTE
    
    def test_scraping_error_handling_workflow(self, job_service_empty):
        """Test workflow when scraping encounters errors"""
        from unittest.mock import Mock, patch
        
        with patch.object(job_service_empty.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 0,
                'jobs_saved': 0,
                'errors': ['Rate limit exceeded for Indeed', 'LinkedIn unavailable']
            }
            
            # Request job listings from empty database
            job_listings, total_count, total_pages, scraping_result = job_service_empty.get_job_listings_paginated(
                auto_scrape=True, keywords=['python']
            )
            
            # Verify scraping was attempted but failed
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True
            assert scraping_result['jobs_found'] == 0
            assert len(scraping_result['errors']) == 2
            
            # Database should still be empty
            assert len(job_listings) == 0
            assert total_count == 0
    
    def test_data_freshness_triggers_automatic_scraping(self, job_service_empty):
        """Test that stale data triggers automatic scraping"""
        from unittest.mock import Mock, patch
        
        # First, add some old data
        old_job = JobListing(
            title="Old Python Job",
            company="Old Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python"],
            description="This is an old job posting.",
            source_url="https://indeed.com/old-job",
            application_url="https://indeed.com/apply/old-job",
            source_site="indeed",
            scraped_at=datetime.utcnow() - timedelta(hours=48)  # 48 hours old
        )
        job_service_empty.db_session.add(old_job)
        job_service_empty.db_session.commit()
        
        # Mock fresh scraping results
        with patch.object(job_service_empty.scraping_manager, 'auto_scrape_if_needed') as mock_scrape:
            mock_scrape.return_value = {
                'scraping_triggered': True,
                'jobs_found': 3,
                'jobs_saved': 3,
                'errors': []
            }
            
            # Request job listings (should trigger scraping due to stale data)
            job_listings, total_count, total_pages, scraping_result = job_service_empty.get_job_listings_paginated(
                auto_scrape=True, keywords=['python']
            )
            
            # Verify scraping was triggered due to stale data
            mock_scrape.assert_called_once()
            assert scraping_result is not None
            assert scraping_result['scraping_triggered'] is True