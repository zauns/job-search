"""
Unit tests for resume adaptation system
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from job_matching_app.services.resume_service import ResumeService
from job_matching_app.services.ai_matching_service import AIMatchingService, OllamaConnectionError
from job_matching_app.services.latex_editor_service import LaTeXEditorService, LaTeXValidationResult
from job_matching_app.models import Resume, AdaptedResumeDraft, JobListing
from job_matching_app.models.job_listing import RemoteType, ExperienceLevel


class TestResumeAdaptation:
    """Test resume adaptation functionality"""
    
    @pytest.fixture
    def resume_service(self):
        """Create resume service instance"""
        return ResumeService()
    
    @pytest.fixture
    def sample_resume(self):
        """Create sample resume"""
        return Resume(
            id=1,
            filename="test_resume.tex",
            latex_content="""\\documentclass{article}
\\begin{document}
\\section{Experience}
Software Developer at TechCorp
\\end{document}""",
            extracted_keywords=["python", "django", "sql"],
            user_keywords=["machine learning"]
        )
    
    @pytest.fixture
    def sample_job(self):
        """Create sample job listing"""
        return JobListing(
            id=1,
            title="Senior Python Developer",
            company="DataCorp",
            description="Looking for experienced Python developer with Django and PostgreSQL skills",
            technologies=["python", "django", "postgresql", "docker"],
            experience_level=ExperienceLevel.SENIOR,
            remote_type=RemoteType.REMOTE,
            source_url="https://example.com/job/1",
            source_site="example",
            scraped_at=datetime.now()
        )
    
    @patch('job_matching_app.services.resume_service.get_db_context')
    def test_adapt_resume_for_job_success(self, mock_db_context, resume_service, sample_resume, sample_job):
        """Test successful resume adaptation"""
        # Mock database operations
        mock_db = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        # Mock resume retrieval
        with patch.object(resume_service, 'get_resume_by_id', return_value=sample_resume):
            # Mock job retrieval
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_job, None]  # job exists, no existing draft
            
            # Mock AI service adaptation
            adapted_latex = """\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Software Developer at TechCorp - Python, Django, PostgreSQL
\\end{document}"""
            
            with patch.object(resume_service.ai_service, 'adapt_resume_content', return_value=adapted_latex):
                # Mock draft creation
                mock_draft = Mock()
                mock_draft.id = None  # Initially no ID
                
                def mock_refresh(draft):
                    draft.id = 123  # Set ID during refresh
                
                mock_db.add.return_value = None
                mock_db.commit.return_value = None
                mock_db.refresh.side_effect = mock_refresh
                
                # Mock the draft creation
                with patch('job_matching_app.models.resume.AdaptedResumeDraft', return_value=mock_draft):
                    result = resume_service.adapt_resume_for_job(1, 1)
                    
                    assert result == 123
                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called_once()
                    mock_db.refresh.assert_called_once()
    
    @patch('job_matching_app.services.resume_service.get_db_context')
    def test_adapt_resume_existing_draft(self, mock_db_context, resume_service, sample_resume, sample_job):
        """Test adaptation when draft already exists"""
        mock_db = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        # Mock existing draft
        existing_draft = Mock()
        existing_draft.id = 456
        
        with patch.object(resume_service, 'get_resume_by_id', return_value=sample_resume):
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_job, existing_draft]
            
            result = resume_service.adapt_resume_for_job(1, 1)
            
            assert result == 456
    
    def test_adapt_resume_invalid_resume_id(self, resume_service):
        """Test adaptation with invalid resume ID"""
        with patch.object(resume_service, 'get_resume_by_id', return_value=None):
            with pytest.raises(ValueError, match="Resume with ID 999 not found"):
                resume_service.adapt_resume_for_job(999, 1)
    
    @patch('job_matching_app.services.resume_service.get_db_context')
    def test_adapt_resume_invalid_job_id(self, mock_db_context, resume_service, sample_resume):
        """Test adaptation with invalid job ID"""
        mock_db = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        with patch.object(resume_service, 'get_resume_by_id', return_value=sample_resume):
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(ValueError, match="Job listing with ID 999 not found"):
                resume_service.adapt_resume_for_job(1, 999)
    
    @patch('job_matching_app.services.resume_service.get_db_context')
    def test_get_adapted_resume_draft(self, mock_db_context, resume_service):
        """Test getting adapted resume draft"""
        mock_db = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        # Mock draft
        mock_draft = Mock()
        mock_draft.id = 1
        mock_draft.original_resume_id = 1
        mock_draft.job_id = 1
        mock_draft.adapted_latex_content = "\\documentclass{article}..."
        mock_draft.is_user_edited = False
        mock_draft.created_at = datetime.now()
        mock_draft.updated_at = datetime.now()
        
        # Mock related objects
        mock_resume = Mock()
        mock_resume.filename = "test.tex"
        mock_job = Mock()
        mock_job.title = "Developer"
        mock_job.company = "TechCorp"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_draft, mock_resume, mock_job]
        
        result = resume_service.get_adapted_resume_draft(1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['original_resume_filename'] == "test.tex"
        assert result['job_title'] == "Developer"
        assert result['status'] == "AI Generated"
    
    @patch('job_matching_app.services.resume_service.get_db_context')
    def test_update_adapted_resume_draft(self, mock_db_context, resume_service):
        """Test updating adapted resume draft"""
        mock_db = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        mock_draft = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_draft
        
        new_content = """\\documentclass{article}
