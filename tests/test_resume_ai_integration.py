"""
Integration tests for Resume Service with AI functionality
"""
import pytest
import tempfile
import os
from job_matching_app.services import ResumeService, KeywordExtractionResult
from job_matching_app.models import Resume


class TestResumeAIIntegration:
    """Integration tests for Resume Service AI features"""
    
    @pytest.fixture
    def resume_service(self, require_ollama):
        """Create resume service instance with Ollama availability check"""
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
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_with_ai_success(self, resume_service, sample_latex_file):
        """Test successful AI keyword extraction integration"""
        # Upload resume
        resume = resume_service.upload_latex_resume(sample_latex_file)
        assert resume.id is not None
        
        # Extract keywords with AI
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify result
        assert isinstance(result, KeywordExtractionResult)
        assert result.confidence > 0
        assert len(result.keywords) > 0
        
        # Verify keywords were saved to database
        updated_resume = resume_service.get_resume_by_id(resume.id)
        assert updated_resume is not None
        assert len(updated_resume.extracted_keywords) > 0
    
    @pytest.mark.requires_ollama
    def test_extract_keywords_portuguese_content(self, resume_service, portuguese_latex_file):
        """Test AI keyword extraction with Portuguese content"""
        # Upload Portuguese resume
        resume = resume_service.upload_latex_resume(portuguese_latex_file)
        
        # Extract keywords with AI
        result = resume_service.extract_keywords_with_ai(resume.id)
        
        # Verify Portuguese language was detected
        assert result.language_detected == 'pt'
        assert len(result.keywords) > 0
    
    @pytest.mark.requires_ollama
    def test_get_ai_service_info_available(self, resume_service):
        """Test getting AI service info when available"""
        info = resume_service.get_ai_service_info()
        
        assert info['status'] == 'available'
        assert 'model' in info

    
    @pytest.mark.requires_ollama
    def test_keyword_extraction_preserves_user_keywords(self, resume_service, sample_latex_file):
        """Test that AI extraction preserves existing user keywords"""
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
    
    @pytest.mark.requires_ollama
    def test_multilingual_keyword_extraction_workflow(self, resume_service, sample_latex_file, portuguese_latex_file):
        """Test complete workflow with both English and Portuguese resumes"""
        # Upload English resume
        en_resume = resume_service.upload_latex_resume(sample_latex_file, "english_resume.tex")
        en_result = resume_service.extract_keywords_with_ai(en_resume.id)
        
        # Upload Portuguese resume
        pt_resume = resume_service.upload_latex_resume(portuguese_latex_file, "portuguese_resume.tex")
        pt_result = resume_service.extract_keywords_with_ai(pt_resume.id)
        
        # Verify both extractions worked
        assert en_result.language_detected == 'en'
        assert pt_result.language_detected == 'pt'
        
        # Verify both resumes have keywords
        en_updated = resume_service.get_resume_by_id(en_resume.id)
        pt_updated = resume_service.get_resume_by_id(pt_resume.id)
        
        assert len(en_updated.extracted_keywords) > 0
        assert len(pt_updated.extracted_keywords) > 0
    
    def test_extract_keywords_nonexistent_resume(self, resume_service):
        """Test keyword extraction with nonexistent resume ID"""
        with pytest.raises(ValueError, match="Resume with ID 99999 not found"):
            resume_service.extract_keywords_with_ai(99999)