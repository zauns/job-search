"""
Job listing model for storing scraped job information
"""
from enum import Enum
from sqlalchemy import Column, String, Text, JSON, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel


class RemoteType(str, Enum):
    """Remote work type enumeration"""
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class ExperienceLevel(str, Enum):
    """Experience level enumeration"""
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


class JobListing(BaseModel):
    """Job listing model for storing scraped job information"""
    
    __tablename__ = "job_listings"
    
    # Basic job information
    title = Column(String(500), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    
    # Job characteristics
    remote_type = Column(SQLEnum(RemoteType), nullable=True, index=True)
    experience_level = Column(SQLEnum(ExperienceLevel), nullable=True, index=True)
    
    # Technologies and skills (stored as JSON array)
    technologies = Column(JSON, default=list, nullable=False)
    
    # Job description and details
    description = Column(Text, nullable=False)
    
    # Source information
    source_url = Column(String(1000), nullable=False)
    application_url = Column(String(1000), nullable=True)
    source_site = Column(String(100), nullable=False, index=True)  # indeed, linkedin, etc.
    
    # Scraping metadata
    scraped_at = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    job_matches = relationship("JobMatch", back_populates="job_listing", cascade="all, delete-orphan")
    adapted_drafts = relationship("AdaptedResumeDraft", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<JobListing(id={self.id}, title='{self.title}', company='{self.company}')>"
    
    @property
    def display_location(self):
        """Get formatted location for display"""
        if self.location and self.remote_type:
            if self.remote_type == RemoteType.REMOTE:
                return f"{self.location} (Remote)"
            elif self.remote_type == RemoteType.HYBRID:
                return f"{self.location} (Hybrid)"
            else:
                return self.location
        elif self.remote_type == RemoteType.REMOTE:
            return "Remote"
        elif self.location:
            return self.location
        else:
            return "Location not specified"
    
    @property
    def display_tags(self):
        """Get tags for display (remote type, experience level, top technologies)"""
        tags = []
        
        if self.remote_type:
            tags.append(self.remote_type.value.title())
        
        if self.experience_level:
            tags.append(self.experience_level.value.title())
        
        # Add top 3 technologies
        if self.technologies:
            tags.extend(self.technologies[:3])
        
        return tags