\\begin{document}
Updated content
\\end{document}"""
        
        result = resume_service.update_adapted_resume_draft(1, new_content)
        
        assert result is True
        assert mock_draft.adapted_latex_content == new_content
        mock_draft.mark_as_edited.assert_called_once()
    
    def test_update_adapted_resume_draft_invalid_latex(self, resume_service):
        """Test updating with invalid LaTeX content"""
        invalid_latex = "This is not LaTeX"
        
        with pytest.raises(ValueError, match="Invalid LaTeX content"):
            resume_service.update_adapted_resume_draft(1, invalid_latex)


class TestAIMatchingServiceAdaptation:
    """Test AI matching service adaptation functionality"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI matching service instance"""
        with patch('job_matching_app.services.ai_matching_service.ollama') as mock_ollama:
            mock_ollama.list.return_value.models = [Mock(model='llama2')]
            service = AIMatchingService()
            service.client = mock_ollama
            return service
    
    def test_adapt_resume_content_english(self, ai_service):
        """Test resume adaptation for English content"""
        original_latex = """\\documentclass{article}
\\begin{document}
\\section{Experience}
Software Developer
\\end{document}"""
        
        job_data = {
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'description': 'Looking for Python developer with Django experience',
            'technologies': ['python', 'django'],
            'experience_level': 'senior'
        }
        
        adapted_latex = """\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Software Developer - Python, Django
\\end{document}"""
        
        mock_response = {'response': adapted_latex}
        ai_service.client.generate.return_value = mock_response
        
        result = ai_service.adapt_resume_content(original_latex, job_data)
        
        assert result == adapted_latex
        ai_service.client.generate.assert_called_once()
    
    def test_adapt_resume_content_portuguese(self, ai_service):
        """Test resume adaptation for Portuguese content"""
        original_latex = """\\documentclass{article}
\\begin{document}
\\section{Experiência}
Desenvolvedor de Software
\\end{document}"""
        
        job_data = {
            'title': 'Desenvolvedor Python Sênior',
            'company': 'TechCorp',
            'description': 'Procuramos desenvolvedor Python com experiência em Django',
            'technologies': ['python', 'django'],
            'experience_level': 'senior'
        }
        
        adapted_latex = """\\documentclass{article}
\\begin{document}
\\section{Experiência}
Desenvolvedor de Software Sênior - Python, Django
\\end{document}"""
        
        mock_response = {'response': adapted_latex}
        ai_service.client.generate.return_value = mock_response
        
        result = ai_service.adapt_resume_content(original_latex, job_data)
        
        assert result == adapted_latex
    
    def test_adapt_resume_content_ollama_unavailable(self, ai_service):
        """Test adaptation when Ollama is unavailable"""
        ai_service.client = None
        
        with pytest.raises(OllamaConnectionError, match="Ollama service is not available"):
            ai_service.adapt_resume_content("\\documentclass{article}", {})
    
    def test_clean_adapted_latex_response(self, ai_service):
        """Test cleaning AI response to extract LaTeX"""
        response_with_explanation = """Here's the adapted resume:

\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Developer
\\end{document}

I've made the following changes..."""
        
        result = ai_service._clean_adapted_latex_response(response_with_explanation)
        
        expected = """\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Developer
\\end{document}"""
        
        assert result == expected
    
    def test_clean_adapted_latex_response_code_block(self, ai_service):
        """Test cleaning AI response with code blocks"""
        response_with_code_block = """Here's the adapted LaTeX:

```latex
\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Developer
\\end{document}
```

The changes include..."""
        
        result = ai_service._clean_adapted_latex_response(response_with_code_block)
        
        expected = """\\documentclass{article}
\\begin{document}
\\section{Experience}
Senior Developer
\\end{document}"""
        
        assert result == expected
    
    def test_validate_latex_structure_valid(self, ai_service):
        """Test LaTeX structure validation with valid content"""
        valid_latex = """\\documentclass{article}
\\begin{document}
Content here
\\end{document}"""
        
        result = ai_service._validate_latex_structure(valid_latex)
        assert result is True
    
    def test_validate_latex_structure_invalid(self, ai_service):
        """Test LaTeX structure validation with invalid content"""
        invalid_latex = "Just some text without LaTeX structure"
        
        result = ai_service._validate_latex_structure(invalid_latex)
        assert result is False


