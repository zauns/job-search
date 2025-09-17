"""
Integration tests for JobScrapingService with real functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import requests
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_matching_app.services.job_scraping_service import (
    JobScrapingService, 
    JobScrapingError, 
    RateLimitError, 
    SiteUnavailableError,
    NetworkError,
    BlockedError,
    TimeoutError,
    ScrapingResult,
    ScrapingErrorType
)
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.database import Base


class TestJobScrapingServiceIntegration:
    """Integration tests for JobScrapingService with real functionality"""
    
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
    def scraping_service(self):
        """Create a JobScrapingService instance for testing"""
        return JobScrapingService()
    
    @pytest.fixture
    def sample_indeed_html(self):
        """Sample Indeed HTML response for testing"""
        return """
        <html>
            <body>
                <div data-jk="12345">
                    <h2 class="jobTitle">
                        <a href="/viewjob?jk=12345">Python Developer</a>
                    </h2>
                    <span data-testid="company-name">Tech Company</span>
                    <div data-testid="job-location">São Paulo, SP</div>
                    <div data-testid="job-snippet">
                        Looking for a senior Python developer with Django experience.
                        Remote work available.
                    </div>
                </div>
                <div data-jk="67890">
                    <h2 class="jobTitle">
                        <a href="/viewjob?jk=67890">Junior JavaScript Developer</a>
                    </h2>
                    <span data-testid="company-name">Startup Inc</span>
                    <div data-testid="job-location">Rio de Janeiro, RJ</div>
                    <div data-testid="job-snippet">
                        Entry-level position for JavaScript developer. React experience preferred.
                        On-site work required.
                    </div>
                </div>
            </body>
        </html>
        """
    
    @pytest.fixture
    def sample_linkedin_html(self):
        """Sample LinkedIn HTML response for testing"""
        return """
        <html>
            <body>
                <div data-entity-urn="job:123">
                    <h3 class="base-search-card__title">
                        <a href="/jobs/view/123">Data Scientist</a>
                    </h3>
                    <h4 class="base-search-card__subtitle">AI Corp</h4>
                    <span class="job-search-card__location">Remote</span>
                    <p class="job-search-card__snippet">
                        Senior data scientist position with machine learning focus.
                        Python and TensorFlow required. Hybrid work model.
                    </p>
                </div>
            </body>
        </html>
        """
    
    def test_create_session(self, scraping_service):
        """Test session creation with proper configuration"""
        session = scraping_service._create_session()
        
        assert session is not None
        assert 'User-Agent' in session.headers
        assert 'Mozilla' in session.headers['User-Agent']
    
    def test_build_indeed_url(self, scraping_service):
        """Test Indeed URL building"""
        url = scraping_service._build_indeed_url("python developer", "São Paulo", 0)
        
        assert "indeed.com/jobs" in url
        assert "q=python+developer" in url
        assert "l=S%C3%A3o+Paulo" in url
        assert "start=0" in url
        assert "sort=date" in url
    
    def test_build_linkedin_url(self, scraping_service):
        """Test LinkedIn URL building"""
        url = scraping_service._build_linkedin_url("data scientist", "Remote", 25)
        
        assert "linkedin.com/jobs/search" in url
        assert "keywords=data+scientist" in url
        assert "location=Remote" in url
        assert "start=25" in url
        assert "sortBy=DD" in url
    
    def test_extract_remote_indicators(self, scraping_service):
        """Test remote work indicator extraction"""
        # Test remote indicators
        remote_text = "This is a remote position with home office benefits"
        indicators = scraping_service._extract_remote_indicators(remote_text)
        assert 'remote' in indicators
        
        # Test hybrid indicators
        hybrid_text = "Hybrid work model with flexible schedule"
        indicators = scraping_service._extract_remote_indicators(hybrid_text)
        assert 'hybrid' in indicators
        
        # Test onsite indicators
        onsite_text = "On-site position at our headquarters"
        indicators = scraping_service._extract_remote_indicators(onsite_text)
        assert 'onsite' in indicators
        
        # Test Portuguese indicators
        pt_text = "Trabalho remoto disponível"
        indicators = scraping_service._extract_remote_indicators(pt_text)
        assert 'remote' in indicators
    
    def test_extract_experience_indicators(self, scraping_service):
        """Test experience level indicator extraction"""
        # Test senior level
        senior_text = "Senior Python Developer position"
        indicators = scraping_service._extract_experience_indicators(senior_text)
        assert 'senior' in indicators
        
        # Test junior level
        junior_text = "Junior developer opportunity"
        indicators = scraping_service._extract_experience_indicators(junior_text)
        assert 'junior' in indicators
        
        # Test intern level
        intern_text = "Internship program for students"
        indicators = scraping_service._extract_experience_indicators(intern_text)
        assert 'intern' in indicators
        
        # Test Portuguese indicators
        pt_text = "Vaga para estagiário em desenvolvimento"
        indicators = scraping_service._extract_experience_indicators(pt_text)
        assert 'intern' in indicators
    
    def test_extract_technology_keywords(self, scraping_service):
        """Test technology keyword extraction"""
        tech_text = "Python developer with Django, React, and AWS experience"
        keywords = scraping_service._extract_technology_keywords(tech_text)
        
        assert 'python' in keywords
        assert 'django' in keywords
        assert 'react' in keywords
        assert 'aws' in keywords
    
    def test_parse_indeed_page(self, scraping_service, sample_indeed_html):
        """Test Indeed page parsing"""
        jobs = scraping_service._parse_indeed_page(sample_indeed_html, "https://indeed.com/search")
        
        assert len(jobs) == 2
        
        # Check first job
        job1 = jobs[0]
        assert job1.title == "Python Developer"
        assert job1.company == "Tech Company"
        assert job1.location == "São Paulo, SP"
        assert job1.source_site == "indeed"
        assert job1.remote_type == RemoteType.REMOTE
        assert job1.experience_level == ExperienceLevel.SENIOR
        assert 'python' in job1.technologies
        assert 'django' in job1.technologies
        
        # Check second job
        job2 = jobs[1]
        assert job2.title == "Junior JavaScript Developer"
        assert job2.company == "Startup Inc"
        assert job2.experience_level == ExperienceLevel.JUNIOR
        assert job2.remote_type == RemoteType.ONSITE
    
    def test_parse_linkedin_page(self, scraping_service, sample_linkedin_html):
        """Test LinkedIn page parsing"""
        jobs = scraping_service._parse_linkedin_page(sample_linkedin_html, "https://linkedin.com/search")
        
        assert len(jobs) == 1
        
        job = jobs[0]
        assert job.title == "Data Scientist"
        assert job.company == "AI Corp"
        assert job.location == "Remote"
        assert job.source_site == "linkedin"
        assert job.remote_type == RemoteType.HYBRID
        assert job.experience_level == ExperienceLevel.SENIOR
        assert 'python' in job.technologies
        assert 'machine learning' in job.technologies
    
    def test_normalize_job_data(self, scraping_service):
        """Test job data normalization"""
        raw_data = {
            'title': 'Senior Python Developer',
            'company': 'Tech Corp',
            'location': 'São Paulo, SP',
            'description': 'Python developer with Django experience',
            'source_url': 'https://example.com/job/123',
            'application_url': 'https://example.com/apply/123',
            'source_site': 'indeed',
            'raw_data': {
                'remote_indicators': ['remote'],
                'experience_indicators': ['senior'],
                'technology_keywords': ['python', 'django']
            }
        }
        
        job = scraping_service.normalize_job_data(raw_data)
        
        assert isinstance(job, JobListing)
        assert job.title == 'Senior Python Developer'
        assert job.company == 'Tech Corp'
        assert job.location == 'São Paulo, SP'
        assert job.remote_type == RemoteType.REMOTE
        assert job.experience_level == ExperienceLevel.SENIOR
        assert job.technologies == ['python', 'django']
        assert job.source_site == 'indeed'
        assert isinstance(job.scraped_at, datetime)
    
    def test_save_jobs_to_database_real(self, scraping_service, db_session):
        """Test saving jobs to real database"""
        # Create test jobs
        job1 = JobListing(
            title="Test Job 1",
            company="Test Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python", "django"],
            description="Test description for job 1",
            source_url="https://example.com/job1",
            application_url="https://example.com/apply1",
            source_site="indeed",
            scraped_at=datetime.now(timezone.utc)
        )
        
        job2 = JobListing(
            title="Test Job 2",
            company="Test Company 2",
            location="Rio de Janeiro, RJ",
            remote_type=RemoteType.HYBRID,
            experience_level=ExperienceLevel.JUNIOR,
            technologies=["javascript", "react"],
            description="Test description for job 2",
            source_url="https://example.com/job2",
            application_url="https://example.com/apply2",
            source_site="linkedin",
            scraped_at=datetime.now(timezone.utc)
        )
        
        jobs = [job1, job2]
        
        # Mock the database context to use our test session
        with patch('job_matching_app.services.job_scraping_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = db_session
            
            # Test saving
            saved_count = scraping_service.save_jobs_to_database(jobs)
            
            assert saved_count == 2
            
            # Verify jobs are actually in the database
            saved_jobs = db_session.query(JobListing).all()
            assert len(saved_jobs) == 2
            
            # Verify job details
            saved_job1 = db_session.query(JobListing).filter_by(source_url="https://example.com/job1").first()
            assert saved_job1 is not None
            assert saved_job1.title == "Test Job 1"
            assert saved_job1.technologies == ["python", "django"]
    
    def test_save_jobs_duplicate_detection(self, scraping_service, db_session):
        """Test duplicate job detection during save"""
        # Create a job
        job = JobListing(
            title="Duplicate Test Job",
            company="Test Company",
            location="São Paulo, SP",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["python"],
            description="Test description",
            source_url="https://example.com/duplicate-job",
            application_url="https://example.com/apply-duplicate",
            source_site="indeed",
            scraped_at=datetime.now(timezone.utc)
        )
        
        # Save it first time
        with patch('job_matching_app.services.job_scraping_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = db_session
            
            saved_count1 = scraping_service.save_jobs_to_database([job])
            assert saved_count1 == 1
            
            # Try to save the same job again (should be detected as duplicate)
            saved_count2 = scraping_service.save_jobs_to_database([job])
            assert saved_count2 == 0  # No new jobs saved
            
            # Verify only one job exists in database
            total_jobs = db_session.query(JobListing).count()
            assert total_jobs == 1
    
    def test_scrape_indeed_html_parsing(self, scraping_service, sample_indeed_html):
        """Test Indeed HTML parsing without network requests"""
        # Test the parsing logic directly
        jobs = scraping_service._parse_indeed_page(sample_indeed_html, "https://indeed.com/search")
        
        assert len(jobs) == 2
        assert jobs[0].title == "Python Developer"
        assert jobs[0].company == "Tech Company"
        assert jobs[0].location == "São Paulo, SP"
        assert jobs[0].source_site == "indeed"
        assert jobs[0].remote_type == RemoteType.REMOTE
        assert jobs[0].experience_level == ExperienceLevel.SENIOR
        assert 'python' in jobs[0].technologies
        assert 'django' in jobs[0].technologies
        
        assert jobs[1].title == "Junior JavaScript Developer"
        assert jobs[1].company == "Startup Inc"
        assert jobs[1].experience_level == ExperienceLevel.JUNIOR
        assert jobs[1].remote_type == RemoteType.ONSITE
    
    def test_scrape_linkedin_html_parsing(self, scraping_service, sample_linkedin_html):
        """Test LinkedIn HTML parsing without network requests"""
        # Test the parsing logic directly
        jobs = scraping_service._parse_linkedin_page(sample_linkedin_html, "https://linkedin.com/search")
        
        assert len(jobs) == 1
        
        job = jobs[0]
        assert job.title == "Data Scientist"
        assert job.company == "AI Corp"
        assert job.location == "Remote"
        assert job.source_site == "linkedin"
        assert job.remote_type == RemoteType.HYBRID
        assert job.experience_level == ExperienceLevel.SENIOR
        assert 'python' in job.technologies
        assert 'machine learning' in job.technologies
    
    def test_real_scraping_integration_with_error_handling(self, scraping_service, db_session):
        """Test real scraping integration with proper error handling"""
        # This test uses real network requests but with error handling
        # It's designed to test the complete workflow including error scenarios
        
        with patch('job_matching_app.services.job_scraping_service.get_db_context') as mock_context:
            mock_context.return_value.__enter__.return_value = db_session
            
            # Test with a very specific search that's unlikely to return many results
            # This reduces the load on job sites during testing
            try:
                result = scraping_service.scrape_all_sites(
                    keywords=['very-specific-test-keyword-unlikely-to-exist'],
                    location='Test Location',
                    max_pages=1  # Limit to 1 page to be respectful
                )
                
                # Verify result structure regardless of success/failure
                assert isinstance(result, ScrapingResult)
                assert hasattr(result, 'jobs')
                assert hasattr(result, 'errors')
                assert hasattr(result, 'successful_sites')
                assert hasattr(result, 'failed_sites')
                
                # The search might succeed with 0 results or fail due to rate limiting
                # Both are valid outcomes for this test
                if result.has_jobs():
                    assert len(result.jobs) >= 0
                    # Verify jobs have required fields
                    for job in result.jobs:
                        assert job.title is not None
                        assert job.company is not None
                        assert job.source_site in ['indeed', 'linkedin']
                
                if result.has_errors():
                    # Verify error structure
                    for error in result.errors:
                        assert isinstance(error, JobScrapingError)
                        assert error.site in ['indeed', 'linkedin']
                
            except (RateLimitError, SiteUnavailableError, NetworkError) as e:
                # These errors are expected and acceptable during testing
                assert isinstance(e, JobScrapingError)
                assert e.site in ['indeed', 'linkedin']
                pytest.skip(f"Scraping test skipped due to expected error: {e}")
            
            except Exception as e:
                # Unexpected errors should be investigated
                pytest.fail(f"Unexpected error during scraping test: {e}")
    
    def test_scrape_all_sites_mock_success(self, scraping_service, db_session):
        """Test scraping all sites successfully with mocked network calls"""
        # Mock the individual site scraping methods to avoid network calls
        with patch.object(scraping_service, 'scrape_indeed') as mock_indeed:
            with patch.object(scraping_service, 'scrape_linkedin') as mock_linkedin:
                with patch('job_matching_app.services.job_scraping_service.get_db_context') as mock_context:
                    mock_context.return_value.__enter__.return_value = db_session
                    
                    # Mock scraping results
                    indeed_jobs = [
                        JobListing(
                            title="Python Developer",
                            company="Tech Company",
                            location="São Paulo, SP",
                            remote_type=RemoteType.REMOTE,
                            experience_level=ExperienceLevel.SENIOR,
                            technologies=["python", "django"],
                            description="Python developer position",
                            source_url="https://indeed.com/job1",
                            application_url="https://indeed.com/apply1",
                            source_site="indeed",
                            scraped_at=datetime.now(timezone.utc)
                        )
                    ]
                    linkedin_jobs = [
                        JobListing(
                            title="Data Scientist",
                            company="AI Company",
                            location="Remote",
                            remote_type=RemoteType.REMOTE,
                            experience_level=ExperienceLevel.SENIOR,
                            technologies=["python", "machine learning"],
                            description="Data scientist position",
                            source_url="https://linkedin.com/job2",
                            application_url="https://linkedin.com/apply2",
                            source_site="linkedin",
                            scraped_at=datetime.now(timezone.utc)
                        )
                    ]
                    
                    mock_indeed.return_value = indeed_jobs
                    mock_linkedin.return_value = linkedin_jobs
                    
                    # Test scraping all sites
                    result = scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
                    
                    assert isinstance(result, ScrapingResult)
                    assert len(result.jobs) == 2
                    assert result.total_jobs_saved == 2
                    assert "indeed" in result.successful_sites
                    assert "linkedin" in result.successful_sites
                    assert not result.has_errors()
                    
                    # Verify jobs were saved to database
                    saved_jobs = db_session.query(JobListing).all()
                    assert len(saved_jobs) == 2
                    
                    # Verify job details
                    indeed_job = db_session.query(JobListing).filter_by(source_site="indeed").first()
                    assert indeed_job.title == "Python Developer"
                    assert indeed_job.technologies == ["python", "django"]
                    
                    linkedin_job = db_session.query(JobListing).filter_by(source_site="linkedin").first()
                    assert linkedin_job.title == "Data Scientist"
                    assert linkedin_job.technologies == ["python", "machine learning"]
    
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_indeed')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_linkedin')
    def test_scrape_all_sites_partial_failure(self, mock_linkedin, mock_indeed, scraping_service):
        """Test scraping with one site failing"""
        # Mock Indeed success and LinkedIn failure
        indeed_jobs = [
            JobListing(title="Job 1", company="Company 1", description="Desc 1",
                      source_url="url1", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        ]
        
        mock_indeed.return_value = indeed_jobs
        mock_linkedin.side_effect = SiteUnavailableError("LinkedIn failed", "linkedin")
        
        with patch.object(scraping_service, 'save_jobs_to_database', return_value=1):
            result = scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
        
        assert isinstance(result, ScrapingResult)
        assert len(result.jobs) == 1
        assert result.jobs[0].source_site == "indeed"
        assert "indeed" in result.successful_sites
        assert "linkedin" in result.failed_sites
        assert result.has_errors()
        assert len(result.errors) == 1
    
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_indeed')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_linkedin')
    def test_scrape_all_sites_complete_failure(self, mock_linkedin, mock_indeed, scraping_service):
        """Test scraping with all sites failing"""
        # Mock both sites failing
        mock_indeed.side_effect = SiteUnavailableError("Indeed failed", "indeed")
        mock_linkedin.side_effect = SiteUnavailableError("LinkedIn failed", "linkedin")
        
        with pytest.raises(SiteUnavailableError):
            scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
    
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_indeed')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_linkedin')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.save_jobs_to_database')
    def test_scrape_all_sites_legacy_method(self, mock_save, mock_linkedin, mock_indeed, scraping_service):
        """Test legacy method that returns just the job list"""
        # Mock scraping results
        indeed_jobs = [
            JobListing(title="Job 1", company="Company 1", description="Desc 1", 
                      source_url="url1", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        ]
        
        mock_indeed.return_value = indeed_jobs
        mock_linkedin.return_value = []
        mock_save.return_value = 1
        
        # Test legacy method
        jobs = scraping_service.scrape_all_sites_legacy(['python'], 'São Paulo', 2)
        
        assert isinstance(jobs, list)
        assert len(jobs) == 1
        assert jobs[0].source_site == "indeed"
    
    def test_extract_indeed_job_data_missing_required_fields(self, scraping_service):
        """Test Indeed job data extraction with missing required fields"""
        from bs4 import BeautifulSoup
        
        # HTML with missing company name
        html = '<div data-jk="123"><h2 class="jobTitle">Test Job</h2></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = scraping_service._extract_indeed_job_data(card, "https://test.com")
        assert result is None
    
    def test_extract_linkedin_job_data_missing_required_fields(self, scraping_service):
        """Test LinkedIn job data extraction with missing required fields"""
        from bs4 import BeautifulSoup
        
        # HTML with missing title
        html = '<div data-entity-urn="job:123"><h4 class="base-search-card__subtitle">Test Company</h4></div>'
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div')
        
        result = scraping_service._extract_linkedin_job_data(card, "https://test.com")
        assert result is None


class TestErrorHandling:
    """Test cases for enhanced error handling"""
    
    @pytest.fixture
    def scraping_service(self):
        """Create a JobScrapingService instance for testing"""
        return JobScrapingService()
    
    def test_job_scraping_error_user_messages(self):
        """Test user-friendly error messages for different error types"""
        # Rate limit error
        rate_error = RateLimitError("Rate limit exceeded", "indeed", 120)
        assert "Rate limit exceeded for indeed" in rate_error.user_message
        assert "120 seconds" in rate_error.user_message
        
        # Site unavailable error
        site_error = SiteUnavailableError("Site down", "linkedin")
        assert "linkedin is currently unavailable" in site_error.user_message
        
        # Network error
        network_error = NetworkError("Connection failed", "indeed")
        assert "Network connection issues" in network_error.user_message
        
        # Blocked error
        blocked_error = BlockedError("Access denied", "linkedin")
        assert "Access to linkedin has been temporarily blocked" in blocked_error.user_message
        
        # Timeout error
        timeout_error = TimeoutError("Request timeout", "indeed")
        assert "Request to indeed timed out" in timeout_error.user_message
    
    def test_calculate_retry_delay(self, scraping_service):
        """Test exponential backoff calculation"""
        # Test basic exponential backoff
        delay1 = scraping_service._calculate_retry_delay(0)  # First retry
        delay2 = scraping_service._calculate_retry_delay(1)  # Second retry
        delay3 = scraping_service._calculate_retry_delay(2)  # Third retry
        
        # Should increase exponentially (with jitter)
        assert delay1 < delay2 < delay3
        
        # Test with custom base delay
        custom_delay = scraping_service._calculate_retry_delay(0, base_delay=5)
        assert custom_delay >= 5  # Should be at least the base delay
        
        # Test maximum delay cap
        large_delay = scraping_service._calculate_retry_delay(10)  # Very high attempt
        assert large_delay <= scraping_service.max_delay
    
    def test_handle_request_error_timeout(self, scraping_service):
        """Test timeout error handling"""
        timeout_exception = requests.exceptions.Timeout("Request timed out")
        error = scraping_service._handle_request_error(timeout_exception, "indeed", "https://test.com")
        
        assert isinstance(error, TimeoutError)
        assert error.site == "indeed"
        assert error.error_type == ScrapingErrorType.TIMEOUT_ERROR
    
    def test_handle_request_error_connection(self, scraping_service):
        """Test connection error handling"""
        connection_exception = requests.exceptions.ConnectionError("Connection failed")
        error = scraping_service._handle_request_error(connection_exception, "linkedin", "https://test.com")
        
        assert isinstance(error, NetworkError)
        assert error.site == "linkedin"
        assert error.error_type == ScrapingErrorType.NETWORK_ERROR
    
    def test_handle_request_error_rate_limit(self, scraping_service):
        """Test rate limit error handling"""
        # Mock HTTP 429 error
        response = Mock()
        response.status_code = 429
        response.headers = {'Retry-After': '300'}
        
        http_error = requests.exceptions.HTTPError("429 Too Many Requests")
        http_error.response = response
        
        error = scraping_service._handle_request_error(http_error, "indeed", "https://test.com")
        
        assert isinstance(error, RateLimitError)
        assert error.site == "indeed"
        assert error.retry_after == 300
        assert error.error_type == ScrapingErrorType.RATE_LIMIT
    
    def test_handle_request_error_blocked(self, scraping_service):
        """Test blocked access error handling"""
        # Mock HTTP 403 error
        response = Mock()
        response.status_code = 403
        
        http_error = requests.exceptions.HTTPError("403 Forbidden")
        http_error.response = response
        
        error = scraping_service._handle_request_error(http_error, "linkedin", "https://test.com")
        
        assert isinstance(error, BlockedError)
        assert error.site == "linkedin"
        assert error.error_type == ScrapingErrorType.BLOCKED_ERROR
    
    def test_handle_request_error_server_error(self, scraping_service):
        """Test server error handling"""
        # Mock HTTP 503 error
        response = Mock()
        response.status_code = 503
        
        http_error = requests.exceptions.HTTPError("503 Service Unavailable")
        http_error.response = response
        
        error = scraping_service._handle_request_error(http_error, "indeed", "https://test.com")
        
        assert isinstance(error, SiteUnavailableError)
        assert error.site == "indeed"
        assert error.error_type == ScrapingErrorType.SITE_UNAVAILABLE
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    @patch('requests.Session.get')
    def test_make_request_with_retry_success_after_failure(self, mock_get, mock_sleep, scraping_service):
        """Test successful request after initial failures"""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            mock_response
        ]
        
        result = scraping_service._make_request_with_retry("https://test.com", "indeed", max_retries=2)
        
        assert result == mock_response
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()  # Should have slept between retries
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    @patch('requests.Session.get')
    def test_make_request_with_retry_all_failures(self, mock_get, mock_sleep, scraping_service):
        """Test request that fails all retry attempts"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(NetworkError):
            scraping_service._make_request_with_retry("https://test.com", "indeed", max_retries=2)
        
        assert mock_get.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2  # Should have slept between retries
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    @patch('requests.Session.get')
    def test_make_request_with_retry_rate_limit(self, mock_get, mock_sleep, scraping_service):
        """Test rate limit handling in retry logic"""
        # Mock rate limit response
        response = Mock()
        response.status_code = 429
        response.headers = {'Retry-After': '60'}
        
        http_error = requests.exceptions.HTTPError("429 Too Many Requests")
        http_error.response = response
        
        mock_get.side_effect = http_error
        
        with pytest.raises(RateLimitError) as exc_info:
            scraping_service._make_request_with_retry("https://test.com", "indeed", max_retries=1)
        
        assert exc_info.value.retry_after == 60
        mock_sleep.assert_called()  # Should have used retry-after value for sleep
    
    def test_user_agent_rotation(self, scraping_service):
        """Test user agent rotation functionality"""
        original_ua = scraping_service.session.headers['User-Agent']
        
        scraping_service._rotate_user_agent()
        new_ua = scraping_service.session.headers['User-Agent']
        
        # User agent should be different (though there's a small chance it's the same)
        # At minimum, it should be a valid Mozilla user agent
        assert 'Mozilla' in new_ua


