"""
Tests for DataFreshnessChecker service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from job_matching_app.services.data_freshness_checker import DataFreshnessChecker
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.config import Settings


class TestDataFreshnessChecker:
    """Test cases for DataFreshnessChecker"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings"""
        settings = Mock(spec=Settings)
        settings.job_data_freshness_hours = 24
        settings.auto_scrape_enabled = True
        settings.min_jobs_before_scrape = 10
        return settings
    
    @pytest.fixture
    def freshness_checker(self, mock_db_session, mock_settings):
        """Create DataFreshnessChecker instance with mocked dependencies"""
        with patch('job_matching_app.services.data_freshness_checker.get_settings', return_value=mock_settings):
            return DataFreshnessChecker(db_session=mock_db_session)
    
    def test_init_with_session(self, mock_db_session, mock_settings):
        """Test initialization with provided database session"""
        with patch('job_matching_app.services.data_freshness_checker.get_settings', return_value=mock_settings):
            checker = DataFreshnessChecker(db_session=mock_db_session)
            assert checker.db_session == mock_db_session
            assert checker.settings == mock_settings
    
    def test_init_without_session(self, mock_settings):
        """Test initialization without provided database session"""
        with patch('job_matching_app.services.data_freshness_checker.get_settings', return_value=mock_settings):
            checker = DataFreshnessChecker()
            assert checker.db_session is None
            assert checker.settings == mock_settings
    
    def test_get_last_scrape_time_with_data(self, freshness_checker, mock_db_session):
        """Test getting last scrape time when data exists"""
        expected_time = datetime.utcnow() - timedelta(hours=12)
        mock_db_session.query.return_value.scalar.return_value = expected_time
        
        result = freshness_checker.get_last_scrape_time()
        
        assert result == expected_time
        mock_db_session.query.assert_called_once()
    
    def test_get_last_scrape_time_no_data(self, freshness_checker, mock_db_session):
        """Test getting last scrape time when no data exists"""
        mock_db_session.query.return_value.scalar.return_value = None
        
        result = freshness_checker.get_last_scrape_time()
        
        assert result is None
        mock_db_session.query.assert_called_once()
    
    def test_is_data_stale_no_data(self, freshness_checker, mock_db_session):
        """Test is_data_stale when no data exists"""
        mock_db_session.query.return_value.scalar.return_value = None
        
        result = freshness_checker.is_data_stale()
        
        assert result is True
    
    def test_is_data_stale_fresh_data(self, freshness_checker, mock_db_session):
        """Test is_data_stale with fresh data"""
        fresh_time = datetime.utcnow() - timedelta(hours=12)  # 12 hours ago
        mock_db_session.query.return_value.scalar.return_value = fresh_time
        
        result = freshness_checker.is_data_stale(threshold_hours=24)
        
        assert result is False
    
    def test_is_data_stale_old_data(self, freshness_checker, mock_db_session):
        """Test is_data_stale with stale data"""
        stale_time = datetime.utcnow() - timedelta(hours=36)  # 36 hours ago
        mock_db_session.query.return_value.scalar.return_value = stale_time
        
        result = freshness_checker.is_data_stale(threshold_hours=24)
        
        assert result is True
    
    def test_is_data_stale_default_threshold(self, freshness_checker, mock_db_session):
        """Test is_data_stale using default threshold from settings"""
        stale_time = datetime.utcnow() - timedelta(hours=36)  # 36 hours ago
        mock_db_session.query.return_value.scalar.return_value = stale_time
        
        result = freshness_checker.is_data_stale()  # Should use 24 hours from settings
        
        assert result is True
    
    def test_get_total_job_count(self, freshness_checker, mock_db_session):
        """Test getting total job count"""
        expected_count = 42
        mock_db_session.query.return_value.count.return_value = expected_count
        
        result = freshness_checker.get_total_job_count()
        
        assert result == expected_count
        mock_db_session.query.assert_called_once()
    
    def test_should_auto_scrape_stale_data(self, freshness_checker, mock_db_session):
        """Test should_auto_scrape when data is stale"""
        stale_time = datetime.utcnow() - timedelta(hours=36)
        mock_db_session.query.return_value.scalar.return_value = stale_time
        mock_db_session.query.return_value.count.return_value = 50  # Enough jobs
        
        result = freshness_checker.should_auto_scrape()
        
        assert result is True
    
    def test_should_auto_scrape_insufficient_jobs(self, freshness_checker, mock_db_session):
        """Test should_auto_scrape when job count is below threshold"""
        fresh_time = datetime.utcnow() - timedelta(hours=12)  # Fresh data
        mock_db_session.query.return_value.scalar.return_value = fresh_time
        mock_db_session.query.return_value.count.return_value = 5  # Below threshold
        
        result = freshness_checker.should_auto_scrape(job_count_threshold=10)
        
        assert result is True
    
    def test_should_auto_scrape_no_scraping_needed(self, freshness_checker, mock_db_session):
        """Test should_auto_scrape when no scraping is needed"""
        fresh_time = datetime.utcnow() - timedelta(hours=12)  # Fresh data
        mock_db_session.query.return_value.scalar.return_value = fresh_time
        mock_db_session.query.return_value.count.return_value = 50  # Enough jobs
        
        result = freshness_checker.should_auto_scrape()
        
        assert result is False
    
    def test_should_auto_scrape_no_data(self, freshness_checker, mock_db_session):
        """Test should_auto_scrape when no data exists"""
        mock_db_session.query.return_value.scalar.return_value = None
        mock_db_session.query.return_value.count.return_value = 0
        
        result = freshness_checker.should_auto_scrape()
        
        assert result is True
    
    def test_get_data_freshness_status_with_data(self, freshness_checker, mock_db_session):
        """Test get_data_freshness_status with existing data"""
        scrape_time = datetime.utcnow() - timedelta(hours=12)
        mock_db_session.query.return_value.scalar.return_value = scrape_time
        mock_db_session.query.return_value.count.return_value = 25
        
        result = freshness_checker.get_data_freshness_status()
        
        assert result['last_scrape_time'] == scrape_time
        assert result['total_jobs'] == 25
        assert result['is_stale'] is False
        assert result['should_auto_scrape'] is False
        assert result['threshold_hours'] == 24
        assert result['has_data'] is True
        assert result['data_age_hours'] == pytest.approx(12, abs=0.1)
    
    def test_get_data_freshness_status_no_data(self, freshness_checker, mock_db_session):
        """Test get_data_freshness_status with no existing data"""
        mock_db_session.query.return_value.scalar.return_value = None
        mock_db_session.query.return_value.count.return_value = 0
        
        result = freshness_checker.get_data_freshness_status()
        
        assert result['last_scrape_time'] is None
        assert result['total_jobs'] == 0
        assert result['is_stale'] is True
        assert result['should_auto_scrape'] is True
        assert result['threshold_hours'] == 24
        assert result['has_data'] is False
        assert result['data_age_hours'] is None
    
    def test_get_data_freshness_status_custom_threshold(self, freshness_checker, mock_db_session):
        """Test get_data_freshness_status with custom threshold"""
        scrape_time = datetime.utcnow() - timedelta(hours=18)
        mock_db_session.query.return_value.scalar.return_value = scrape_time
        mock_db_session.query.return_value.count.return_value = 25
        
        result = freshness_checker.get_data_freshness_status(threshold_hours=12)
        
        assert result['is_stale'] is True  # 18 hours > 12 hour threshold
        assert result['threshold_hours'] == 12
    
    @patch('job_matching_app.services.data_freshness_checker.get_db_context')
    def test_get_last_scrape_time_without_session(self, mock_get_db_context, mock_settings):
        """Test get_last_scrape_time when no session is provided"""
        mock_db = Mock()
        mock_get_db_context.return_value.__enter__.return_value = mock_db
        expected_time = datetime.utcnow() - timedelta(hours=12)
        mock_db.query.return_value.scalar.return_value = expected_time
        
        with patch('job_matching_app.services.data_freshness_checker.get_settings', return_value=mock_settings):
            checker = DataFreshnessChecker()  # No session provided
            result = checker.get_last_scrape_time()
        
        assert result == expected_time
        mock_get_db_context.assert_called_once()
    
    @patch('job_matching_app.services.data_freshness_checker.get_db_context')
    def test_get_total_job_count_without_session(self, mock_get_db_context, mock_settings):
        """Test get_total_job_count when no session is provided"""
        mock_db = Mock()
        mock_get_db_context.return_value.__enter__.return_value = mock_db
        expected_count = 42
        mock_db.query.return_value.count.return_value = expected_count
        
        with patch('job_matching_app.services.data_freshness_checker.get_settings', return_value=mock_settings):
            checker = DataFreshnessChecker()  # No session provided
            result = checker.get_total_job_count()
        
        assert result == expected_count
        mock_get_db_context.assert_called_once()


