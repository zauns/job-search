"""
Tests for ResumeService
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_matching_app.services.resume_service import ResumeService, LaTeXCompilationError
from job_matching_app.models import Resume
from job_matching_app.database import Base


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def resume_service():
    """Create ResumeService instance"""
    return ResumeService()


@pytest.fixture
def valid_latex_content():
    """Valid LaTeX content for testing"""
    return r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\title{Test Resume}
\author{John Doe}
\date{\today}

\begin{document}
\maketitle

\section{Experience}
Software Developer at Tech Company

\section{Skills}
Python, JavaScript, SQL

\end{document}
"""


@pytest.fixture
def invalid_latex_content():
    """Invalid LaTeX content for testing"""
    return "This is not LaTeX content"


@pytest.fixture
def temp_latex_file(valid_latex_content):
    """Create temporary LaTeX file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as f:
        f.write(valid_latex_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestResumeService:
    """Test cases for ResumeService"""
    pass


class TestLaTeXValidation:
    """Test LaTeX validation functionality"""
    
    def test_validate_valid_latex(self, resume_service, valid_latex_content):
        """Test validation of valid LaTeX content"""
        assert resume_service.validate_latex(valid_latex_content)
    
    def test_validate_invalid_latex(self, resume_service, invalid_latex_content):
        """Test validation of invalid LaTeX content"""
        assert not resume_service.validate_latex(invalid_latex_content)
    
    def test_validate_empty_content(self, resume_service):
        """Test validation of empty content"""
        assert not resume_service.validate_latex("")
        assert not resume_service.validate_latex(None)


class TestResumeUpload:
    """Test resume upload functionality"""
    
    def test_upload_valid_resume(self, resume_service, temp_latex_file, db_session):
        """Test uploading a valid LaTeX resume"""
        resume = resume_service.upload_latex_resume(temp_latex_file)
        
        assert isinstance(resume, Resume)
        assert resume.filename.endswith('.tex')
        assert resume.latex_content is not None
        assert len(resume.latex_content) > 0
    
    def test_upload_nonexistent_file(self, resume_service):
        """Test uploading a non-existent file"""
        with pytest.raises(FileNotFoundError):
            resume_service.upload_latex_resume("/nonexistent/file.tex")
    
    def test_upload_invalid_latex_file(self, resume_service, invalid_latex_content):
        """Test uploading a file with invalid LaTeX content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as f:
            f.write(invalid_latex_content)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid LaTeX content"):
                resume_service.upload_latex_resume(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_upload_with_custom_filename(self, resume_service, temp_latex_file, db_session):
        """Test uploading with custom filename"""
        custom_name = "my_custom_resume.tex"
        resume = resume_service.upload_latex_resume(temp_latex_file, custom_name)
        
        assert resume.filename == custom_name


class TestLaTeXCompilation:
    """Test LaTeX compilation functionality"""
    
    @patch('job_matching_app.services.resume_service.ResumeService._find_pdflatex')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_compile_to_pdf_success(self, mock_rmtree, mock_makedirs, mock_open, mock_exists, mock_run, mock_find_pdflatex, resume_service, valid_latex_content):
        """Test successful PDF compilation"""
        # Mock pdflatex found
        mock_find_pdflatex.return_value = 'pdflatex'
        
        # Mock successful pdflatex execution
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Mock PDF file creation and reading
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = b"PDF content"
        
        pdf_content = resume_service.compile_to_pdf(valid_latex_content)
        
        assert isinstance(pdf_content, bytes)
        assert pdf_content == b"PDF content"
    
    @patch('job_matching_app.services.resume_service.ResumeService._find_pdflatex')
    @patch('subprocess.run')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_compile_to_pdf_failure(self, mock_rmtree, mock_makedirs, mock_open, mock_run, mock_find_pdflatex, resume_service, valid_latex_content):
        """Test PDF compilation failure"""
        # Mock pdflatex found
        mock_find_pdflatex.return_value = 'pdflatex'
        
        # Mock file operations
        mock_open.return_value.__enter__.return_value.write.return_value = None
        
        # Mock failed pdflatex execution
        mock_run.return_value = MagicMock(returncode=1, stdout="LaTeX Error", stderr="LaTeX Error")
        
        with pytest.raises(LaTeXCompilationError, match="LaTeX compilation failed"):
            resume_service.compile_to_pdf(valid_latex_content)
        
        mock_find_pdflatex.assert_called_once()
    
    @patch('job_matching_app.services.resume_service.ResumeService._find_pdflatex')
    def test_compile_pdflatex_not_found(self, mock_find_pdflatex, resume_service, valid_latex_content):
        """Test compilation when pdflatex is not installed"""
        # Mock pdflatex not found
        mock_find_pdflatex.return_value = None
        
        with pytest.raises(LaTeXCompilationError, match="pdflatex not found"):
            resume_service.compile_to_pdf(valid_latex_content)
    
    @patch('job_matching_app.services.resume_service.ResumeService._find_pdflatex')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    def test_compile_pdf_not_created(self, mock_rmtree, mock_makedirs, mock_open, mock_exists, mock_run, mock_find_pdflatex, resume_service, valid_latex_content):
        """Test compilation when PDF file is not created"""
        # Mock pdflatex found
        mock_find_pdflatex.return_value = 'pdflatex'
        
        # Mock file operations
        mock_open.return_value.__enter__.return_value.write.return_value = None
        
        # Mock successful pdflatex execution but PDF file not created
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = False
        
        with pytest.raises(LaTeXCompilationError, match="PDF file was not created"):
            resume_service.compile_to_pdf(valid_latex_content)
        
        mock_find_pdflatex.assert_called_once()


class TestResumeManagement:
    """Test resume management functionality"""
    
    def test_get_resume_by_id(self, resume_service, temp_latex_file, db_session):
        """Test getting resume by ID"""
        # Upload a resume first
        uploaded_resume = resume_service.upload_latex_resume(temp_latex_file)
        
        # Get it back by ID
        retrieved_resume = resume_service.get_resume_by_id(uploaded_resume.id)
        
        assert retrieved_resume is not None
        assert retrieved_resume.id == uploaded_resume.id
        assert retrieved_resume.filename == uploaded_resume.filename
    
    def test_get_nonexistent_resume(self, resume_service):
        """Test getting non-existent resume"""
        resume = resume_service.get_resume_by_id(99999)
        assert resume is None
    
    def test_get_all_resumes(self, resume_service, temp_latex_file, db_session):
        """Test getting all resumes"""
        # Upload multiple resumes
        resume1 = resume_service.upload_latex_resume(temp_latex_file, "resume1.tex")
        resume2 = resume_service.upload_latex_resume(temp_latex_file, "resume2.tex")
        
        all_resumes = resume_service.get_all_resumes()
        
        assert len(all_resumes) >= 2
        resume_ids = [r.id for r in all_resumes]
        assert resume1.id in resume_ids
        assert resume2.id in resume_ids
    
    def test_update_resume_keywords(self, resume_service, temp_latex_file, db_session):
        """Test updating resume keywords"""
        resume = resume_service.upload_latex_resume(temp_latex_file)
        
        extracted_keywords = ["python", "javascript", "sql"]
        user_keywords = ["machine learning", "data science"]
        
        success = resume_service.update_resume_keywords(
            resume.id, extracted_keywords, user_keywords
        )
        
        assert success
        
        # Verify keywords were updated
        updated_resume = resume_service.get_resume_by_id(resume.id)
        assert updated_resume.extracted_keywords == extracted_keywords
        assert updated_resume.user_keywords == user_keywords
    
    def test_update_nonexistent_resume_keywords(self, resume_service):
        """Test updating keywords for non-existent resume"""
        success = resume_service.update_resume_keywords(99999, [], [])
        assert not success
    
    def test_delete_resume(self, resume_service, temp_latex_file, db_session):
        """Test deleting a resume"""
        resume = resume_service.upload_latex_resume(temp_latex_file)
        resume_id = resume.id
        
        success = resume_service.delete_resume(resume_id)
        assert success
        
        # Verify resume was deleted
        deleted_resume = resume_service.get_resume_by_id(resume_id)
        assert deleted_resume is None
    
    def test_delete_nonexistent_resume(self, resume_service):
        """Test deleting non-existent resume"""
        success = resume_service.delete_resume(99999)
        assert not success


class TestLaTeXInstallationCheck:
    """Test LaTeX installation checking"""
    
    @patch('subprocess.run')
    def test_latex_installed(self, mock_run, resume_service):
        """Test when LaTeX is properly installed"""
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="pdfTeX 3.14159265-2.6-1.40.21 (TeX Live 2020)"
        )
        
        is_installed, version_info = resume_service.check_latex_installation()
        
        assert is_installed
        assert "pdfTeX" in version_info
    
    @patch('subprocess.run')
    def test_latex_not_installed(self, mock_run, resume_service):
        """Test when LaTeX is not installed"""
        mock_run.side_effect = FileNotFoundError()
        
        is_installed, version_info = resume_service.check_latex_installation()
        
        assert not is_installed
        assert "not found" in version_info
    
    @patch('subprocess.run')
    def test_latex_command_failed(self, mock_run, resume_service):
        """Test when LaTeX command fails"""
        mock_run.return_value = MagicMock(returncode=1)
        
        is_installed, version_info = resume_service.check_latex_installation()
        
        assert not is_installed
        assert "pdflatex not found" in version_info