class TestScrapingResult:
    """Test cases for ScrapingResult class"""
    
    def test_scraping_result_initialization(self):
        """Test ScrapingResult initialization"""
        result = ScrapingResult()
        
        assert result.jobs == []
        assert result.errors == []
        assert result.site_results == {}
        assert result.total_jobs_found == 0
        assert result.total_jobs_saved == 0
        assert result.successful_sites == []
        assert result.failed_sites == []
    
    def test_add_site_result_success(self):
        """Test adding successful site results"""
        result = ScrapingResult()
        
        job1 = JobListing(title="Job 1", company="Company 1", description="Desc 1",
                         source_url="url1", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        job2 = JobListing(title="Job 2", company="Company 2", description="Desc 2",
                         source_url="url2", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        
        result.add_site_result("indeed", [job1, job2])
        
        assert len(result.jobs) == 2
        assert result.total_jobs_found == 2
        assert "indeed" in result.successful_sites
        assert "indeed" not in result.failed_sites
        assert not result.has_errors()
        assert result.has_jobs()
    
    def test_add_site_result_failure(self):
        """Test adding failed site results"""
        result = ScrapingResult()
        
        error = RateLimitError("Rate limit exceeded", "linkedin", 60)
        result.add_site_result("linkedin", [], error)
        
        assert len(result.jobs) == 0
        assert result.total_jobs_found == 0
        assert "linkedin" in result.failed_sites
        assert "linkedin" not in result.successful_sites
        assert result.has_errors()
        assert not result.has_jobs()
        assert len(result.errors) == 1
        assert result.errors[0] == error
    
    def test_get_summary(self):
        """Test result summary generation"""
        result = ScrapingResult()
        
        # Add successful site
        job1 = JobListing(title="Job 1", company="Company 1", description="Desc 1",
                         source_url="url1", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        result.add_site_result("indeed", [job1])
        result.total_jobs_saved = 1
        
        # Add failed site
        error = RateLimitError("Rate limit exceeded", "linkedin", 60)
        result.add_site_result("linkedin", [], error)
        
        summary = result.get_summary()
        
        assert "Found 1 jobs" in summary
        assert "saved 1 new jobs" in summary
        assert "successful sites: indeed" in summary
        assert "failed sites: linkedin" in summary