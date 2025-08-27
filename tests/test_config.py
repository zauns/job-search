"""
Tests for configuration module
"""
import pytest
from pathlib import Path
from job_matching_app.config import get_settings, ensure_directories


def test_get_settings():
    """Test getting application settings"""
    settings = get_settings()
    
    assert settings.database_url == "sqlite:///job_matching.db"
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.jobs_per_page == 30
    assert isinstance(settings.app_dir, Path)


def test_ensure_directories():
    """Test directory creation"""
    # This should not raise any exceptions
    ensure_directories()
    
    settings = get_settings()
    assert settings.app_dir.exists()
    assert settings.resumes_dir.exists()
    assert settings.adapted_resumes_dir.exists()
    assert settings.logs_dir.exists()