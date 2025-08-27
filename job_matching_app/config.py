"""
Configuration settings for the Job Matching Application
"""
import os
from pathlib import Path

try:
    from pydantic import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback base class when pydantic is not available
    class BaseSettings:
        pass


class Settings(BaseSettings if PYDANTIC_AVAILABLE else object):
    """Application settings"""
    
    def __init__(self):
        # Database settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///job_matching.db")
        
        # Ollama settings
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        
        # Application directories
        self.app_dir = Path.home() / ".job_matching_app"
        self.resumes_dir = self.app_dir / "resumes"
        self.adapted_resumes_dir = self.app_dir / "adapted_resumes"
        self.logs_dir = self.app_dir / "logs"
        
        # Scraping settings
        self.scraping_delay = float(os.getenv("SCRAPING_DELAY", "1.0"))
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
        
        # Pagination
        self.jobs_per_page = int(os.getenv("JOBS_PER_PAGE", "30"))
        
        if PYDANTIC_AVAILABLE:
            super().__init__()
    
    if PYDANTIC_AVAILABLE:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()


def ensure_directories():
    """Ensure all required directories exist"""
    settings = get_settings()
    settings.app_dir.mkdir(exist_ok=True)
    settings.resumes_dir.mkdir(exist_ok=True)
    settings.adapted_resumes_dir.mkdir(exist_ok=True)
    settings.logs_dir.mkdir(exist_ok=True)