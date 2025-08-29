"""
Unit tests for JobScrapingService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import requests

from job_matching_app.services.job_scraping_service import (
    JobScrapingService, 
    JobScrapingError, 
    RateLimitError, 
    SiteUnavailableError
)
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel


class TestJobScrapingService:
    """Test cases for JobScrapingService"""
    
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
    
    @patch('job_matching_app.services.job_scraping_service.get_db_context')
    def test_save_jobs_to_database(self, mock_get_db_context, scraping_service):
        """Test saving jobs to database"""
        # Mock database session
        mock_session = MagicMock()
        mock_get_db_context.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Create test jobs
        job1 = JobListing(
            title="Test Job 1",
            company="Test Company",
            description="Test description",
            source_url="https://example.com/job1",
            source_site="indeed",
            scraped_at=datetime.now(timezone.utc)
        )
        
        job2 = JobListing(
            title="Test Job 2",
            company="Test Company",
            description="Test description",
            source_url="https://example.com/job2",
            source_site="linkedin",
            scraped_at=datetime.now(timezone.utc)
        )
        
        jobs = [job1, job2]
        
        # Test saving
        saved_count = scraping_service.save_jobs_to_database(jobs)
        
        assert saved_count == 2
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_called_once()
    
    @patch('requests.Session.get')
    def test_scrape_indeed_success(self, mock_get, scraping_service, sample_indeed_html):
        """Test successful Indeed scraping"""
        # Mock response
        mock_response = Mock()
        mock_response.text = sample_indeed_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock time.sleep to avoid delays in tests
        with patch('time.sleep'):
            jobs = scraping_service.scrape_indeed(['python'], 'São Paulo', 1)
        
        assert len(jobs) == 2
        assert jobs[0].title == "Python Developer"
        assert jobs[1].title == "Junior JavaScript Developer"
    
    @patch('requests.Session.get')
    def test_scrape_indeed_rate_limit_error(self, mock_get, scraping_service):
        """Test Indeed scraping with rate limit error"""
        # Mock rate limit response
        mock_get.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        with pytest.raises(RateLimitError):
            scraping_service.scrape_indeed(['python'], 'São Paulo', 1)
    
    @patch('requests.Session.get')
    def test_scrape_linkedin_success(self, mock_get, scraping_service, sample_linkedin_html):
        """Test successful LinkedIn scraping"""
        # Mock response
        mock_response = Mock()
        mock_response.text = sample_linkedin_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock time.sleep to avoid delays in tests
        with patch('time.sleep'):
            jobs = scraping_service.scrape_linkedin(['data scientist'], 'Remote', 1)
        
        assert len(jobs) == 1
        assert jobs[0].title == "Data Scientist"
    
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_indeed')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_linkedin')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.save_jobs_to_database')
    def test_scrape_all_sites_success(self, mock_save, mock_linkedin, mock_indeed, scraping_service):
        """Test scraping all sites successfully"""
        # Mock scraping results
        indeed_jobs = [
            JobListing(title="Job 1", company="Company 1", description="Desc 1", 
                      source_url="url1", source_site="indeed", scraped_at=datetime.now(timezone.utc))
        ]
        linkedin_jobs = [
            JobListing(title="Job 2", company="Company 2", description="Desc 2",
                      source_url="url2", source_site="linkedin", scraped_at=datetime.now(timezone.utc))
        ]
        
        mock_indeed.return_value = indeed_jobs
        mock_linkedin.return_value = linkedin_jobs
        mock_save.return_value = 2
        
        # Test scraping all sites
        all_jobs = scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
        
        assert len(all_jobs) == 2
        mock_indeed.assert_called_once_with(['python'], 'São Paulo', 2)
        mock_linkedin.assert_called_once_with(['python'], 'São Paulo', 2)
        mock_save.assert_called_once()
    
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
        mock_linkedin.side_effect = SiteUnavailableError("LinkedIn failed")
        
        with patch.object(scraping_service, 'save_jobs_to_database', return_value=1):
            all_jobs = scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
        
        assert len(all_jobs) == 1
        assert all_jobs[0].source_site == "indeed"
    
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_indeed')
    @patch('job_matching_app.services.job_scraping_service.JobScrapingService.scrape_linkedin')
    def test_scrape_all_sites_complete_failure(self, mock_linkedin, mock_indeed, scraping_service):
        """Test scraping with all sites failing"""
        # Mock both sites failing
        mock_indeed.side_effect = SiteUnavailableError("Indeed failed")
        mock_linkedin.side_effect = SiteUnavailableError("LinkedIn failed")
        
        with pytest.raises(SiteUnavailableError):
            scraping_service.scrape_all_sites(['python'], 'São Paulo', 2)
    
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