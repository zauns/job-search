"""
Integration tests for Resume Service with AI functionality
"""
import pytest
import tempfile
import os
from unittest.mock import patch, Mock
from job_matching_app.services import ResumeService, KeywordExtractionResult
from job_matching_app.models import Resume


class TestResumeAIIntegration:
    """Integration tests for Resume Service AI features"""
    
    @pytest.fixture
    def resume_service(self):
        """Create resume service instance"""
        return ResumeService()
    
    @pytest.fixture
    def sample_latex_file(self):
        """Create a temporary LaTeX file for testing"""
        latex_content = """
        \\documentclass{article}
        \\usepackage[utf8]{inputenc}
        \\begin{document}
        \\section{Experience}
        Senior Software Engineer at TechCorp (2020-2023)
        - Developed scalable web applications using Python and Django
        - Implemented microservices architecture with Docker and Kubernetes
        - Worked with PostgreSQL, Redis, and Elasticsearch
        - Built REST APIs and integrated third-party services
        
        \\section{Skills}
        Programming: Python, JavaScript, TypeScript, Java
        Frameworks: Django, React, Spring Boot, Express.js
        Databases: PostgreSQL, MongoDB, Redis, Elasticsearch
        DevOps: Docker, Kubernetes, AWS, Jenkins, Git
        
        \\section{Education}
        Master of Science in Computer Science
        University of Technology (2018-2020)
        \\end{document}
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as f:
            f.write(latex_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def portuguese_latex_file(self):
        """Create a temporary Portuguese LaTeX file for testing"""
        latex_content = """
        \\documentclass{article}
        \\usepackage[utf8]{inputenc}
        \\begin{document}
        \\section{Experiência}
        Engenheiro de Software Sênior na TechCorp (2020-2023)
        - Desenvolveu aplicações web escaláveis usando Python e Django
        - Implementou arquitetura de microsserviços com Docker e Kubernetes
        - Trabalhou com PostgreSQL, Redis e Elasticsearch
        - Construiu APIs REST e integrou serviços de terceiros
        
        \\section{Habilidades}
        Programação: Python, JavaScript, TypeScript, Java
        Frameworks: Django, React, Spring Boot, Express.js
        Bancos de Dados: PostgreSQL, MongoDB, Redis, Elasticsearch
        DevOps: Docker, Kubernetes, AWS, Jenkins, Git
        
        \\section{Formação}
        Mestrado em Ciência da Computação
        Universidade de Tecnologia (2018-2020)
        \\end{document}
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as f:
            f.write(latex_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_with_ai_success(self, mock_ollama, resume_service, sample_latex_file):
        """Test successful AI keyword extraction integration"""
        # Mock Ollama responses
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        mock_ollama.generate.return_value = {
            'response': 'python, django, docker, kubernetes, postgresql, redis, elasticsearch, rest api, microservices, javascript'
        }
        
        # Reinitialize AI service with mocked Ollama
        resume_service.ai_service._initialize_client()
        resume_service.ai_service.client = mock_ollama
        
        # Upload resume
        resume = resume_service.upload_latex_resume(sample_latex_file)
        assert resume.id is not None
        
        # Extract keywords with AI
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify result
        assert isinstance(result, KeywordExtractionResult)
        assert not result.fallback_used
        assert result.confidence == 0.8
        assert len(result.keywords) > 0
        
        # Verify keywords were saved to database
        updated_resume = resume_service.get_resume_by_id(resume.id)
        assert updated_resume is not None
        assert len(updated_resume.extracted_keywords) > 0
        assert 'python' in [kw.lower() for kw in updated_resume.extracted_keywords]
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_portuguese_content(self, mock_ollama, resume_service, portuguese_latex_file):
        """Test AI keyword extraction with Portuguese content"""
        # Mock Ollama responses
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        mock_ollama.generate.return_value = {
            'response': 'python, django, docker, kubernetes, postgresql, redis, elasticsearch, api rest, microsserviços, javascript'
        }
        
        # Reinitialize AI service with mocked Ollama
        resume_service.ai_service._initialize_client()
        resume_service.ai_service.client = mock_ollama
        
        # Upload Portuguese resume
        resume = resume_service.upload_latex_resume(portuguese_latex_file)
        
        # Extract keywords with AI
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify Portuguese language was detected
        assert result.language_detected == 'pt'
        assert not result.fallback_used
        
        # Verify Ollama was called with Portuguese prompt
        mock_ollama.generate.assert_called_once()
        call_args = mock_ollama.generate.call_args
        prompt = call_args[1]['prompt']
        assert 'Analise o seguinte texto' in prompt
    
    def test_extract_keywords_fallback_when_ollama_unavailable(self, resume_service, sample_latex_file):
        """Test fallback keyword extraction when Ollama is unavailable"""
        # Ensure AI service has no Ollama client
        resume_service.ai_service.client = None
        
        # Upload resume
        resume = resume_service.upload_latex_resume(sample_latex_file)
        
        # Extract keywords (should use fallback)
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify fallback was used
        assert result.fallback_used
        assert result.confidence == 0.5
        assert len(result.keywords) > 0
        
        # Should still extract some technical keywords
        keywords_lower = [kw.lower() for kw in result.keywords]
        # Check for any of the expected technical keywords from the sample content
        expected_keywords = ['python', 'django', 'javascript', 'java', 'react', 'postgresql', 'docker', 'kubernetes']
        found_keywords = [kw for kw in expected_keywords if any(kw in keyword for keyword in keywords_lower)]
        assert len(found_keywords) > 0, f"Expected to find at least one of {expected_keywords} in {keywords_lower}"
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_extract_keywords_ollama_error_fallback(self, mock_ollama, resume_service, sample_latex_file):
        """Test fallback when Ollama extraction fails"""
        # Mock Ollama to fail during generation
        mock_ollama.list.return_value = Mock()
        mock_ollama.list.return_value.models = [
            Mock(model='llama3.2:3b', size=2000000000)
        ]
        mock_ollama.generate.side_effect = Exception("Ollama service temporarily unavailable")
        
        # Force re-initialization of AI service with mocked ollama
        resume_service.ai_service._initialize_client()
        resume_service.ai_service.client = mock_ollama
        
        # Upload resume
        resume = resume_service.upload_latex_resume(sample_latex_file)
        
        # Extract keywords (should fallback after Ollama fails)
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify fallback was used
        assert result.fallback_used
        assert result.confidence == 0.5
        assert len(result.keywords) > 0
    
    def test_extract_keywords_nonexistent_resume(self, resume_service):
        """Test keyword extraction with nonexistent resume ID"""
        with pytest.raises(ValueError, match="Resume with ID 99999 not found"):
            resume_service.extract_keywords_with_ai(99999)
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_get_ai_service_info_available(self, mock_ollama, resume_service):
        """Test getting AI service info when available"""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        
        # Reinitialize AI service
        resume_service.ai_service._initialize_client()
        
        info = resume_service.get_ai_service_info()
        
        assert info['status'] == 'available'
        assert info['model'] == 'llama3.2:3b'
    
    def test_get_ai_service_info_unavailable(self, resume_service):
        """Test getting AI service info when unavailable"""
        # Ensure AI service is unavailable
        resume_service.ai_service.client = None
        
        info = resume_service.get_ai_service_info()
        
        assert info['status'] == 'unavailable'
        assert info['fallback'] == 'rule-based extraction'
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_keyword_extraction_preserves_user_keywords(self, mock_ollama, resume_service, sample_latex_file):
        """Test that AI extraction preserves existing user keywords"""
        # Mock Ollama
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        mock_ollama.generate.return_value = {
            'response': 'python, django, docker'
        }
        
        # Upload resume and set initial user keywords
        resume = resume_service.upload_latex_resume(sample_latex_file)
        initial_user_keywords = ['custom_skill', 'special_knowledge']
        resume_service.update_resume_keywords(resume.id, [], initial_user_keywords)
        
        # Extract keywords with AI
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify user keywords were preserved
        updated_resume = resume_service.get_resume_by_id(resume.id)
        assert updated_resume.user_keywords == initial_user_keywords
        assert len(updated_resume.extracted_keywords) > 0
    
    @patch('job_matching_app.services.ai_matching_service.ollama')
    def test_multilingual_keyword_extraction_workflow(self, mock_ollama, resume_service, sample_latex_file, portuguese_latex_file):
        """Test complete workflow with both English and Portuguese resumes"""
        # Mock Ollama
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.2:3b', 'size': '2GB'}]
        }
        
        # Different responses for different languages
        def mock_generate(**kwargs):
            prompt = kwargs.get('prompt', '')
            if 'Analise o seguinte texto' in prompt:
                return {'response': 'python, django, docker, kubernetes, postgresql, microsserviços'}
            else:
                return {'response': 'python, django, docker, kubernetes, postgresql, microservices'}
        
        mock_ollama.generate.side_effect = mock_generate
        
        # Reinitialize AI service with mocked Ollama
        resume_service.ai_service._initialize_client()
        resume_service.ai_service.client = mock_ollama
        
        # Upload English resume
        en_resume = resume_service.upload_latex_resume(sample_latex_file, "english_resume.tex")
        en_result = resume_service.extract_keywords_with_ai(en_resume.id)
        
        # Upload Portuguese resume
        pt_resume = resume_service.upload_latex_resume(portuguese_latex_file, "portuguese_resume.tex")
        pt_result = resume_service.extract_keywords_with_ai(pt_resume.id)
        
        # Verify both extractions worked
        assert en_result.language_detected == 'en'
        assert pt_result.language_detected == 'pt'
        assert not en_result.fallback_used
        assert not pt_result.fallback_used
        
        # Verify both resumes have keywords
        en_updated = resume_service.get_resume_by_id(en_resume.id)
        pt_updated = resume_service.get_resume_by_id(pt_resume.id)
        
        assert len(en_updated.extracted_keywords) > 0
        assert len(pt_updated.extracted_keywords) > 0
        
        # Verify Ollama was called twice with different prompts
        assert mock_ollama.generate.call_count == 2
    
    def test_ai_service_integration_error_handling(self, resume_service, sample_latex_file):
        """Test error handling in AI service integration"""
        # Upload resume
        resume = resume_service.upload_latex_resume(sample_latex_file)
        
        # Mock AI service to raise an exception
        original_extract = resume_service.ai_service.extract_resume_keywords
        
        def mock_extract_error(content):
            raise Exception("AI service internal error")
        
        resume_service.ai_service.extract_resume_keywords = mock_extract_error
        
        # Should handle the error gracefully
        with pytest.raises(Exception, match="AI service internal error"):
            resume_service.extract_keywords_with_ai(resume.id)
        
        # Restore original method
        resume_service.ai_service.extract_resume_keywords = original_extract