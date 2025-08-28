"""
Unit tests for AI matching service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from job_matching_app.services.ai_matching_service import (
    AIMatchingService, 
    KeywordExtractionResult, 
    OllamaConnectionError
)


class TestAIMatchingService:
    """Test cases for AIMatchingService"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing"""
        return AIMatchingService()
    
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
    
    def test_initialization_without_ollama(self):
        """Test service initialization when Ollama is not available"""
        with patch('job_matching_app.services.ai_matching_service.OLLAMA_AVAILABLE', False):
            service = AIMatchingService()
            assert not service.is_ollama_available()
            assert service.client is None
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_initialization_with_ollama_success(self, mock_ollama):
        """Test successful Ollama initialization"""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        
        service = AIMatchingService()
        assert service.is_ollama_available()
        assert service.client == mock_ollama
        assert service.model_name == 'llama3.2:3b'
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_initialization_with_different_model(self, mock_ollama):
        """Test initialization when requested model is not available"""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama2:7b', 'size': '4GB'}]
        }
        
        service = AIMatchingService(model_name='nonexistent:model')
        assert service.model_name == 'llama2:7b'  # Should use first available
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_initialization_ollama_connection_error(self, mock_ollama):
        """Test initialization when Ollama connection fails"""
        mock_ollama.list.side_effect = Exception("Connection failed")
        
        service = AIMatchingService()
        assert not service.is_ollama_available()
        assert service.client is None
    
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
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_with_ollama_success(self, mock_ollama, ai_service, sample_latex_content):
        """Test successful keyword extraction with Ollama"""
        # Mock Ollama response
        mock_ollama.list.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        mock_ollama.generate.return_value = {
            'response': 'python, javascript, django, react, postgresql, docker, kubernetes, git, rest api, microservices'
        }
        
        # Reinitialize service with mocked Ollama
        ai_service._initialize_client()
        ai_service.client = mock_ollama
        
        result = ai_service.extract_resume_keywords(sample_latex_content)
        
        assert isinstance(result, KeywordExtractionResult)
        assert not result.fallback_used
        assert result.confidence == 0.8
        assert 'python' in result.keywords
        assert 'django' in result.keywords
        assert 'docker' in result.keywords
        
        # Verify Ollama was called with correct parameters
        mock_ollama.generate.assert_called_once()
        call_args = mock_ollama.generate.call_args
        assert call_args[1]['model'] == 'llama3.2:3b'
        assert 'temperature' in call_args[1]['options']
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_with_ollama_portuguese(self, mock_ollama, ai_service, sample_portuguese_latex):
        """Test keyword extraction with Portuguese content"""
        mock_ollama.list.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        mock_ollama.generate.return_value = {
            'response': 'python, javascript, django, react, postgresql, docker, kubernetes, git, api rest, microsserviços'
        }
        
        ai_service._initialize_client()
        ai_service.client = mock_ollama
        
        result = ai_service.extract_resume_keywords(sample_portuguese_latex)
        
        assert result.language_detected == 'pt'
        assert not result.fallback_used
        
        # Verify Portuguese prompt was used
        call_args = mock_ollama.generate.call_args
        prompt = call_args[1]['prompt']
        assert 'Analise o seguinte texto' in prompt
        assert 'habilidades técnicas' in prompt.lower()
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_ollama_failure(self, mock_ollama, ai_service, sample_latex_content):
        """Test fallback when Ollama extraction fails"""
        mock_ollama.list.return_value = {'models': [{'name': 'llama3.2:3b'}]}
        mock_ollama.generate.side_effect = Exception("Ollama service error")
        
        ai_service._initialize_client()
        ai_service.client = mock_ollama
        
        result = ai_service.extract_resume_keywords(sample_latex_content)
        
        assert isinstance(result, KeywordExtractionResult)
        assert result.fallback_used
        assert result.confidence == 0.5
        assert len(result.keywords) > 0
    
    def test_extract_keywords_fallback_only(self, ai_service, sample_latex_content):
        """Test fallback keyword extraction when Ollama is unavailable"""
        # Ensure Ollama is not available
        ai_service.client = None
        
        result = ai_service.extract_resume_keywords(sample_latex_content)
        
        assert isinstance(result, KeywordExtractionResult)
        assert result.fallback_used
        assert result.confidence == 0.5
        assert len(result.keywords) > 0
        
        # Should extract some technical keywords
        keywords_lower = [kw.lower() for kw in result.keywords]
        # Check for any of the expected technical keywords from the sample content
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
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_get_model_info_available(self, mock_ollama, ai_service):
        """Test getting model info when Ollama is available"""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        
        ai_service._initialize_client()
        ai_service.client = mock_ollama
        
        info = ai_service.get_model_info()
        
        assert info['status'] == 'available'
        assert info['model'] == 'llama3.2:3b'
        assert info['size'] == '2GB'
        assert info['fallback'] == 'none'
    
    def test_get_model_info_unavailable(self, ai_service):
        """Test getting model info when Ollama is unavailable"""
        ai_service.client = None
        
        info = ai_service.get_model_info()
        
        assert info['status'] == 'unavailable'
        assert info['model'] == 'none'
        assert info['fallback'] == 'rule-based extraction'
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_get_model_info_error(self, mock_ollama, ai_service):
        """Test getting model info when there's an error"""
        mock_ollama.list.side_effect = Exception("Connection error")
        
        ai_service._initialize_client()
        ai_service.client = mock_ollama
        
        info = ai_service.get_model_info()
        
        assert info['status'] == 'error'
        assert 'error' in info
        assert info['fallback'] == 'rule-based extraction'


class TestKeywordExtractionResult:
    """Test cases for KeywordExtractionResult dataclass"""
    
    def test_keyword_extraction_result_creation(self):
        """Test creating KeywordExtractionResult"""
        result = KeywordExtractionResult(
            keywords=['python', 'django', 'postgresql'],
            confidence=0.8,
            language_detected='en',
            fallback_used=False
        )
        
        assert result.keywords == ['python', 'django', 'postgresql']
        assert result.confidence == 0.8
        assert result.language_detected == 'en'
        assert not result.fallback_used
    
    def test_keyword_extraction_result_defaults(self):
        """Test KeywordExtractionResult with default values"""
        result = KeywordExtractionResult(
            keywords=['python'],
            confidence=0.9,
            language_detected='en'
        )
        
        assert not result.fallback_used  # Default should be False


class TestOllamaConnectionError:
    """Test cases for OllamaConnectionError exception"""
    
    def test_ollama_connection_error(self):
        """Test OllamaConnectionError exception"""
        error_msg = "Failed to connect to Ollama service"
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            raise OllamaConnectionError(error_msg)
        
        assert str(exc_info.value) == error_msg