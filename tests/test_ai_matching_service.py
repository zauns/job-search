"""
Unit tests for AI matching service
"""
import pytest
from datetime import datetime
from job_matching_app.services.ai_matching_service import (
    AIMatchingService, 
    KeywordExtractionResult, 
    JobMatchResult,
    OllamaConnectionError
)
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel


class TestAIMatchingService:
    """Test cases for AIMatchingService"""
    
    @pytest.fixture
    def ai_service(self, ai_service_with_ollama_check):
        """Create AI service instance for testing with Ollama availability check"""
        return ai_service_with_ollama_check
    
    @pytest.fixture
    def sample_latex_content(self):
        """Sample LaTeX resume content for testing"""
        return """
        \\documentclass{article}
        \\begin{document}
        \\section{Experience}
        Software Engineer at Tech Company
        - Developed web applications using Python, Django, and React
        - Worked with PostgreSQL databases and Docker containers
        - Implemented REST APIs and microservices architecture
        
        \\section{Skills}
        Programming Languages: Python, JavaScript, Java
        Frameworks: Django, React, Spring Boot
        Databases: PostgreSQL, MongoDB, Redis
        Tools: Docker, Kubernetes, Git, Jenkins
        
        \\section{Education}
        Bachelor of Computer Science
        \\end{document}
        """
    
    @pytest.fixture
    def sample_portuguese_latex(self):
        """Sample Portuguese LaTeX resume content"""
        return """
        \\documentclass{article}
        \\begin{document}
        \\section{Experiência}
        Desenvolvedor de Software na Empresa Tech
        - Desenvolveu aplicações web usando Python, Django e React
        - Trabalhou com bancos de dados PostgreSQL e containers Docker
        - Implementou APIs REST e arquitetura de microsserviços
        
        \\section{Habilidades}
        Linguagens de Programação: Python, JavaScript, Java
        Frameworks: Django, React, Spring Boot
        Bancos de Dados: PostgreSQL, MongoDB, Redis
        Ferramentas: Docker, Kubernetes, Git, Jenkins
        
        \\section{Formação}
        Bacharelado em Ciência da Computação
        \\end{document}
        """
    
    @pytest.mark.requires_ollama
    def test_initialization_requires_ollama(self, ai_service):
        """Test service initialization requires Ollama to be available"""
        # Service should initialize and connect to real Ollama
        assert ai_service.is_ollama_available()
        assert ai_service.client is not None
    
    @pytest.mark.requires_ollama
    def test_initialization_with_ollama_success(self, ai_service):
        """Test successful Ollama initialization"""
        assert ai_service.is_ollama_available()
        assert ai_service.client is not None
        assert ai_service.model_name is not None
    
    @pytest.mark.requires_ollama
    def test_initialization_with_different_model(self, require_ollama):
        """Test initialization when requested model is not available"""
        service = AIMatchingService(model_name='nonexistent:model')
        # Should use first available model from real Ollama
        assert service.model_name is not None
    
    def test_initialization_ollama_connection_error_without_ollama(self, ollama_availability):
        """Test initialization when Ollama connection fails"""
        if ollama_availability['available']:
            pytest.skip("Ollama is available, cannot test connection error scenario")
        
        # This test verifies that proper errors are raised when Ollama is unavailable
        with pytest.raises(OllamaConnectionError):
            AIMatchingService()
    
    def test_clean_latex_content(self, ai_service, sample_latex_content):
        """Test LaTeX content cleaning"""
        cleaned = ai_service._clean_latex_content(sample_latex_content)
        
        # Should remove LaTeX commands
        assert '\\documentclass' not in cleaned
        assert '\\section' not in cleaned
        assert '\\begin' not in cleaned
        assert '\\end' not in cleaned
        
        # Should preserve actual content
        assert 'Software Engineer' in cleaned
        assert 'Python' in cleaned
        assert 'Django' in cleaned
        assert 'PostgreSQL' in cleaned
    
    def test_detect_language_english(self, ai_service):
        """Test English language detection"""
        english_text = "Software Engineer with experience in Python development"
        language = ai_service._detect_language(english_text)
        assert language == 'en'
    
    def test_detect_language_portuguese(self, ai_service):
        """Test Portuguese language detection"""
        portuguese_text = "Desenvolvedor de Software com experiência em desenvolvimento Python"
        language = ai_service._detect_language(portuguese_text)
        assert language == 'pt'
    
    def test_clean_keywords(self, ai_service):
        """Test keyword cleaning and validation"""
        raw_keywords = [
            'Python', 'JAVASCRIPT', '  React  ', 'the', 'and', 'a', 'Docker',
            '', '  ', 'machine learning', 'API'
        ]
        
        cleaned = ai_service._clean_keywords(raw_keywords)
        
        # Should convert to lowercase and strip whitespace
        assert 'python' in cleaned
        assert 'javascript' in cleaned
        assert 'react' in cleaned
        assert 'docker' in cleaned
        assert 'machine learning' in cleaned
        assert 'api' in cleaned
        
        # Should remove stop words and empty strings
        assert 'the' not in cleaned
        assert 'and' not in cleaned
        assert 'a' not in cleaned
        assert '' not in cleaned
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_with_ollama_success(self, ai_service, sample_latex_content):
        """Test successful keyword extraction with Ollama"""
        result = ai_service.extract_resume_keywords(sample_latex_content)
        
        assert isinstance(result, KeywordExtractionResult)
        assert result.confidence > 0
        assert len(result.keywords) > 0
        assert result.language_detected in ['en', 'pt']
        
        # Should extract some technical keywords from the sample content
        keywords_lower = [kw.lower() for kw in result.keywords]
        expected_keywords = ['python', 'django', 'javascript', 'postgresql', 'docker']
        found_keywords = [kw for kw in expected_keywords if any(kw in keyword for keyword in keywords_lower)]
        assert len(found_keywords) > 0
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_with_ollama_portuguese(self, ai_service, sample_portuguese_latex):
        """Test keyword extraction with Portuguese content"""
        result = ai_service.extract_resume_keywords(sample_portuguese_latex)
        
        assert isinstance(result, KeywordExtractionResult)
        assert result.language_detected == 'pt'
        assert len(result.keywords) > 0
        
        # Should extract technical keywords from Portuguese content
        keywords_lower = [kw.lower() for kw in result.keywords]
        expected_keywords = ['python', 'django', 'javascript', 'postgresql', 'docker']
        found_keywords = [kw for kw in expected_keywords if any(kw in keyword for keyword in keywords_lower)]
        assert len(found_keywords) > 0
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_ollama_failure(self, ai_service, sample_latex_content):
        """Test behavior when Ollama extraction fails"""
        # Test with empty content - should handle gracefully or raise appropriate error
        invalid_content = ""
        
        try:
            result = ai_service.extract_resume_keywords(invalid_content)
            # If no exception, should return valid result with empty or minimal keywords
            assert isinstance(result, KeywordExtractionResult)
            assert len(result.keywords) >= 0  # May be empty for invalid content
        except OllamaConnectionError:
            # This is also acceptable behavior for invalid content
            pass
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_requires_ollama(self, ai_service, sample_latex_content):
        """Test that keyword extraction requires Ollama to be available"""
        result = ai_service.extract_resume_keywords(sample_latex_content)
        
        assert isinstance(result, KeywordExtractionResult)
        assert result.confidence > 0
        assert len(result.keywords) > 0
        
        # Should extract technical keywords using Ollama
        keywords_lower = [kw.lower() for kw in result.keywords]
        expected_keywords = ['python', 'django', 'javascript', 'java', 'react', 'postgresql', 'docker', 'kubernetes']
        found_keywords = [kw for kw in expected_keywords if any(kw in keyword for keyword in keywords_lower)]
        assert len(found_keywords) > 0, f"Expected to find at least one of {expected_keywords} in {keywords_lower}"
    
    def test_calculate_job_compatibility_high_match(self, ai_service):
        """Test job compatibility calculation with high match"""
        resume_keywords = ['python', 'django', 'postgresql', 'docker', 'rest api']
        job_description = """
        We are looking for a Python developer with experience in Django framework.
        The candidate should have knowledge of PostgreSQL databases and Docker containers.
        Experience with REST API development is required.
        """
        job_technologies = ['python', 'django', 'postgresql', 'docker']
        
        compatibility = ai_service.calculate_job_compatibility(resume_keywords, job_description, job_technologies)
        
        assert compatibility > 0.8  # Should be high compatibility
        assert compatibility <= 1.0
    
    def test_calculate_job_compatibility_low_match(self, ai_service):
        """Test job compatibility calculation with low match"""
        resume_keywords = ['python', 'django', 'postgresql', 'docker']
        job_description = """
        We are looking for a Java developer with Spring Boot experience.
        The candidate should have knowledge of Oracle databases and Kubernetes.
        Experience with GraphQL is preferred.
        """
        job_technologies = ['java', 'spring boot', 'oracle', 'kubernetes']
        
        compatibility = ai_service.calculate_job_compatibility(resume_keywords, job_description, job_technologies)
        
        assert compatibility < 0.3  # Should be low compatibility
        assert compatibility >= 0.0
    
    def test_calculate_job_compatibility_empty_inputs(self, ai_service):
        """Test job compatibility with empty inputs"""
        assert ai_service.calculate_job_compatibility([], "some job description") == 0.0
        assert ai_service.calculate_job_compatibility(['python'], "") == 0.0
        assert ai_service.calculate_job_compatibility([], "") == 0.0
    
    def test_calculate_job_compatibility_with_technologies(self, ai_service):
        """Test job compatibility calculation with technology list"""
        resume_keywords = ['python', 'react', 'mongodb']
        job_description = "Looking for a full-stack developer"
        job_technologies = ['python', 'react', 'mongodb', 'node.js']
        
        compatibility = ai_service.calculate_job_compatibility(resume_keywords, job_description, job_technologies)
        
        assert compatibility > 0.8  # Should match all technologies
        assert compatibility <= 1.0
    
    def test_is_technical_keyword(self, ai_service):
        """Test technical keyword identification"""
        assert ai_service._is_technical_keyword('python')
        assert ai_service._is_technical_keyword('machine learning')
        assert ai_service._is_technical_keyword('software development')
        assert ai_service._is_technical_keyword('API design')
        assert ai_service._is_technical_keyword('typescript')
        assert ai_service._is_technical_keyword('kubernetes')
        
        assert not ai_service._is_technical_keyword('communication')
        assert not ai_service._is_technical_keyword('teamwork')
        assert not ai_service._is_technical_keyword('leadership')
    
    def test_calculate_detailed_job_match(self, ai_service):
        """Test detailed job match calculation"""
        resume_keywords = ['python', 'django', 'postgresql', 'docker', 'rest api']
        
        job_listing = JobListing(
            id=1,
            title="Python Developer",
            company="Tech Corp",
            location="Remote",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.MID,
            technologies=['python', 'django', 'postgresql'],
            description="Looking for Python developer with Django and PostgreSQL experience",
            source_url="https://example.com/job/1",
            application_url="https://example.com/apply/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        result = ai_service.calculate_detailed_job_match(resume_keywords, job_listing)
        
        assert isinstance(result, JobMatchResult)
        assert result.job_listing == job_listing
        assert result.compatibility_score > 0.5
        assert len(result.matching_keywords) > 0
        assert result.keyword_match_ratio > 0.0
        assert result.technical_match_score > 0.0
    
    def test_rank_jobs_by_compatibility(self, ai_service):
        """Test job ranking by compatibility"""
        resume_keywords = ['python', 'django', 'postgresql', 'docker']
        
        # Create test job listings with different compatibility levels
        high_match_job = JobListing(
            id=1,
            title="Python Django Developer",
            company="High Match Corp",
            location="Remote",
            technologies=['python', 'django', 'postgresql', 'docker'],
            description="Python Django developer with PostgreSQL and Docker experience required",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        medium_match_job = JobListing(
            id=2,
            title="Full Stack Developer",
            company="Medium Match Corp",
            location="Remote",
            technologies=['python', 'react', 'mongodb'],
            description="Full stack developer with Python and React experience",
            source_url="https://example.com/job/2",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        low_match_job = JobListing(
            id=3,
            title="Java Developer",
            company="Low Match Corp",
            location="Remote",
            technologies=['java', 'spring', 'oracle'],
            description="Java developer with Spring framework experience",
            source_url="https://example.com/job/3",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        job_listings = [low_match_job, medium_match_job, high_match_job]  # Intentionally unordered
        
        ranked_results = ai_service.rank_jobs_by_compatibility(resume_keywords, job_listings)
        
        assert len(ranked_results) == 3
        assert isinstance(ranked_results[0], JobMatchResult)
        
        # Should be ranked by compatibility score (highest first)
        assert ranked_results[0].compatibility_score >= ranked_results[1].compatibility_score
        assert ranked_results[1].compatibility_score >= ranked_results[2].compatibility_score
        
        # High match job should be first
        assert ranked_results[0].job_listing.id == high_match_job.id
    
    def test_rank_jobs_empty_inputs(self, ai_service):
        """Test job ranking with empty inputs"""
        assert ai_service.rank_jobs_by_compatibility([], []) == []
        assert ai_service.rank_jobs_by_compatibility(['python'], []) == []
        
        job_listing = JobListing(
            id=1,
            title="Test Job",
            company="Test Corp",
            description="Test description",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        assert ai_service.rank_jobs_by_compatibility([], [job_listing]) == []
    
    def test_create_job_match_records(self, ai_service):
        """Test creation of JobMatch database records"""
        resume_id = 1
        
        job_listing = JobListing(
            id=1,
            title="Python Developer",
            company="Tech Corp",
            description="Python developer position",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        job_match_result = JobMatchResult(
            job_listing=job_listing,
            compatibility_score=0.85,
            matching_keywords=['python', 'django'],
            missing_keywords=['react'],
            keyword_match_ratio=0.67,
            technical_match_score=0.8,
            language_match_bonus=0.05
        )
        
        job_matches = ai_service.create_job_match_records(resume_id, [job_match_result])
        
        assert len(job_matches) == 1
        job_match = job_matches[0]
        
        assert job_match.resume_id == resume_id
        assert job_match.job_listing_id == job_listing.id
        assert job_match.compatibility_score == 0.85
        assert job_match.matching_keywords == ['python', 'django']
        assert job_match.missing_keywords == ['react']
        assert job_match.algorithm_version == 2
    
    def test_find_similar_terms(self, ai_service):
        """Test finding similar terms in text"""
        text = "We need experience with javascript and nodejs development"
        
        # Should find exact matches
        assert ai_service._find_similar_terms('javascript', text, threshold=0.7)
        assert ai_service._find_similar_terms('development', text, threshold=0.7)
        
        # Should find similar terms with lower threshold
        assert ai_service._find_similar_terms('node', text, threshold=0.5)
        
        # Should not find dissimilar terms
        assert not ai_service._find_similar_terms('python', text, threshold=0.7)
        assert not ai_service._find_similar_terms('database', text, threshold=0.7)
    
    def test_calculate_string_similarity(self, ai_service):
        """Test string similarity calculation"""
        # Identical strings
        assert ai_service._calculate_string_similarity('python', 'python') == 1.0
        
        # Similar strings
        similarity = ai_service._calculate_string_similarity('javascript', 'java')
        assert 0.0 < similarity < 1.0
        
        # Completely different strings
        similarity = ai_service._calculate_string_similarity('python', 'xyz')
        assert similarity < 0.5
        
        # Empty strings
        assert ai_service._calculate_string_similarity('', 'python') == 0.0
        assert ai_service._calculate_string_similarity('python', '') == 0.0
    
    def test_normalize_multilingual_keywords(self, ai_service):
        """Test multilingual keyword normalization"""
        pt_keywords = ['desenvolvimento', 'programação', 'python', 'django']
        
        # Normalize to English
        en_normalized = ai_service._normalize_multilingual_keywords(pt_keywords, 'en')
        assert 'development' in en_normalized
        assert 'programming' in en_normalized
        assert 'python' in en_normalized  # Technical terms should remain
        assert 'django' in en_normalized
        
        # Normalize to Portuguese
        en_keywords = ['development', 'programming', 'python', 'react']
        pt_normalized = ai_service._normalize_multilingual_keywords(en_keywords, 'pt')
        assert 'desenvolvimento' in pt_normalized
        assert 'programação' in pt_normalized
        assert 'python' in pt_normalized  # Technical terms should remain
        assert 'react' in pt_normalized
    
    def test_multilingual_job_matching(self, ai_service):
        """Test job matching with multilingual content"""
        # Portuguese resume keywords
        pt_resume_keywords = ['python', 'desenvolvimento web', 'banco de dados', 'django']
        
        # English job description
        en_job_description = "Looking for Python web development experience with database knowledge"
        
        compatibility = ai_service.calculate_job_compatibility(pt_resume_keywords, en_job_description)
        
        # Should have reasonable compatibility despite language difference
        assert compatibility > 0.3
        assert compatibility <= 1.0
    
    @pytest.mark.requires_ollama
    def test_get_model_info_available(self, ai_service):
        """Test getting model info when Ollama is available"""
        info = ai_service.get_model_info()
        
        assert info['status'] == 'available'
        assert info['model'] is not None
        assert 'size' in info or 'error' not in info
    
    def test_get_model_info_unavailable(self, ollama_availability):
        """Test getting model info when Ollama is unavailable"""
        if ollama_availability['available']:
            pytest.skip("Ollama service is available, cannot test unavailable scenario")
        
        # When Ollama is unavailable, service initialization should fail
        with pytest.raises(OllamaConnectionError):
            service = AIMatchingService()
            service.get_model_info()
    
    @pytest.mark.requires_ollama
    def test_get_model_info_success(self, ai_service):
        """Test getting model info when Ollama is working properly"""
        info = ai_service.get_model_info()
        
        # With real Ollama, we should get valid info or the service wouldn't be available
        assert info['status'] == 'available'
        assert info['model'] is not None


class TestKeywordExtractionResult:
    """Test cases for KeywordExtractionResult dataclass"""
    
    def test_keyword_extraction_result_creation(self):
        """Test creating KeywordExtractionResult"""
        result = KeywordExtractionResult(
            keywords=['python', 'django', 'postgresql'],
            confidence=0.8,
            language_detected='en'
        )
        
        assert result.keywords == ['python', 'django', 'postgresql']
        assert result.confidence == 0.8
        assert result.language_detected == 'en'
    
    def test_keyword_extraction_result_defaults(self):
        """Test KeywordExtractionResult with default values"""
        result = KeywordExtractionResult(
            keywords=['python'],
            confidence=0.9,
            language_detected='en'
        )


class TestJobMatchResult:
    """Test cases for JobMatchResult dataclass"""
    
    def test_job_match_result_creation(self):
        """Test creating JobMatchResult"""
        job_listing = JobListing(
            id=1,
            title="Python Developer",
            company="Tech Corp",
            description="Python development position",
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
        
        result = JobMatchResult(
            job_listing=job_listing,
            compatibility_score=0.85,
            matching_keywords=['python', 'django'],
            missing_keywords=['react'],
            keyword_match_ratio=0.67,
            technical_match_score=0.8,
            language_match_bonus=0.05
        )
        
        assert result.job_listing == job_listing
        assert result.compatibility_score == 0.85
        assert result.matching_keywords == ['python', 'django']
        assert result.missing_keywords == ['react']
        assert result.keyword_match_ratio == 0.67
        assert result.technical_match_score == 0.8
        assert result.language_match_bonus == 0.05



class TestOllamaConnectionError:
    """Test cases for OllamaConnectionError exception"""
    
    def test_ollama_connection_error(self):
        """Test OllamaConnectionError exception"""
        error_msg = "Failed to connect to Ollama service"
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            raise OllamaConnectionError(error_msg)
        
        assert str(exc_info.value) == error_msg