class TestLaTeXEditorService:
    """Test LaTeX editor service functionality"""
    
    @pytest.fixture
    def editor_service(self):
        """Create LaTeX editor service instance"""
        return LaTeXEditorService()
    
    def test_validate_latex_content_valid(self, editor_service):
        """Test validation of valid LaTeX content"""
        valid_latex = """\\documentclass{article}
\\usepackage{geometry}
\\begin{document}
\\section{Test}
\\begin{itemize}
\\item First item
\\item Second item
\\end{itemize}
\\end{document}"""
        
        result = editor_service.validate_latex_content(valid_latex)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_latex_content_missing_documentclass(self, editor_service):
        """Test validation with missing documentclass"""
        invalid_latex = """\\begin{document}
Content
\\end{document}"""
        
        result = editor_service.validate_latex_content(invalid_latex)
        
        assert result.is_valid is False
        assert "Missing \\documentclass declaration" in result.errors
    
    def test_validate_latex_content_unbalanced_braces(self, editor_service):
        """Test validation with unbalanced braces"""
        invalid_latex = """\\documentclass{article}
\\begin{document}
\\section{Test
Content
\\end{document}"""
        
        result = editor_service.validate_latex_content(invalid_latex)
        
        assert result.is_valid is False
        assert "Unbalanced braces" in result.errors[0]
    
    def test_validate_latex_content_unbalanced_environment(self, editor_service):
        """Test validation with unbalanced environment"""
        invalid_latex = """\\documentclass{article}
\\begin{document}
\\begin{itemize}
\\item Test
\\end{document}"""
        
        result = editor_service.validate_latex_content(invalid_latex)
        
        assert result.is_valid is False
        assert "Unbalanced itemize environment" in result.errors[0]
    
    def test_validate_latex_content_item_outside_list(self, editor_service):
        """Test validation with item outside list environment"""
        invalid_latex = """\\documentclass{article}
\\begin{document}
\\item This is wrong
\\end{document}"""
        
        result = editor_service.validate_latex_content(invalid_latex)
        
        assert result.is_valid is False
        assert "\\item found outside of list environment" in result.errors
    
    @patch.object(ResumeService, 'update_adapted_resume_draft')
    def test_save_edited_resume_success(self, mock_update, editor_service):
        """Test successful saving of edited resume"""
        mock_update.return_value = True
        
        valid_latex = """\\documentclass{article}
\\begin{document}
\\section{Test}
Content
\\end{document}"""
        
        success, errors = editor_service.save_edited_resume(1, valid_latex)
        
        assert success is True
        assert len(errors) == 0
        mock_update.assert_called_once_with(1, valid_latex)
    
    @patch.object(ResumeService, 'update_adapted_resume_draft')
    def test_save_edited_resume_invalid_latex(self, mock_update, editor_service):
        """Test saving with invalid LaTeX content"""
        invalid_latex = "Not LaTeX content"
        
        success, errors = editor_service.save_edited_resume(1, invalid_latex)
        
        assert success is False
        assert len(errors) > 0
        assert "Missing \\documentclass declaration" in errors
        mock_update.assert_not_called()
    
    @patch.object(ResumeService, 'compile_to_pdf')
    def test_preview_latex_compilation_success(self, mock_compile, editor_service):
        """Test successful LaTeX compilation preview"""
        mock_compile.return_value = b"PDF content"
        
        latex_content = """\\documentclass{article}
\\begin{document}
Test
\\end{document}"""
        
        success, message = editor_service.preview_latex_compilation(latex_content)
        
        assert success is True
        assert "Compilation successful" in message
        assert "11 bytes" in message
    
    @patch.object(ResumeService, 'compile_to_pdf')
    def test_preview_latex_compilation_failure(self, mock_compile, editor_service):
        """Test failed LaTeX compilation preview"""
        mock_compile.side_effect = Exception("LaTeX error")
        
        latex_content = "Invalid LaTeX"
        
        success, message = editor_service.preview_latex_compilation(latex_content)
        
        assert success is False
        assert "LaTeX error" in message
    
    def test_get_latex_editing_suggestions(self, editor_service):
        """Test getting LaTeX editing suggestions"""
        latex_content = """\\documentclass{article}
\\usepackage{times}
\\begin{document}
\\\\\\\\
http://example.com
test@example.com
\\end{document}"""
        
        suggestions = editor_service.get_latex_editing_suggestions(latex_content)
        
        assert len(suggestions) > 0
        assert any("moderncv" in suggestion for suggestion in suggestions)
        assert any("hyperref" in suggestion for suggestion in suggestions)
        assert any("mailto:" in suggestion for suggestion in suggestions)
    
    def test_format_latex_content(self, editor_service):
        """Test LaTeX content formatting"""
        unformatted_latex = """\\documentclass{article}
\\begin{document}
\\section{Test}
\\begin{itemize}
\\item First
\\item Second
\\end{itemize}
\\end{document}"""
        
        formatted = editor_service.format_latex_content(unformatted_latex)
        
        lines = formatted.split('\n')
        # Check that itemize content is indented
        itemize_line_index = next(i for i, line in enumerate(lines) if '\\begin{itemize}' in line)
        item_line_index = next(i for i, line in enumerate(lines) if '\\item First' in line)
        
        assert lines[item_line_index].startswith('    ')  # Should be indented
    
    def test_get_latex_template_suggestions(self, editor_service):
        """Test getting LaTeX template suggestions"""
        suggestions = editor_service.get_latex_template_suggestions()
        
        assert len(suggestions) > 0
        assert all('name' in suggestion for suggestion in suggestions)
        assert all('description' in suggestion for suggestion in suggestions)
        assert all('package' in suggestion for suggestion in suggestions)
        assert all('example' in suggestion for suggestion in suggestions)
    
    @patch.object(ResumeService, 'compile_adapted_resume_to_pdf')
    def test_compile_and_save_pdf_success(self, mock_compile, editor_service):
        """Test successful PDF compilation and saving"""
        mock_compile.return_value = b"PDF content"
        
        success, message, pdf_content = editor_service.compile_and_save_pdf(1)
        
        assert success is True
        assert "compiled successfully" in message
        assert pdf_content == b"PDF content"
        mock_compile.assert_called_once_with(1, None)
    
    @patch.object(ResumeService, 'compile_adapted_resume_to_pdf')
    def test_compile_and_save_pdf_failure(self, mock_compile, editor_service):
        """Test failed PDF compilation"""
        mock_compile.side_effect = Exception("Compilation failed")
        
        success, message, pdf_content = editor_service.compile_and_save_pdf(1)
        
        assert success is False
        assert "Compilation failed" in message
        assert pdf_content is None


