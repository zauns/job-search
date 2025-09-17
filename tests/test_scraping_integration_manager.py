"""
Unit tests for ScrapingIntegrationManager
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from job_matching_app.services.scraping_integration_manager import ScrapingIntegrationManager
from job_matching_app.services.job_scraping_service import RateLimitError, SiteUnavailableError
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.models.scraping_session import ScrapingSession, ScrapingStatus


class TestScrapingIntegrationManager:
    """Test cases for ScrapingIntegrationManager"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings"""
        settings = Mock()
        settings.default_scraping_keywords = ['python', 'software engineer']
        settings.max_scraping_pages = 3
        settings.auto_scrape_enabled = True
        settings.job_data_freshness_hours = 24
        settings.min_jobs_before_scrape = 10
        return settings
    
    @pytest.fixture
    def sample_job_listings(self):
        """Sample job listings for testing"""
        return [
            JobListing(
                id=1,
                title="Python Developer",
                company="Tech Corp",
                location="Remote",
                remote_type=RemoteType.REMOTE,
                experience_level=ExperienceLevel.MID,
                technologies=["python", "django"],
                description="Great Python job",
                source_url="https://example.com/job1",
                source_site="indeed",
                scraped_at=datetime.utcnow()
            ),
            JobListing(
                id=2,
                title="Software Engineer",
                company="StartupCo",
                location="San Francisco",
                remote_type=RemoteType.HYBRID,
                experience_level=ExperienceLevel.SENIOR,
                technologies=["javascript", "react"],
                description="Exciting startup role",
                source_url="https://example.com/job2",
                source_site="linkedin",
                scraped_at=datetime.utcnow()
            )
        ]
    
    @pytest.fixture
    def scraping_manager(self, mock_db_session, mock_settings):
        """Create ScrapingIntegrationManager instance with mocked dependencies"""
        with patch('job_matching_app.services.scraping_integration_manager.get_settings', return_value=mock_settings):
            manager = ScrapingIntegrationManager(mock_db_session)
            
            # Mock the services
            manager.scraping_service = Mock()
            manager.freshness_checker = Mock()
            
            return manager
    
    def test_init(self, mock_db_session):
        """Test ScrapingIntegrationManager initialization"""
        with patch('job_matching_app.services.scraping_integration_manager.get_settings'):
            manager = ScrapingIntegrationManager(mock_db_session)
            
            assert manager.db_session == mock_db_session
            assert manager.scraping_service is not None
            assert manager.freshness_checker is not None
    
    def test_auto_scrape_if_needed_data_fresh(self, scraping_manager):
        """Test auto_scrape_if_needed when data is fresh"""
        # Setup mocks
        scraping_manager.freshness_checker.should_auto_scrape.return_value = False
        scraping_manager.freshness_checker.get_data_freshness_status.return_value = {
            'is_stale': False,
            'last_scrape_time': datetime.utcnow(),
            'total_jobs': 50
        }
        
        # Test
        result = scraping_manager.auto_scrape_if_needed(['python'], 'Remote')
        
        # Assertions
        assert result['scraping_triggered'] is False
        assert result['reason'] == 'Data is fresh'
        assert result['jobs_found'] == 0
        assert result['jobs_saved'] == 0
        assert 'freshness_status' in result
        
        scraping_manager.freshness_checker.should_auto_scrape.assert_called_once()
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_auto_scrape_if_needed_data_stale(self, mock_session_service_class, scraping_manager, sample_job_listings):
        """Test auto_scrape_if_needed when data is stale"""
        # Setup mocks
        scraping_manager.freshness_checker.should_auto_scrape.return_value = True
        
        # Mock scraping session
        mock_session = Mock()
        mock_session.id = 123
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        # Mock scraping results
        scraping_manager.scraping_service.scrape_indeed.return_value = [sample_job_listings[0]]
        scraping_manager.scraping_service.scrape_linkedin.return_value = [sample_job_listings[1]]
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 2
        
        # Test
        result = scraping_manager.auto_scrape_if_needed(['python'], 'Remote')
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['jobs_found'] == 2
        assert result['jobs_saved'] == 2
        assert result['session_id'] == 123
        assert result['success'] is True
        
        scraping_manager.scraping_service.scrape_indeed.assert_called_once()
        scraping_manager.scraping_service.scrape_linkedin.assert_called_once()
        mock_session_service.complete_session.assert_called_once_with(123, 2, 2)
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_auto_scrape_if_needed_force_scrape(self, mock_session_service_class, scraping_manager, sample_job_listings):
        """Test auto_scrape_if_needed with force_scrape=True"""
        # Setup mocks - even though data is fresh, should still scrape
        scraping_manager.freshness_checker.should_auto_scrape.return_value = False
        
        # Mock scraping session
        mock_session = Mock()
        mock_session.id = 456
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        # Mock scraping results
        scraping_manager.scraping_service.scrape_indeed.return_value = sample_job_listings
        scraping_manager.scraping_service.scrape_linkedin.return_value = []
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 2
        
        # Test
        result = scraping_manager.auto_scrape_if_needed(['python'], 'Remote', force_scrape=True)
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['jobs_found'] == 2
        assert result['jobs_saved'] == 2
        
        # Should not check freshness when force_scrape=True
        scraping_manager.freshness_checker.should_auto_scrape.assert_not_called()
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_scrape_with_progress_success(self, mock_session_service_class, scraping_manager, sample_job_listings):
        """Test scrape_with_progress with successful scraping"""
        # Setup mocks
        mock_session = Mock()
        mock_session.id = 789
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        scraping_manager.scraping_service.scrape_indeed.return_value = [sample_job_listings[0]]
        scraping_manager.scraping_service.scrape_linkedin.return_value = [sample_job_listings[1]]
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 2
        
        # Mock progress callback
        progress_callback = Mock()
        
        # Test
        result = scraping_manager.scrape_with_progress(
            keywords=['python', 'django'],
            location='San Francisco',
            max_pages=5,
            progress_callback=progress_callback
        )
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['session_id'] == 789
        assert result['jobs_found'] == 2
        assert result['jobs_saved'] == 2
        assert result['success'] is True
        assert len(result['errors']) == 0
        
        # Check progress callbacks were called
        assert progress_callback.call_count >= 5  # started, 2 sites, saving, completed
        
        # Verify specific callback calls
        progress_callback.assert_any_call("started", {
            'session_id': 789,
            'keywords': ['python', 'django'],
            'location': 'San Francisco',
            'max_pages': 5
        })
        
        progress_callback.assert_any_call("completed", {
            'session_id': 789,
            'total_jobs_found': 2,
            'jobs_saved': 2,
            'errors': []
        })
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_scrape_with_progress_rate_limit_error(self, mock_session_service_class, scraping_manager, sample_job_listings):
        """Test scrape_with_progress with rate limit error"""
        # Setup mocks
        mock_session = Mock()
        mock_session.id = 101
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        # Indeed fails with rate limit, LinkedIn succeeds
        scraping_manager.scraping_service.scrape_indeed.side_effect = RateLimitError("Rate limit exceeded")
        scraping_manager.scraping_service.scrape_linkedin.return_value = sample_job_listings
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 2
        
        progress_callback = Mock()
        
        # Test
        result = scraping_manager.scrape_with_progress(
            keywords=['python'],
            progress_callback=progress_callback
        )
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['jobs_found'] == 2
        assert result['jobs_saved'] == 2
        assert len(result['errors']) == 1
        assert 'Rate limit exceeded for Indeed' in result['errors'][0]
        
        # Check error was added to session
        mock_session_service.add_session_error.assert_called_once()
        
        # Check progress callback for rate limit
        progress_callback.assert_any_call("scraping_site", {
            'site': 'Indeed',
            'status': 'rate_limited',
            'error': 'Rate limit exceeded for Indeed: Rate limit exceeded'
        })
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_scrape_with_progress_site_unavailable_error(self, mock_session_service_class, scraping_manager):
        """Test scrape_with_progress with site unavailable error"""
        # Setup mocks
        mock_session = Mock()
        mock_session.id = 102
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        # Both sites fail
        scraping_manager.scraping_service.scrape_indeed.side_effect = SiteUnavailableError("Site down")
        scraping_manager.scraping_service.scrape_linkedin.side_effect = SiteUnavailableError("Site down")
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 0
        
        progress_callback = Mock()
        
        # Test
        result = scraping_manager.scrape_with_progress(
            keywords=['python'],
            progress_callback=progress_callback
        )
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['jobs_found'] == 0
        assert result['jobs_saved'] == 0
        assert len(result['errors']) == 2
        assert all('unavailable' in error for error in result['errors'])
        
        # Check session was completed (not failed) since this is expected behavior
        mock_session_service.complete_session.assert_called_once_with(102, 0, 0)
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_scrape_with_progress_critical_error(self, mock_session_service_class, scraping_manager):
        """Test scrape_with_progress with critical error during session creation"""
        # Setup mocks to raise exception during session creation
        mock_session_service_class.side_effect = Exception("Database error")
        
        progress_callback = Mock()
        
        # Test
        result = scraping_manager.scrape_with_progress(
            keywords=['python'],
            progress_callback=progress_callback
        )
        
        # Assertions
        assert result['scraping_triggered'] is True
        assert result['success'] is False
        assert len(result['errors']) == 1
        assert 'Critical error during scraping' in result['errors'][0]
        
        # Check failure callback
        progress_callback.assert_any_call("failed", {
            'session_id': None,
            'error': 'Critical error during scraping: Database error'
        })
    
    def test_handle_scraping_errors_no_errors(self, scraping_manager):
        """Test handle_scraping_errors with no errors"""
        result = scraping_manager.handle_scraping_errors([])
        
        assert result['has_errors'] is False
        assert result['recommendations'] == []
    
    def test_handle_scraping_errors_with_errors(self, scraping_manager):
        """Test handle_scraping_errors with various error types"""
        errors = [
            "Rate limit exceeded for Indeed",
            "LinkedIn unavailable: Connection timeout",
            "Network connection failed",
            "Unexpected parsing error"
        ]
        
        result = scraping_manager.handle_scraping_errors(errors)
        
        # Assertions
        assert result['has_errors'] is True
        assert result['total_errors'] == 4
        assert result['error_types']['rate_limit'] == 1
        assert result['error_types']['site_unavailable'] == 1
        assert result['error_types']['network'] == 1
        assert result['error_types']['other'] == 1
        
        # Check recommendations
        recommendations = result['recommendations']
        assert any('rate limiting' in rec.lower() for rec in recommendations)
        assert any('unavailable' in rec.lower() for rec in recommendations)
        assert any('network' in rec.lower() for rec in recommendations)
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_get_scraping_status(self, mock_session_service_class, scraping_manager):
        """Test get_scraping_status"""
        # Setup mocks
        freshness_status = {
            'is_stale': False,
            'last_scrape_time': datetime.utcnow(),
            'total_jobs': 25
        }
        scraping_manager.freshness_checker.get_data_freshness_status.return_value = freshness_status
        
        session_stats = {
            'total_sessions': 10,
            'completed_sessions': 8,
            'failed_sessions': 1,
            'running_sessions': 1
        }
        
        active_sessions = [Mock(id=1), Mock(id=2)]
        
        mock_session_service = Mock()
        mock_session_service.get_session_statistics.return_value = session_stats
        mock_session_service.get_active_sessions.return_value = active_sessions
        mock_session_service_class.return_value = mock_session_service
        
        # Test
        result = scraping_manager.get_scraping_status()
        
        # Assertions
        assert result['data_freshness'] == freshness_status
        assert result['session_statistics'] == session_stats
        assert result['active_sessions'] == 2
        assert result['active_session_ids'] == [1, 2]
        assert result['scraping_available'] is True
        assert result['auto_scrape_enabled'] is True
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_cancel_active_sessions(self, mock_session_service_class, scraping_manager):
        """Test cancel_active_sessions"""
        # Setup mocks
        active_sessions = [Mock(id=1), Mock(id=2), Mock(id=3)]
        
        mock_session_service = Mock()
        mock_session_service.get_active_sessions.return_value = active_sessions
        mock_session_service.cancel_session.return_value = Mock()
        mock_session_service_class.return_value = mock_session_service
        
        # Test
        cancelled_count = scraping_manager.cancel_active_sessions()
        
        # Assertions
        assert cancelled_count == 3
        
        # Check all sessions were cancelled
        expected_calls = [((1,),), ((2,),), ((3,),)]
        actual_calls = mock_session_service.cancel_session.call_args_list
        assert len(actual_calls) == 3
        for call in actual_calls:
            assert call in expected_calls
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_cancel_active_sessions_with_error(self, mock_session_service_class, scraping_manager):
        """Test cancel_active_sessions with some cancellation errors"""
        # Setup mocks
        active_sessions = [Mock(id=1), Mock(id=2)]
        
        mock_session_service = Mock()
        mock_session_service.get_active_sessions.return_value = active_sessions
        # First cancellation succeeds, second fails
        mock_session_service.cancel_session.side_effect = [Mock(), Exception("Cancel failed")]
        mock_session_service_class.return_value = mock_session_service
        
        # Test
        cancelled_count = scraping_manager.cancel_active_sessions()
        
        # Assertions
        assert cancelled_count == 1  # Only one succeeded
    
    @patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService')
    def test_auto_scrape_with_default_keywords(self, mock_session_service_class, scraping_manager, sample_job_listings):
        """Test auto_scrape_if_needed with default keywords from settings"""
        # Setup mocks
        scraping_manager.freshness_checker.should_auto_scrape.return_value = True
        
        mock_session = Mock()
        mock_session.id = 999
        mock_session_service = Mock()
        mock_session_service.create_session.return_value = mock_session
        mock_session_service_class.return_value = mock_session_service
        
        scraping_manager.scraping_service.scrape_indeed.return_value = sample_job_listings
        scraping_manager.scraping_service.scrape_linkedin.return_value = []
        scraping_manager.scraping_service.save_jobs_to_database.return_value = 2
        
        # Test with keywords=None (should use defaults)
        result = scraping_manager.auto_scrape_if_needed(keywords=None)
        
        # Assertions
        assert result['scraping_triggered'] is True
        
        # Check that create_session was called with default keywords
        mock_session_service.create_session.assert_called_once_with(
            ['python', 'software engineer'], ""
        )
    
    @patch('job_matching_app.services.scraping_integration_manager.get_db_context')
    def test_scrape_with_progress_no_db_session(self, mock_get_db_context, mock_settings, sample_job_listings):
        """Test scrape_with_progress when no db_session is provided"""
        # Setup mocks
        mock_db = Mock()
        mock_get_db_context.return_value.__enter__.return_value = mock_db
        
        with patch('job_matching_app.services.scraping_integration_manager.get_settings', return_value=mock_settings):
            manager = ScrapingIntegrationManager(db_session=None)
            manager.scraping_service = Mock()
            
            # Mock session service creation within context
            mock_session_service = Mock()
            mock_session = Mock()
            mock_session.id = 555
            mock_session_service.create_session.return_value = mock_session
            
            with patch('job_matching_app.services.scraping_integration_manager.ScrapingSessionService', return_value=mock_session_service):
                manager.scraping_service.scrape_indeed.return_value = sample_job_listings
                manager.scraping_service.scrape_linkedin.return_value = []
                manager.scraping_service.save_jobs_to_database.return_value = 2
                
                # Test
                result = manager.scrape_with_progress(['python'])
                
                # Assertions
                assert result['scraping_triggered'] is True
                assert result['session_id'] == 555
                
                # Verify database context was used
                mock_get_db_context.assert_called()