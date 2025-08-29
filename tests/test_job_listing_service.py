"""
Unit tests for JobListingService
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from job_matching_app.services.job_listing_service import JobListingService
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.models.job_match import JobMatch


class TestJobListingService:
    """Test cases for JobListingService"""
    
    @pytest.fixture
    def job_service(self):
        """Create JobListingService instance"""
        return JobListingService()
    
    @pytest.fixture
    def sample_job_listings(self):
        """Create sample job listings for testing"""
        jobs = []
        for i in range(50):  # Create 50 jobs for pagination testing
            job = JobListing(
                id=i + 1,
                title=f"Software Engineer {i + 1}",
                company=f"Company {i + 1}",
                location=f"City {i % 5}",  # 5 different cities
                remote_type=RemoteType.REMOTE if i % 3 == 0 else RemoteType.ONSITE,
                experience_level=ExperienceLevel.JUNIOR if i % 2 == 0 else ExperienceLevel.SENIOR,
                technologies=["Python", "Django"] if i % 2 == 0 else ["JavaScript", "React"],
                description=f"Job description for position {i + 1}",
                source_url=f"https://example.com/job/{i + 1}",
                application_url=f"https://example.com/apply/{i + 1}",
                source_site="indeed" if i % 2 == 0 else "linkedin",
                scraped_at=datetime.now()
            )
            jobs.append(job)
        return jobs
    
    @pytest.fixture
    def sample_job_matches(self, sample_job_listings):
        """Create sample job matches for testing"""
        matches = []
        for i, job in enumerate(sample_job_listings[:10]):  # Only first 10 jobs have matches
            match = JobMatch(
                id=i + 1,
                resume_id=1,
                job_listing_id=job.id,
                compatibility_score=0.9 - (i * 0.1),  # Decreasing scores
                matching_keywords=["python", "django"],
                missing_keywords=["react", "javascript"],
                algorithm_version=2
            )
            matches.append(match)
        return matches
    
    def test_get_job_listings_paginated_default(self, job_service, sample_job_listings):
        """Test getting paginated job listings with default parameters"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = len(sample_job_listings)
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[:30]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated()
            
            assert len(job_listings) == 30
            assert total_count == 50
            assert total_pages == 2
    
    def test_get_job_listings_paginated_custom_page_size(self, job_service, sample_job_listings):
        """Test getting paginated job listings with custom page size"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = len(sample_job_listings)
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[:10]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
                page=1, per_page=10
            )
            
            assert len(job_listings) == 10
            assert total_count == 50
            assert total_pages == 5
    
    def test_get_job_listings_paginated_second_page(self, job_service, sample_job_listings):
        """Test getting second page of job listings"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = len(sample_job_listings)
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[10:20]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
                page=2, per_page=10
            )
            
            # Verify offset was called with correct value
            mock_query.offset.assert_called_with(10)
            mock_query.offset.return_value.limit.assert_called_with(10)
    
    def test_get_job_listings_with_filters(self, job_service, sample_job_listings):
        """Test getting job listings with filters applied"""
        filters = {
            'company': 'Company 1',
            'remote_type': 'remote',
            'experience_level': 'junior'
        }
        
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = 5
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[:5]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
                filters=filters
            )
            
            # Verify filters were applied (check that filter methods were called)
            assert mock_query.filter.call_count >= 3  # At least 3 filters applied
    
    def test_get_job_listings_with_sorting(self, job_service, sample_job_listings):
        """Test getting job listings with custom sorting"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = len(sample_job_listings)
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[:30]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
                sort_by="title", sort_order="asc"
            )
            
            # Verify order_by was called
            mock_query.order_by.assert_called()
    
    def test_get_job_listings_with_matches(self, job_service, sample_job_listings, sample_job_matches):
        """Test getting job listings with match scores"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = 10
            
            # Mock the query result to return tuples of (JobListing, JobMatch)
            mock_results = [(sample_job_listings[i], sample_job_matches[i]) for i in range(10)]
            mock_query.offset.return_value.limit.return_value.all.return_value = mock_results
            
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_matches, total_count, total_pages = job_service.get_job_listings_with_matches(
                resume_id=1
            )
            
            assert len(job_matches) == 10
            assert total_count == 10
            assert total_pages == 1
            
            # Verify each result is a tuple
            for job_listing, job_match in job_matches:
                assert isinstance(job_listing, JobListing)
                assert isinstance(job_match, JobMatch)
    
    def test_get_job_by_id_found(self, job_service, sample_job_listings):
        """Test getting a job by ID when it exists"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = sample_job_listings[0]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listing = job_service.get_job_by_id(1)
            
            assert job_listing is not None
            assert job_listing.id == 1
            assert job_listing.title == "Software Engineer 1"
    
    def test_get_job_by_id_not_found(self, job_service):
        """Test getting a job by ID when it doesn't exist"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listing = job_service.get_job_by_id(999)
            
            assert job_listing is None
    
    def test_get_job_with_match_found(self, job_service, sample_job_listings, sample_job_matches):
        """Test getting a job with its match score"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = (sample_job_listings[0], sample_job_matches[0])
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listing, job_match = job_service.get_job_with_match(1, 1)
            
            assert job_listing is not None
            assert job_match is not None
            assert job_listing.id == 1
            assert job_match.resume_id == 1
    
    def test_get_job_with_match_no_match(self, job_service, sample_job_listings):
        """Test getting a job when no match exists"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            # First query returns None (no match), second query returns job
            mock_query.filter.return_value.first.side_effect = [None, sample_job_listings[0]]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listing, job_match = job_service.get_job_with_match(1, 1)
            
            assert job_listing is not None
            assert job_match is None
            assert job_listing.id == 1
    
    def test_search_jobs(self, job_service, sample_job_listings):
        """Test searching jobs by term"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = 5
            mock_query.offset.return_value.limit.return_value.all.return_value = sample_job_listings[:5]
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            job_listings, total_count, total_pages = job_service.search_jobs("Engineer")
            
            assert len(job_listings) == 5
            assert total_count == 5
            assert total_pages == 1
            
            # Verify filter was applied for search
            mock_query.filter.assert_called()
    
    def test_get_available_filters(self, job_service):
        """Test getting available filter options"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_session_obj = Mock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            # Mock distinct queries
            mock_session_obj.query.return_value.distinct.return_value.order_by.return_value.all.side_effect = [
                [("Company A",), ("Company B",)],  # companies
                [("City A",), ("City B",)],         # locations
                [("indeed",), ("linkedin",)]        # source_sites
            ]
            
            # Mock technologies query
            mock_session_obj.query.return_value.filter.return_value.all.return_value = [
                (["Python", "Django"],),
                (["JavaScript", "React"],)
            ]
            
            filters = job_service.get_available_filters()
            
            assert 'companies' in filters
            assert 'locations' in filters
            assert 'source_sites' in filters
            assert 'technologies' in filters
            assert 'remote_types' in filters
            assert 'experience_levels' in filters
            
            assert len(filters['companies']) == 2
            assert len(filters['locations']) == 2
            assert len(filters['source_sites']) == 2
            assert len(filters['technologies']) == 4  # Flattened from both lists
    
    def test_get_job_statistics(self, job_service):
        """Test getting job statistics"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_session_obj = Mock()
            mock_session.return_value.__enter__.return_value = mock_session_obj
            
            # Mock total count
            mock_session_obj.query.return_value.count.return_value = 100
            
            # Mock group by queries
            mock_session_obj.query.return_value.group_by.return_value.all.side_effect = [
                [(RemoteType.REMOTE, 60), (RemoteType.ONSITE, 40)],  # remote_type
                [(ExperienceLevel.JUNIOR, 30), (ExperienceLevel.SENIOR, 70)],  # experience_level
                [("indeed", 50), ("linkedin", 50)]  # source_site
            ]
            
            stats = job_service.get_job_statistics()
            
            assert stats['total_jobs'] == 100
            assert 'remote_type_distribution' in stats
            assert 'experience_level_distribution' in stats
            assert 'source_site_distribution' in stats
            
            assert stats['remote_type_distribution'][RemoteType.REMOTE] == 60
            assert stats['experience_level_distribution'][ExperienceLevel.JUNIOR] == 30
            assert stats['source_site_distribution']['indeed'] == 50
    
    def test_apply_filters_company(self, job_service):
        """Test applying company filter"""
        mock_query = Mock()
        filters = {'company': 'Test Company'}
        
        result_query = job_service._apply_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_filters_multiple(self, job_service):
        """Test applying multiple filters"""
        mock_query = Mock()
        filters = {
            'company': 'Test Company',
            'location': 'Test City',
            'remote_type': 'remote',
            'experience_level': 'junior'
        }
        
        result_query = job_service._apply_filters(mock_query, filters)
        
        # Should have called filter multiple times
        assert mock_query.filter.call_count >= 4
    
    def test_apply_filters_technologies(self, job_service):
        """Test applying technologies filter"""
        mock_query = Mock()
        filters = {'technologies': ['Python', 'Django']}
        
        result_query = job_service._apply_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_sorting_default(self, job_service):
        """Test applying default sorting"""
        mock_query = Mock()
        
        result_query = job_service._apply_sorting(mock_query, "scraped_at", "desc")
        
        mock_query.order_by.assert_called()
    
    def test_apply_sorting_ascending(self, job_service):
        """Test applying ascending sort"""
        mock_query = Mock()
        
        result_query = job_service._apply_sorting(mock_query, "title", "asc")
        
        mock_query.order_by.assert_called()
    
    def test_apply_sorting_with_matches_compatibility(self, job_service):
        """Test applying sorting with compatibility score"""
        mock_query = Mock()
        
        result_query = job_service._apply_sorting_with_matches(mock_query, "compatibility_score", "desc")
        
        mock_query.order_by.assert_called()
    
    def test_pagination_edge_cases(self, job_service):
        """Test pagination edge cases"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_query.count.return_value = 0  # No results
            mock_query.offset.return_value.limit.return_value.all.return_value = []
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            # Test empty results
            job_listings, total_count, total_pages = job_service.get_job_listings_paginated()
            
            assert len(job_listings) == 0
            assert total_count == 0
            assert total_pages == 0
    
    def test_pagination_calculation(self, job_service):
        """Test pagination calculation with various scenarios"""
        with patch('job_matching_app.services.job_listing_service.get_db_context') as mock_session:
            mock_query = Mock()
            mock_session.return_value.__enter__.return_value.query.return_value = mock_query
            
            # Test exact division
            mock_query.count.return_value = 60
            mock_query.offset.return_value.limit.return_value.all.return_value = []
            
            _, total_count, total_pages = job_service.get_job_listings_paginated(per_page=30)
            assert total_pages == 2
            
            # Test with remainder
            mock_query.count.return_value = 61
            _, total_count, total_pages = job_service.get_job_listings_paginated(per_page=30)
            assert total_pages == 3
            
            # Test single item
            mock_query.count.return_value = 1
            _, total_count, total_pages = job_service.get_job_listings_paginated(per_page=30)
            assert total_pages == 1