class TestResumeAdaptationIntegration:
    """Integration tests for resume adaptation workflow"""
    
    @pytest.fixture
    def services(self):
        """Create service instances"""
        return {
            'resume': ResumeService(),
            'editor': LaTeXEditorService()
        }
    
    def test_latex_validation_workflow(self, services):
        """Test LaTeX validation and editing workflow"""
        # Test valid LaTeX content
        valid_latex = """\\documentclass{article}
\\usepackage{geometry}
\\begin{document}
\\section{Experience}
\\begin{itemize}
\\item Software Developer at TechCorp
\\item Python, Django, PostgreSQL
\\end{itemize}
\\end{document}"""
        
        # Step 1: Validate content
        validation = services['editor'].validate_latex_content(valid_latex)
        assert validation.is_valid is True
        assert len(validation.errors) == 0
        
        # Step 2: Test formatting
        formatted = services['editor'].format_latex_content(valid_latex)
        assert formatted is not None
        assert len(formatted) > 0
        
        # Step 3: Test suggestions
        suggestions = services['editor'].get_latex_editing_suggestions(valid_latex)
        assert isinstance(suggestions, list)
        
        # Step 4: Test template suggestions
        templates = services['editor'].get_latex_template_suggestions()
        assert len(templates) > 0
        assert all('name' in template for template in templates)
    
    def test_invalid_latex_validation(self, services):
        """Test validation of invalid LaTeX content"""
        invalid_latex = """\\documentclass{article}
\\begin{document}
\\section{Test
\\begin{itemize}
\\item Unclosed item
\\end{document}"""
        
        validation = services['editor'].validate_latex_content(invalid_latex)
        assert validation.is_valid is False
        assert len(validation.errors) > 0
        assert "Unbalanced braces" in validation.errors[0]
        assert "Unbalanced itemize environment" in validation.errors[1]
    
    @patch.object(ResumeService, 'compile_to_pdf')
    def test_latex_compilation_preview(self, mock_compile, services):
        """Test LaTeX compilation preview"""
        mock_compile.return_value = b"PDF content"
        
        latex_content = """\\documentclass{article}
\\begin{document}
Test content
\\end{document}"""
        
        success, message = services['editor'].preview_latex_compilation(latex_content)
        assert success is True
        assert "Compilation successful" in message
        
        # Test compilation failure
        mock_compile.side_effect = Exception("LaTeX error")
        success, message = services['editor'].preview_latex_compilation(latex_content)
        assert success is False
        assert "LaTeX error" in message