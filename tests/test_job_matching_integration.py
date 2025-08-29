"""
Integration tests for job matching and ranking workflow
"""
import pytest
from datetime import datetime
from job_matching_app.services.ai_matching_service import AIMatchingService
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel


class TestJobMatchingIntegration:
    """Integration tests for complete job matching workflow"""
    
    @pytest.fixture
    def ai_service(self, ai_service_with_ollama_check):
        """Create AI service instance for testing"""
        return ai_service_with_ollama_check
    
    @pytest.fixture
    def sample_job_listings(self):
        """Create sample job listings for testing"""
        return [
            JobListing(
                id=1,
                title="Senior Python Developer",
                company="TechCorp",
                location="São Paulo",
                remote_type=RemoteType.HYBRID,
                experience_level=ExperienceLevel.SENIOR,
                technologies=['python', 'django', 'postgresql', 'docker', 'kubernetes'],
                description="""
                Estamos procurando um desenvolvedor Python sênior com experiência em Django.
                O candidato deve ter conhecimento em PostgreSQL, Docker e Kubernetes.
                Experiência com desenvolvimento de APIs REST é obrigatória.
                """,
                source_url="https://example.com/job/1",
                application_url="https://example.com/apply/1",
                source_site="example",
                scraped_at=datetime.now()
            ),
            JobListing(
                id=2,
                title="Full Stack Developer",
                company="StartupXYZ",
                location="Remote",
                remote_type=RemoteType.REMOTE,
                experience_level=ExperienceLevel.MID,
                technologies=['python', 'react', 'mongodb', 'node.js'],
                description="""
                We are looking for a full-stack developer with Python and React experience.
                Knowledge of MongoDB and Node.js is preferred.
                Experience with modern web development practices required.
                """,
                source_url="https://example.com/job/2",
                application_url="https://example.com/apply/2",
                source_site="example",
                scraped_at=datetime.now()
            ),
            JobListing(
                id=3,
                title="Java Backend Developer",
                company="Enterprise Inc",
                location="Rio de Janeiro",
                remote_type=RemoteType.ONSITE,
                experience_level=ExperienceLevel.MID,
                technologies=['java', 'spring boot', 'oracle', 'microservices'],
                description="""
                Java backend developer position with Spring Boot experience.
                Oracle database knowledge and microservices architecture experience required.
                Strong understanding of enterprise software development needed.
                """,
                source_url="https://example.com/job/3",
                application_url="https://example.com/apply/3",
                source_site="example",
                scraped_at=datetime.now()
            ),
            JobListing(
                id=4,
                title="DevOps Engineer",
                company="CloudTech",
                location="Brasília",
                remote_type=RemoteType.REMOTE,
                experience_level=ExperienceLevel.SENIOR,
                technologies=['docker', 'kubernetes', 'aws', 'terraform', 'python'],
                description="""
                DevOps engineer with strong containerization and cloud experience.
                Docker, Kubernetes, and AWS expertise required.
                Python scripting and Terraform knowledge preferred.
                """,
                source_url="https://example.com/job/4",
                application_url="https://example.com/apply/4",
                source_site="example",
                scraped_at=datetime.now()
            )
        ]
    
    @pytest.mark.requires_ollama
    def test_complete_job_matching_workflow(self, ai_service, sample_job_listings):
        """Test complete job matching and ranking workflow"""
        # Sample resume keywords (mix of Portuguese and English technical terms)
        resume_keywords = [
            'python', 'django', 'postgresql', 'docker', 'rest api',
            'desenvolvimento web', 'banco de dados', 'kubernetes', 'aws'
        ]
        
        # Rank jobs by compatibility
        ranked_results = ai_service.rank_jobs_by_compatibility(resume_keywords, sample_job_listings)
        
        # Verify results
        assert len(ranked_results) == 4
        
        # Results should be sorted by compatibility score
        for i in range(len(ranked_results) - 1):
            assert ranked_results[i].compatibility_score >= ranked_results[i + 1].compatibility_score
        
        # Check that we have reasonable compatibility scores
        best_match = ranked_results[0]
        assert best_match.compatibility_score > 0.5  # Should have good compatibility
        
        # Verify detailed match information
        assert len(best_match.matching_keywords) > 0
        assert best_match.keyword_match_ratio > 0.0
        assert best_match.technical_match_score >= 0.0
        
        # The Python/Django job should likely be the best match
        python_jobs = [r for r in ranked_results if 'python' in r.job_listing.technologies]
        assert len(python_jobs) > 0
        
        # DevOps job should also rank well due to Docker/Kubernetes/AWS overlap
        devops_job = next((r for r in ranked_results if r.job_listing.title == "DevOps Engineer"), None)
        assert devops_job is not None
        assert devops_job.compatibility_score > 0.3
        
        # Java job should have lower compatibility
        java_job = next((r for r in ranked_results if r.job_listing.title == "Java Backend Developer"), None)
        assert java_job is not None
        assert java_job.compatibility_score < best_match.compatibility_score
    
    @pytest.mark.requires_ollama
    def test_multilingual_matching_workflow(self, ai_service, sample_job_listings):
        """Test job matching with multilingual keywords"""
        # Portuguese-heavy resume keywords
        pt_resume_keywords = [
            'python', 'desenvolvimento', 'programação', 'banco de dados',
            'django', 'postgresql', 'docker', 'api rest'
        ]
        
        # Rank jobs
        ranked_results = ai_service.rank_jobs_by_compatibility(pt_resume_keywords, sample_job_listings)
        
        assert len(ranked_results) == 4
        
        # Should still find good matches despite language differences
        best_match = ranked_results[0]
        assert best_match.compatibility_score > 0.3
        
        # Should have some matching keywords
        assert len(best_match.matching_keywords) > 0
        
        # Technical terms should match regardless of description language
        technical_matches = [kw for kw in best_match.matching_keywords 
                           if kw.lower() in ['python', 'django', 'postgresql', 'docker']]
        assert len(technical_matches) > 0
    
    def test_job_match_record_creation(self, ai_service, sample_job_listings):
        """Test creation of JobMatch database records"""
        resume_id = 1
        resume_keywords = ['python', 'django', 'postgresql', 'docker']
        
        # Get ranked results
        ranked_results = ai_service.rank_jobs_by_compatibility(resume_keywords, sample_job_listings)
        
        # Create database records
        job_matches = ai_service.create_job_match_records(resume_id, ranked_results)
        
        assert len(job_matches) == len(sample_job_listings)
        
        # Verify record structure
        for job_match in job_matches:
            assert job_match.resume_id == resume_id
            assert job_match.job_listing_id in [job.id for job in sample_job_listings]
            assert 0.0 <= job_match.compatibility_score <= 1.0
            assert isinstance(job_match.matching_keywords, list)
            assert isinstance(job_match.missing_keywords, list)
            assert job_match.algorithm_version == 2
        
        # Records should be in the same order as ranked results
        for i, (job_match, ranked_result) in enumerate(zip(job_matches, ranked_results)):
            assert job_match.job_listing_id == ranked_result.job_listing.id
            assert job_match.compatibility_score == ranked_result.compatibility_score
            assert job_match.matching_keywords == ranked_result.matching_keywords
            assert job_match.missing_keywords == ranked_result.missing_keywords
    
    def test_empty_inputs_handling(self, ai_service):
        """Test handling of empty inputs"""
        # Empty keywords
        assert ai_service.rank_jobs_by_compatibility([], []) == []
        
        # Empty job listings
        assert ai_service.rank_jobs_by_compatibility(['python'], []) == []
        
        # Empty keywords with jobs
        job_listing = JobListing(
            id=1,
            title="Test Job",
            company="Test Corp",
            description="Test description",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        results = ai_service.rank_jobs_by_compatibility([], [job_listing])
        assert results == []
    
    def test_single_job_matching(self, ai_service):
        """Test matching against a single job"""
        resume_keywords = ['python', 'django', 'postgresql']
        
        job_listing = JobListing(
            id=1,
            title="Python Developer",
            company="Tech Corp",
            technologies=['python', 'django', 'postgresql'],
            description="Python developer with Django and PostgreSQL experience",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        results = ai_service.rank_jobs_by_compatibility(resume_keywords, [job_listing])
        
        assert len(results) == 1
        result = results[0]
        
        assert result.job_listing == job_listing
        assert result.compatibility_score > 0.8  # Should be high match
        assert len(result.matching_keywords) == 3  # All keywords should match
        assert len(result.missing_keywords) == 0
        assert result.keyword_match_ratio == 1.0