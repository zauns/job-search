"""
Unit tests for job listing display CLI functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from click.testing import CliRunner

from job_matching_app.main import jobs, _display_job_listings, _display_job_matches, _display_job_details
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel
from job_matching_app.models.job_match import JobMatch


class TestJobDisplayCLI:
    """Test cases for job listing display CLI functionality"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner"""
        return CliRunner()
    
    @pytest.fixture
    def sample_job_listing(self):
        """Create a sample job listing"""
        return JobListing(
            id=1,
            title="Senior Python Developer",
            company="Tech Corp",
            location="San Francisco, CA",
            remote_type=RemoteType.HYBRID,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["Python", "Django", "PostgreSQL", "Docker"],
            description="We are looking for a senior Python developer to join our team...",
            source_url="https://example.com/job/1",
            application_url="https://example.com/apply/1",
            source_site="indeed",
            scraped_at=datetime(2024, 1, 15, 10, 30)
        )
    
    @pytest.fixture
    def sample_job_match(self):
        """Create a sample job match"""
        return JobMatch(
            id=1,
            resume_id=1,
            job_listing_id=1,
            compatibility_score=0.85,
            matching_keywords=["python", "django", "postgresql"],
            missing_keywords=["react", "javascript"],
            algorithm_version=2
        )
    
    @pytest.fixture
    def sample_job_listings(self):
        """Create multiple sample job listings"""
        jobs = []
        for i in range(5):
            job = JobListing(
                id=i + 1,
                title=f"Software Engineer {i + 1}",
                company=f"Company {i + 1}",
                location=f"City {i + 1}",
                remote_type=RemoteType.REMOTE if i % 2 == 0 else RemoteType.ONSITE,
                experience_level=ExperienceLevel.JUNIOR if i % 2 == 0 else ExperienceLevel.SENIOR,
                technologies=["Python", "Django"] if i % 2 == 0 else ["JavaScript", "React"],
                description=f"Job description {i + 1}",
                source_url=f"https://example.com/job/{i + 1}",
                application_url=f"https://example.com/apply/{i + 1}",
                source_site="indeed" if i % 2 == 0 else "linkedin",
                scraped_at=datetime.now()
            )
            jobs.append(job)
        return jobs
    
    def test_jobs_list_command_basic(self, runner):
        """Test basic jobs list command"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_listings_paginated.return_value = ([], 0, 0)
            
            result = runner.invoke(jobs, ['list'])
            
            assert result.exit_code == 0
            mock_service.get_job_listings_paginated.assert_called_once()
    
    def test_jobs_list_command_with_pagination(self, runner):
        """Test jobs list command with pagination options"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_listings_paginated.return_value = ([], 0, 0)
            
            result = runner.invoke(jobs, ['list', '--page', '2', '--per-page', '10'])
            
            assert result.exit_code == 0
            mock_service.get_job_listings_paginated.assert_called_with(
                2, 10, 'scraped_at', 'desc', {}
            )
    
    def test_jobs_list_command_with_filters(self, runner):
        """Test jobs list command with filters"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_listings_paginated.return_value = ([], 0, 0)
            
            result = runner.invoke(jobs, [
                'list',
                '--company', 'Tech Corp',
                '--location', 'San Francisco',
                '--remote-type', 'remote',
                '--experience-level', 'senior'
            ])
            
            assert result.exit_code == 0
            # Verify filters were passed
            call_args = mock_service.get_job_listings_paginated.call_args
            filters = call_args[0][4]  # 5th argument is filters
            assert filters['company'] == 'Tech Corp'
            assert filters['location'] == 'San Francisco'
            assert filters['remote_type'] == 'remote'
            assert filters['experience_level'] == 'senior'
    
    def test_jobs_list_command_with_sorting(self, runner):
        """Test jobs list command with sorting options"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_listings_paginated.return_value = ([], 0, 0)
            
            result = runner.invoke(jobs, [
                'list',
                '--sort-by', 'title',
                '--sort-order', 'asc'
            ])
            
            assert result.exit_code == 0
            mock_service.get_job_listings_paginated.assert_called_with(
                1, None, 'title', 'asc', {}
            )
    
    def test_jobs_search_command(self, runner):
        """Test jobs search command"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.search_jobs.return_value = ([], 0, 0)
            
            result = runner.invoke(jobs, ['search', 'python developer'])
            
            assert result.exit_code == 0
            mock_service.search_jobs.assert_called_with(
                'python developer', 1, None, 'scraped_at', 'desc'
            )
    
    def test_jobs_show_command(self, runner, sample_job_listing):
        """Test jobs show command"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_by_id.return_value = sample_job_listing
            
            with patch('job_matching_app.main._display_job_details') as mock_display:
                result = runner.invoke(jobs, ['show', '1'])
                
                assert result.exit_code == 0
                mock_service.get_job_by_id.assert_called_with(1)
                mock_display.assert_called_once_with(sample_job_listing, None)
    
    def test_jobs_show_command_with_resume(self, runner, sample_job_listing, sample_job_match):
        """Test jobs show command with resume compatibility"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_with_match.return_value = (sample_job_listing, sample_job_match)
            
            with patch('job_matching_app.main._display_job_details') as mock_display:
                result = runner.invoke(jobs, ['show', '1', '--resume-id', '1'])
                
                assert result.exit_code == 0
                mock_service.get_job_with_match.assert_called_with(1, 1)
                mock_display.assert_called_once_with(sample_job_listing, sample_job_match)
    
    def test_jobs_show_command_not_found(self, runner):
        """Test jobs show command when job not found"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_by_id.return_value = None
            
            result = runner.invoke(jobs, ['show', '999'])
            
            assert result.exit_code == 0
            assert "Job with ID 999 not found" in result.output
    
    def test_jobs_match_command(self, runner):
        """Test jobs match command"""
        with patch('job_matching_app.main.ResumeService') as mock_resume_service_class:
            with patch('job_matching_app.main.JobListingService') as mock_job_service_class:
                mock_resume_service = Mock()
                mock_job_service = Mock()
                mock_resume_service_class.return_value = mock_resume_service
                mock_job_service_class.return_value = mock_job_service
                
                # Mock resume exists
                mock_resume = Mock()
                mock_resume.filename = "test_resume.tex"
                mock_resume_service.get_resume_by_id.return_value = mock_resume
                
                # Mock job matches
                mock_job_service.get_job_listings_with_matches.return_value = ([], 0, 0)
                
                result = runner.invoke(jobs, ['match', '1'])
                
                assert result.exit_code == 0
                mock_resume_service.get_resume_by_id.assert_called_with(1)
                mock_job_service.get_job_listings_with_matches.assert_called()
    
    def test_jobs_match_command_resume_not_found(self, runner):
        """Test jobs match command when resume not found"""
        with patch('job_matching_app.main.ResumeService') as mock_resume_service_class:
            mock_resume_service = Mock()
            mock_resume_service_class.return_value = mock_resume_service
            mock_resume_service.get_resume_by_id.return_value = None
            
            result = runner.invoke(jobs, ['match', '999'])
            
            assert result.exit_code == 0
            assert "Resume with ID 999 not found" in result.output
    
    def test_jobs_stats_command(self, runner):
        """Test jobs stats command"""
        with patch('job_matching_app.main.JobListingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_job_statistics.return_value = {
                'total_jobs': 100,
                'remote_type_distribution': {'remote': 60, 'onsite': 40},
                'experience_level_distribution': {'junior': 30, 'senior': 70},
                'source_site_distribution': {'indeed': 50, 'linkedin': 50}
            }
            
            result = runner.invoke(jobs, ['stats'])
            
            assert result.exit_code == 0
            assert "Total Jobs: 100" in result.output
            assert "Remote: 60" in result.output
            mock_service.get_job_statistics.assert_called_once()
    
    @patch('job_matching_app.main.console')
    def test_display_job_listings(self, mock_console, sample_job_listings):
        """Test _display_job_listings function"""
        _display_job_listings(sample_job_listings, 1, 2, 5)
        
        # Verify console.print was called
        assert mock_console.print.call_count >= 2  # At least table and pagination info
    
    @patch('job_matching_app.main.console')
    def test_display_job_listings_empty(self, mock_console):
        """Test _display_job_listings with empty list"""
        _display_job_listings([], 1, 0, 0)
        
        # Should still print table and pagination info
        assert mock_console.print.call_count >= 2
    
    @patch('job_matching_app.main.console')
    def test_display_job_matches(self, mock_console, sample_job_listings, sample_job_match):
        """Test _display_job_matches function"""
        job_matches = [(sample_job_listings[0], sample_job_match)]
        _display_job_matches(job_matches, 1, 1, 1)
        
        # Verify console.print was called
        assert mock_console.print.call_count >= 2
    
    @patch('job_matching_app.main.console')
    def test_display_job_matches_no_match(self, mock_console, sample_job_listings):
        """Test _display_job_matches with job that has no match"""
        job_matches = [(sample_job_listings[0], None)]
        _display_job_matches(job_matches, 1, 1, 1)
        
        # Verify console.print was called
        assert mock_console.print.call_count >= 2
    
    @patch('job_matching_app.main.console')
    def test_display_job_details_basic(self, mock_console, sample_job_listing):
        """Test _display_job_details function without match"""
        _display_job_details(sample_job_listing)
        
        # Should print multiple panels (job info, technologies, description, links)
        assert mock_console.print.call_count >= 4
    
    @patch('job_matching_app.main.console')
    def test_display_job_details_with_match(self, mock_console, sample_job_listing, sample_job_match):
        """Test _display_job_details function with match"""
        _display_job_details(sample_job_listing, sample_job_match)
        
        # Should print additional compatibility panel
        assert mock_console.print.call_count >= 5
    
    @patch('job_matching_app.main.console')
    def test_display_job_details_long_description(self, mock_console, sample_job_listing):
        """Test _display_job_details with long description"""
        # Create job with very long description
        sample_job_listing.description = "A" * 1500  # Longer than 1000 chars
        
        _display_job_details(sample_job_listing)
        
        # Verify console.print was called
        assert mock_console.print.call_count >= 4
    
    def test_job_listing_display_properties(self, sample_job_listing):
        """Test job listing display properties"""
        # Test display_location
        assert "San Francisco, CA (Hybrid)" in sample_job_listing.display_location
        
        # Test display_tags
        tags = sample_job_listing.display_tags
        assert "Hybrid" in tags
        assert "Senior" in tags
        assert "Python" in tags
        assert len(tags) >= 3
    
    def test_job_match_display_properties(self, sample_job_match):
        """Test job match display properties"""
        # Test compatibility_percentage
        assert sample_job_match.compatibility_percentage == 85.0
        
        # Test match_quality
        assert sample_job_match.match_quality == "Excellent"
        
        # Test keyword_match_ratio
        expected_ratio = 3 / 5  # 3 matching, 2 missing = 5 total
        assert sample_job_match.keyword_match_ratio == expected_ratio
    
    def test_job_match_quality_levels(self):
        """Test different job match quality levels"""
        # Excellent match
        match_excellent = JobMatch(compatibility_score=0.85)
        assert match_excellent.match_quality == "Excellent"
        
        # Good match
        match_good = JobMatch(compatibility_score=0.65)
        assert match_good.match_quality == "Good"
        
        # Fair match
        match_fair = JobMatch(compatibility_score=0.45)
        assert match_fair.match_quality == "Fair"
        
        # Poor match
        match_poor = JobMatch(compatibility_score=0.25)
        assert match_poor.match_quality == "Poor"
    
    def test_remote_type_display_variations(self):
        """Test different remote type display variations"""
        # Remote job
        job_remote = JobListing(
            location="New York",
            remote_type=RemoteType.REMOTE
        )
        assert job_remote.display_location == "New York (Remote)"
        
        # Hybrid job
        job_hybrid = JobListing(
            location="Boston",
            remote_type=RemoteType.HYBRID
        )
        assert job_hybrid.display_location == "Boston (Hybrid)"
        
        # Onsite job
        job_onsite = JobListing(
            location="Chicago",
            remote_type=RemoteType.ONSITE
        )
        assert job_onsite.display_location == "Chicago"
        
        # Remote with no location
        job_remote_no_loc = JobListing(
            location=None,
            remote_type=RemoteType.REMOTE
        )
        assert job_remote_no_loc.display_location == "Remote"
        
        # No location, no remote type
        job_no_info = JobListing(
            location=None,
            remote_type=None
        )
        assert job_no_info.display_location == "Location not specified"
    
    def test_display_tags_variations(self):
        """Test display tags with different job configurations"""
        # Job with all attributes
        job_full = JobListing(
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=["Python", "Django", "React", "Node.js", "AWS"]
        )
        tags = job_full.display_tags
        assert "Remote" in tags
        assert "Senior" in tags
        assert "Python" in tags
        assert "Django" in tags
        assert "React" in tags
        assert len(tags) == 5  # Remote + Senior + 3 technologies
        
        # Job with minimal attributes
        job_minimal = JobListing(
            remote_type=None,
            experience_level=None,
            technologies=["Python"]
        )
        tags = job_minimal.display_tags
        assert "Python" in tags
        assert len(tags) == 1
        
        # Job with no technologies
        job_no_tech = JobListing(
            remote_type=RemoteType.HYBRID,
            experience_level=ExperienceLevel.JUNIOR,
            technologies=[]
        )
        tags = job_no_tech.display_tags
        assert "Hybrid" in tags
        assert "Junior" in tags
        assert len(tags) == 2