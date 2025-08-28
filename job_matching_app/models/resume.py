"""
Resume-related database models
"""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Resume(BaseModel):
    """Resume model for storing LaTeX resumes"""
    
    __tablename__ = "resumes"
    
    # Basic resume information
    filename = Column(String(255), nullable=False)
    latex_content = Column(Text, nullable=False)
    
    # Keywords extracted by AI and user-modified keywords
    extracted_keywords = Column(JSON, default=list, nullable=False)
    user_keywords = Column(JSON, default=list, nullable=False)
    
    # Relationships
    adapted_drafts = relationship("AdaptedResumeDraft", back_populates="original_resume", cascade="all, delete-orphan")
    job_matches = relationship("JobMatch", back_populates="resume", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Resume(id={self.id}, filename='{self.filename}')>"
    
    @property
    def all_keywords(self):
        """Get all keywords (extracted + user-defined)"""
        return list(set(self.extracted_keywords + self.user_keywords))
    
    def add_user_keyword(self, keyword: str):
        """Add a user-defined keyword"""
        if keyword not in self.user_keywords:
            self.user_keywords = self.user_keywords + [keyword]
    
    def remove_user_keyword(self, keyword: str):
        """Remove a user-defined keyword"""
        if keyword in self.user_keywords:
            keywords = self.user_keywords.copy()
            keywords.remove(keyword)
            self.user_keywords = keywords


class AdaptedResumeDraft(BaseModel):
    """Model for storing adapted resume drafts for specific jobs"""
    __tablename__ = "adapted_resume_drafts"
    
    original_resume_id = Column(ForeignKey("resumes.id"), nullable=False)
    job_id = Column(ForeignKey("job_listings.id"), nullable=False)
    adapted_latex_content = Column(Text, nullable=False)
    is_user_edited = Column(Boolean, default=False)
    
    # Relationships
    original_resume = relationship("Resume", back_populates="adapted_drafts")
    job = relationship("JobListing", back_populates="adapted_drafts")
    
    def __repr__(self):
        return f"<AdaptedResumeDraft(id={self.id}, resume_id={self.original_resume_id}, job_id={self.job_id})>"
    
    def mark_as_edited(self):
        """Mark this draft as user-edited"""
        self.is_user_edited = True
    
    @property
    def status(self):
        """Get the status of this draft"""
        return "User Modified" if self.is_user_edited else "AI Generated"