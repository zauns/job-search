"""
Unit tests for keyword management functionality
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from job_matching_app.services.resume_service import ResumeService
from job_matching_app.services.ai_matching_service import AIMatchingService, KeywordExtractionResult
from job_matching_app.models import Resume
from job_matching_app.database import get_db_context


class TestKeywordManagement:
    """Test cases for keyword management operations"""
    
    @pytest.fixture
    def sample_latex_content(self):
        """Sample LaTeX resume content for testing"""
        return """
\\documentclass{article}
\\begin{document}
\\section{Experience}
Software Engineer with experience in Python, Django, and React.
Worked on machine learning projects using TensorFlow and scikit-learn.
\\section{Skills}
Programming languages: Python, JavaScript, Java
Frameworks: Django, React, Node.js
Databases: PostgreSQL, MongoDB
\\end{document}
"""
    
    @pytest.fixture
    def resume_service(self):
        """Resume service instance for testing"""
        return ResumeService()
    
    @pytest.fixture
    def sample_resume(self, resume_service, sample_latex_content):
        """Create a sample resume for testing"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
            f.write(sample_latex_content)
            temp_file = f.name
        
        try:
            # Upload the resume
            resume = resume_service.upload_latex_resume(temp_file, "test_resume.tex")
            yield resume
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            # Clean up database
            with get_db_context() as db:
                db_resume = db.query(Resume).filter(Resume.id == resume.id).first()
                if db_resume:
                    db.delete(db_resume)
    
    def test_add_user_keyword_success(self, resume_service, sample_resume):
        """Test successfully adding a user keyword"""
        keyword = "docker"
        
        result = resume_service.add_user_keyword(sample_resume.id, keyword)
        
        assert result is True
        
        # Verify keyword was added
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert keyword in updated_resume.user_keywords
        assert keyword in updated_resume.all_keywords
    
    def test_add_user_keyword_duplicate(self, resume_service, sample_resume):
        """Test adding a duplicate user keyword"""
        keyword = "python"
        
        # Add keyword first time
        result1 = resume_service.add_user_keyword(sample_resume.id, keyword)
        assert result1 is True
        
        # Try to add same keyword again
        result2 = resume_service.add_user_keyword(sample_resume.id, keyword)
        assert result2 is False
        
        # Verify keyword appears only once
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        keyword_count = updated_resume.user_keywords.count(keyword)
        assert keyword_count == 1
    
    def test_add_user_keyword_case_insensitive(self, resume_service, sample_resume):
        """Test that keyword addition is case insensitive"""
        keyword_lower = "docker"
        keyword_upper = "DOCKER"
        
        # Add lowercase version
        result1 = resume_service.add_user_keyword(sample_resume.id, keyword_lower)
        assert result1 is True
        
        # Try to add uppercase version
        result2 = resume_service.add_user_keyword(sample_resume.id, keyword_upper)
        assert result2 is False
        
        # Verify only lowercase version exists
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert keyword_lower in updated_resume.user_keywords
        assert keyword_upper.lower() in updated_resume.user_keywords
    
    def test_add_user_keyword_whitespace_handling(self, resume_service, sample_resume):
        """Test that whitespace is properly handled in keywords"""
        keyword_with_spaces = "  machine learning  "
        expected_keyword = "machine learning"
        
        result = resume_service.add_user_keyword(sample_resume.id, keyword_with_spaces)
        assert result is True
        
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert expected_keyword in updated_resume.user_keywords
    
    def test_add_user_keyword_empty_string(self, resume_service, sample_resume):
        """Test adding empty or whitespace-only keyword"""
        empty_keywords = ["", "   ", "\t", "\n"]
        
        for keyword in empty_keywords:
            result = resume_service.add_user_keyword(sample_resume.id, keyword)
            assert result is False
        
        # Verify no empty keywords were added
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert len(updated_resume.user_keywords) == 0
    
    def test_add_user_keyword_nonexistent_resume(self, resume_service):
        """Test adding keyword to non-existent resume"""
        result = resume_service.add_user_keyword(99999, "test_keyword")
        assert result is False
    
    def test_remove_user_keyword_success(self, resume_service, sample_resume):
        """Test successfully removing a user keyword"""
        keyword = "docker"
        
        # Add keyword first
        resume_service.add_user_keyword(sample_resume.id, keyword)
        
        # Remove keyword
        result = resume_service.remove_user_keyword(sample_resume.id, keyword)
        assert result is True
        
        # Verify keyword was removed
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert keyword not in updated_resume.user_keywords
    
    def test_remove_user_keyword_not_found(self, resume_service, sample_resume):
        """Test removing a keyword that doesn't exist"""
        keyword = "nonexistent_keyword"
        
        result = resume_service.remove_user_keyword(sample_resume.id, keyword)
        assert result is False
    
    def test_remove_user_keyword_case_insensitive(self, resume_service, sample_resume):
        """Test that keyword removal is case insensitive"""
        keyword_lower = "docker"
        keyword_upper = "DOCKER"
        
        # Add lowercase keyword
        resume_service.add_user_keyword(sample_resume.id, keyword_lower)
        
        # Remove using uppercase
        result = resume_service.remove_user_keyword(sample_resume.id, keyword_upper)
        assert result is True
        
        # Verify keyword was removed
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert keyword_lower not in updated_resume.user_keywords
    
    def test_remove_user_keyword_nonexistent_resume(self, resume_service):
        """Test removing keyword from non-existent resume"""
        result = resume_service.remove_user_keyword(99999, "test_keyword")
        assert result is False
    
    def test_clear_user_keywords_success(self, resume_service, sample_resume):
        """Test successfully clearing all user keywords"""
        # Add multiple keywords
        keywords = ["docker", "kubernetes", "aws", "terraform"]
        for keyword in keywords:
            resume_service.add_user_keyword(sample_resume.id, keyword)
        
        # Verify keywords were added
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert len(updated_resume.user_keywords) == len(keywords)
        
        # Clear all keywords
        result = resume_service.clear_user_keywords(sample_resume.id)
        assert result is True
        
        # Verify all keywords were cleared
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert len(updated_resume.user_keywords) == 0
    
    def test_clear_user_keywords_empty_list(self, resume_service, sample_resume):
        """Test clearing keywords when list is already empty"""
        result = resume_service.clear_user_keywords(sample_resume.id)
        assert result is True
        
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert len(updated_resume.user_keywords) == 0
    
    def test_clear_user_keywords_nonexistent_resume(self, resume_service):
        """Test clearing keywords from non-existent resume"""
        result = resume_service.clear_user_keywords(99999)
        assert result is False
    
    def test_get_resume_keywords_success(self, resume_service, sample_resume):
        """Test getting all keywords for a resume"""
        # Add some user keywords
        user_keywords = ["docker", "kubernetes"]
        for keyword in user_keywords:
            resume_service.add_user_keyword(sample_resume.id, keyword)
        
        # Mock extracted keywords
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == sample_resume.id).first()
            resume.extracted_keywords = ["python", "django", "react"]
        
        # Get keywords
        keywords_dict = resume_service.get_resume_keywords(sample_resume.id)
        
        assert "extracted_keywords" in keywords_dict
        assert "user_keywords" in keywords_dict
        assert "all_keywords" in keywords_dict
        
        assert "python" in keywords_dict["extracted_keywords"]
        assert "docker" in keywords_dict["user_keywords"]
        assert len(keywords_dict["all_keywords"]) == 5  # 3 extracted + 2 user
    
    def test_get_resume_keywords_nonexistent_resume(self, resume_service):
        """Test getting keywords for non-existent resume"""
        keywords_dict = resume_service.get_resume_keywords(99999)
        assert keywords_dict == {}
    
    @patch.object(AIMatchingService, 'extract_resume_keywords')
    def test_extract_keywords_with_ai_success(self, mock_extract, resume_service, sample_resume):
        """Test AI keyword extraction success"""
        # Mock AI service response
        mock_result = KeywordExtractionResult(
            keywords=["python", "django", "react", "postgresql"],
            confidence=0.85,
            language_detected="en"
        )
        mock_extract.return_value = mock_result
        
        # Extract keywords
        result = resume_service.extract_keywords_with_ai(sample_resume.id)
        
        assert result.keywords == mock_result.keywords
        assert result.confidence == mock_result.confidence
        assert result.language_detected == mock_result.language_detected
        
        # Verify keywords were saved to database
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        assert updated_resume.extracted_keywords == mock_result.keywords
    
    @patch.object(AIMatchingService, 'extract_resume_keywords')
    def test_extract_keywords_with_ai_fallback(self, mock_extract, resume_service, sample_resume):
        """Test AI keyword extraction with fallback"""
        # Mock AI service response with fallback
        mock_result = KeywordExtractionResult(
            keywords=["python", "programming", "software"],
            confidence=0.5,
            language_detected="en"
        )
        mock_extract.return_value = mock_result
        
        # Extract keywords
        result = resume_service.extract_keywords_with_ai(sample_resume.id)
        
        assert result.confidence == 0.5
        assert len(result.keywords) > 0
    
    def test_extract_keywords_with_ai_nonexistent_resume(self, resume_service):
        """Test AI keyword extraction for non-existent resume"""
        with pytest.raises(ValueError, match="Resume with ID 99999 not found"):
            resume_service.extract_keywords_with_ai(99999)
    
    def test_keyword_persistence_across_sessions(self, resume_service, sample_resume):
        """Test that keywords persist across different service instances"""
        keyword = "persistent_keyword"
        
        # Add keyword with first service instance
        resume_service.add_user_keyword(sample_resume.id, keyword)
        
        # Create new service instance and verify keyword exists
        new_service = ResumeService()
        updated_resume = new_service.get_resume_by_id(sample_resume.id)
        assert keyword in updated_resume.user_keywords
    
    def test_keyword_uniqueness_across_types(self, resume_service, sample_resume):
        """Test that keywords are unique across extracted and user keywords"""
        # Set extracted keywords
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == sample_resume.id).first()
            resume.extracted_keywords = ["python", "django"]
        
        # Try to add extracted keyword as user keyword
        result = resume_service.add_user_keyword(sample_resume.id, "python")
        assert result is False
        
        # Add unique user keyword
        result = resume_service.add_user_keyword(sample_resume.id, "docker")
        assert result is True
        
        # Verify all_keywords contains unique items
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        all_keywords = updated_resume.all_keywords
        assert len(all_keywords) == len(set(all_keywords))  # No duplicates
        assert "python" in all_keywords
        assert "django" in all_keywords
        assert "docker" in all_keywords
    
    def test_multiple_keyword_operations(self, resume_service, sample_resume):
        """Test multiple keyword operations in sequence"""
        keywords_to_add = ["docker", "kubernetes", "aws", "terraform", "jenkins"]
        
        # Add multiple keywords
        for keyword in keywords_to_add:
            result = resume_service.add_user_keyword(sample_resume.id, keyword)
            assert result is True
        
        # Verify all were added
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        for keyword in keywords_to_add:
            assert keyword in updated_resume.user_keywords
        
        # Remove some keywords
        keywords_to_remove = ["docker", "jenkins"]
        for keyword in keywords_to_remove:
            result = resume_service.remove_user_keyword(sample_resume.id, keyword)
            assert result is True
        
        # Verify removal
        updated_resume = resume_service.get_resume_by_id(sample_resume.id)
        for keyword in keywords_to_remove:
            assert keyword not in updated_resume.user_keywords
        
        # Verify remaining keywords
        remaining_keywords = ["kubernetes", "aws", "terraform"]
        for keyword in remaining_keywords:
            assert keyword in updated_resume.user_keywords
        
        assert len(updated_resume.user_keywords) == len(remaining_keywords)