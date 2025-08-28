"""
Job match model for storing compatibility scores and matching results
"""
from sqlalchemy import Column, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class JobMatch(BaseModel):
    """Model for storing job matching results and compatibility scores"""
    
    __tablename__ = "job_matches"
    
    # Foreign keys
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False, index=True)
    job_listing_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False, index=True)
    
    # Matching results
    compatibility_score = Column(Float, nullable=False, index=True)
    matching_keywords = Column(JSON, default=list, nullable=False)
    missing_keywords = Column(JSON, default=list, nullable=False)
    
    # Additional matching metadata
    algorithm_version = Column(Integer, default=1, nullable=False)
    
    # Relationships
    resume = relationship("Resume", back_populates="job_matches")
    job_listing = relationship("JobListing", back_populates="job_matches")
    
    def __repr__(self):
        return f"<JobMatch(id={self.id}, score={self.compatibility_score:.2f}, resume_id={self.resume_id}, job_id={self.job_listing_id})>"
    
    @property
    def compatibility_percentage(self):
        """Get compatibility score as percentage"""
        return round(self.compatibility_score * 100, 1)
    
    @property
    def match_quality(self):
        """Get qualitative match assessment"""
        if self.compatibility_score >= 0.8:
            return "Excellent"
        elif self.compatibility_score >= 0.6:
            return "Good"
        elif self.compatibility_score >= 0.4:
            return "Fair"
        else:
            return "Poor"
    
    @property
    def keyword_match_ratio(self):
        """Get ratio of matching keywords to total keywords"""
        total_keywords = len(self.matching_keywords) + len(self.missing_keywords)
        if total_keywords == 0:
            return 0.0
        return len(self.matching_keywords) / total_keywords