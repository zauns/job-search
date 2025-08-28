"""
Tests for model validators
"""
import pytest
from job_matching_app.models.validators import (
    validate_latex_content,
    validate_url,
    validate_keywords,
    validate_compatibility_score,
    sanitize_filename,
    extract_technologies_from_text
)


class TestValidateLatexContent:
    """Test LaTeX content validation"""
    
    def test_valid_latex_content(self):
        """Test valid LaTeX content"""
        content = r"""
        \documentclass{article}
        \begin{document}
        This is a test document.
        \end{document}
        """
        assert validate_latex_content(content)
    
    def test_invalid_latex_content_missing_documentclass(self):
        """Test invalid LaTeX content missing documentclass"""
        content = r"""
        \begin{document}
        This is a test document.
        \end{document}
        """
        assert not validate_latex_content(content)
    
    def test_invalid_latex_content_missing_begin_document(self):
        """Test invalid LaTeX content missing begin document"""
        content = r"""
        \documentclass{article}
        This is a test document.
        \end{document}
        """
        assert not validate_latex_content(content)
    
    def test_invalid_latex_content_empty(self):
        """Test invalid empty LaTeX content"""
        assert not validate_latex_content("")
        assert not validate_latex_content(None)


class TestValidateUrl:
    """Test URL validation"""
    
    def test_valid_urls(self):
        """Test valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com:8080",
            "https://subdomain.example.com",
            "http://localhost:3000",
            "https://192.168.1.1:8080"
        ]
        
        for url in valid_urls:
            assert validate_url(url), f"URL should be valid: {url}"
    
    def test_invalid_urls(self):
        """Test invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Not http/https
            "",
            None,
            "https://",
            "example.com"  # Missing protocol
        ]
        
        for url in invalid_urls:
            assert not validate_url(url), f"URL should be invalid: {url}"


class TestValidateKeywords:
    """Test keywords validation"""
    
    def test_valid_keywords(self):
        """Test valid keywords list"""
        keywords = ["python", "django", "postgresql", "machine learning"]
        assert validate_keywords(keywords)
    
    def test_empty_keywords_list(self):
        """Test empty keywords list is valid"""
        assert validate_keywords([])
    
    def test_invalid_keywords_not_list(self):
        """Test invalid keywords that are not a list"""
        assert not validate_keywords("not a list")
        assert not validate_keywords(None)
        assert not validate_keywords(123)
    
    def test_invalid_keywords_empty_strings(self):
        """Test invalid keywords with empty strings"""
        assert not validate_keywords(["python", "", "django"])
        assert not validate_keywords(["python", "   ", "django"])
    
    def test_invalid_keywords_non_strings(self):
        """Test invalid keywords with non-string items"""
        assert not validate_keywords(["python", 123, "django"])
        assert not validate_keywords(["python", None, "django"])


class TestValidateCompatibilityScore:
    """Test compatibility score validation"""
    
    def test_valid_scores(self):
        """Test valid compatibility scores"""
        valid_scores = [0.0, 0.5, 1.0, 0.75, 0.123]
        
        for score in valid_scores:
            assert validate_compatibility_score(score), f"Score should be valid: {score}"
    
    def test_valid_integer_scores(self):
        """Test valid integer scores"""
        assert validate_compatibility_score(0)
        assert validate_compatibility_score(1)
    
    def test_invalid_scores_out_of_range(self):
        """Test invalid scores out of range"""
        invalid_scores = [-0.1, 1.1, -1, 2, 100]
        
        for score in invalid_scores:
            assert not validate_compatibility_score(score), f"Score should be invalid: {score}"
    
    def test_invalid_scores_wrong_type(self):
        """Test invalid scores of wrong type"""
        invalid_scores = ["0.5", None, "high", [0.5]]
        
        for score in invalid_scores:
            assert not validate_compatibility_score(score), f"Score should be invalid: {score}"


class TestSanitizeFilename:
    """Test filename sanitization"""
    
    def test_safe_filename(self):
        """Test already safe filename"""
        filename = "resume.tex"
        assert sanitize_filename(filename) == filename
    
    def test_unsafe_characters(self):
        """Test filename with unsafe characters"""
        filename = "my<resume>file.tex"
        sanitized = sanitize_filename(filename)
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert sanitized == "my_resume_file.tex"
    
    def test_empty_filename(self):
        """Test empty filename"""
        assert sanitize_filename("") == "untitled"
        assert sanitize_filename(None) == "untitled"
    
    def test_long_filename(self):
        """Test very long filename gets truncated"""
        long_name = "a" * 300 + ".tex"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".tex")
    
    def test_filename_with_path_separators(self):
        """Test filename with path separators"""
        filename = "folder/subfolder\\resume.tex"
        sanitized = sanitize_filename(filename)
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert sanitized == "folder_subfolder_resume.tex"


class TestExtractTechnologiesFromText:
    """Test technology extraction from text"""
    
    def test_extract_common_technologies(self):
        """Test extracting common technologies"""
        text = "We are looking for a Python developer with Django and PostgreSQL experience."
        technologies = extract_technologies_from_text(text)
        
        assert "python" in technologies
        assert "django" in technologies
        assert "postgresql" in technologies
    
    def test_extract_case_insensitive(self):
        """Test case-insensitive extraction"""
        text = "Experience with PYTHON, Django, and PostgreSQL required."
        technologies = extract_technologies_from_text(text)
        
        assert "python" in technologies
        assert "django" in technologies
        assert "postgresql" in technologies
    
    def test_extract_max_technologies(self):
        """Test maximum technologies limit"""
        text = "Python Java JavaScript TypeScript C++ C# PHP Ruby Go Rust React Angular Vue Django Flask"
        technologies = extract_technologies_from_text(text, max_technologies=5)
        
        assert len(technologies) <= 5
    
    def test_extract_from_empty_text(self):
        """Test extraction from empty text"""
        assert extract_technologies_from_text("") == []
        assert extract_technologies_from_text(None) == []
    
    def test_extract_no_technologies(self):
        """Test extraction when no technologies are found"""
        text = "We are looking for a great team player with excellent communication skills."
        technologies = extract_technologies_from_text(text)
        
        assert technologies == []
    
    def test_extract_compound_technologies(self):
        """Test extraction of compound technology names"""
        text = "Experience with machine learning and data science is preferred."
        technologies = extract_technologies_from_text(text)
        
        assert "machine learning" in technologies
        assert "data science" in technologies