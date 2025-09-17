"""
Scraping session model for tracking scraping operations
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, JSON, DateTime, Integer, Enum as SQLEnum
from .base import BaseModel


class ScrapingStatus(str, Enum):
    """Scraping session status enumeration"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapingSession(BaseModel):
    """Model for tracking scraping sessions and their progress"""
    
    __tablename__ = "scraping_sessions"
    
    # Scraping parameters
    keywords = Column(JSON, nullable=False)  # List of keywords used for scraping
    location = Column(String(255), nullable=True)  # Location filter for scraping
    
    # Session timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Results tracking
    jobs_found = Column(Integer, default=0, nullable=False)  # Total jobs found during scraping
    jobs_saved = Column(Integer, default=0, nullable=False)  # Jobs actually saved (after deduplication)
    
    # Error tracking
    errors = Column(JSON, default=list, nullable=False)  # List of error messages/details
    
    # Session status
    status = Column(SQLEnum(ScrapingStatus), default=ScrapingStatus.RUNNING, nullable=False, index=True)
    
    def __repr__(self):
        return f"<ScrapingSession(id={self.id}, status='{self.status}', keywords={self.keywords})>"
    
    @property
    def duration_seconds(self):
        """Get the duration of the scraping session in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_active(self):
        """Check if the scraping session is currently active"""
        return self.status == ScrapingStatus.RUNNING
    
    @property
    def is_completed(self):
        """Check if the scraping session completed successfully"""
        return self.status == ScrapingStatus.COMPLETED
    
    @property
    def has_errors(self):
        """Check if the scraping session encountered any errors"""
        return bool(self.errors)
    
    def add_error(self, error_message: str, error_details: dict = None):
        """Add an error to the session"""
        error_entry = {
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        if error_details:
            error_entry["details"] = error_details
        
        current_errors = self.errors or []
        self.errors = current_errors + [error_entry]
    
    def mark_completed(self, jobs_found: int = None, jobs_saved: int = None):
        """Mark the session as completed"""
        self.status = ScrapingStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if jobs_found is not None:
            self.jobs_found = jobs_found
        if jobs_saved is not None:
            self.jobs_saved = jobs_saved
    
    def mark_failed(self, error_message: str = None):
        """Mark the session as failed"""
        self.status = ScrapingStatus.FAILED
        self.completed_at = datetime.utcnow()
        if error_message:
            self.add_error(error_message)
    
    def mark_cancelled(self):
        """Mark the session as cancelled"""
        self.status = ScrapingStatus.CANCELLED
        self.completed_at = datetime.utcnow()