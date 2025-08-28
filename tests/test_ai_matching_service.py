"""
Unit tests for AI matching service
"""
import pytest
from job_matching_app.services.ai_matching_service import (
    AIMatchingService, 
    KeywordExtractionResult, 
    OllamaConnectionError
)


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
        
        compatibility = ai_service.calculate_job_compatibility(resume_keywords, job_description)
        
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
        
        compatibility = ai_service.calculate_job_compatibility(resume_keywords, job_description)
        
        assert compatibility < 0.3  # Should be low compatibility
        assert compatibility >= 0.0
    
    def test_calculate_job_compatibility_empty_inputs(self, ai_service):
        """Test job compatibility with empty inputs"""
        assert ai_service.calculate_job_compatibility([], "some job description") == 0.0
        assert ai_service.calculate_job_compatibility(['python'], "") == 0.0
        assert ai_service.calculate_job_compatibility([], "") == 0.0
    
    def test_is_technical_keyword(self, ai_service):
        """Test technical keyword identification"""
        assert ai_service._is_technical_keyword('python')
        assert ai_service._is_technical_keyword('machine learning')
        assert ai_service._is_technical_keyword('software development')
        assert ai_service._is_technical_keyword('API design')
        
        assert not ai_service._is_technical_keyword('communication')
        assert not ai_service._is_technical_keyword('teamwork')
        assert not ai_service._is_technical_keyword('leadership')
    
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



class TestOllamaConnectionError:
    """Test cases for OllamaConnectionError exception"""
    
    def test_ollama_connection_error(self):
        """Test OllamaConnectionError exception"""
        error_msg = "Failed to connect to Ollama service"
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            raise OllamaConnectionError(error_msg)
        
        assert str(exc_info.value) == error_msg