"""
Service for managing scraping sessions
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from job_matching_app.database import get_db
from job_matching_app.models import ScrapingSession, ScrapingStatus


class ScrapingSessionService:
    """Service for managing scraping sessions with CRUD operations"""
    
    def __init__(self, db: Session = None):
        self.db = db or next(get_db())
    
    def create_session(self, keywords: List[str], location: str = None) -> ScrapingSession:
        """Create a new scraping session"""
        session = ScrapingSession(
            keywords=keywords,
            location=location,
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING,
            jobs_found=0,
            jobs_saved=0,
            errors=[]
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_session(self, session_id: int) -> Optional[ScrapingSession]:
        """Get a scraping session by ID"""
        return self.db.query(ScrapingSession).filter(ScrapingSession.id == session_id).first()
    
    def get_all_sessions(self, limit: int = 100, offset: int = 0) -> List[ScrapingSession]:
        """Get all scraping sessions with pagination"""
        return (self.db.query(ScrapingSession)
                .order_by(desc(ScrapingSession.created_at))
                .limit(limit)
                .offset(offset)
                .all())
    
    def get_sessions_by_status(self, status: ScrapingStatus, limit: int = 100) -> List[ScrapingSession]:
        """Get scraping sessions by status"""
        return (self.db.query(ScrapingSession)
                .filter(ScrapingSession.status == status)
                .order_by(desc(ScrapingSession.created_at))
                .limit(limit)
                .all())
    
    def get_active_sessions(self) -> List[ScrapingSession]:
        """Get all currently active (running) scraping sessions"""
        return self.get_sessions_by_status(ScrapingStatus.RUNNING)
    
    def get_recent_sessions(self, days: int = 7, limit: int = 50) -> List[ScrapingSession]:
        """Get recent scraping sessions within the specified number of days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (self.db.query(ScrapingSession)
                .filter(ScrapingSession.created_at >= cutoff_date)
                .order_by(desc(ScrapingSession.created_at))
                .limit(limit)
                .all())
    
    def update_session_progress(self, session_id: int, jobs_found: int = None, jobs_saved: int = None) -> Optional[ScrapingSession]:
        """Update the progress of a scraping session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        if jobs_found is not None:
            session.jobs_found = jobs_found
        if jobs_saved is not None:
            session.jobs_saved = jobs_saved
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def add_session_error(self, session_id: int, error_message: str, error_details: Dict[str, Any] = None) -> Optional[ScrapingSession]:
        """Add an error to a scraping session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.add_error(error_message, error_details)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def complete_session(self, session_id: int, jobs_found: int = None, jobs_saved: int = None) -> Optional[ScrapingSession]:
        """Mark a scraping session as completed"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.mark_completed(jobs_found, jobs_saved)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def fail_session(self, session_id: int, error_message: str = None) -> Optional[ScrapingSession]:
        """Mark a scraping session as failed"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.mark_failed(error_message)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def cancel_session(self, session_id: int) -> Optional[ScrapingSession]:
        """Mark a scraping session as cancelled"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.mark_cancelled()
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def delete_session(self, session_id: int) -> bool:
        """Delete a scraping session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        self.db.delete(session)
        self.db.commit()
        
        return True
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete scraping sessions older than the specified number of days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = (self.db.query(ScrapingSession)
                        .filter(ScrapingSession.created_at < cutoff_date)
                        .delete())
        
        self.db.commit()
        return deleted_count
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics about scraping sessions"""
        total_sessions = self.db.query(ScrapingSession).count()
        
        completed_sessions = self.db.query(ScrapingSession).filter(
            ScrapingSession.status == ScrapingStatus.COMPLETED
        ).count()
        
        failed_sessions = self.db.query(ScrapingSession).filter(
            ScrapingSession.status == ScrapingStatus.FAILED
        ).count()
        
        running_sessions = self.db.query(ScrapingSession).filter(
            ScrapingSession.status == ScrapingStatus.RUNNING
        ).count()
        
        # Get total jobs found and saved
        result = self.db.query(
            func.sum(ScrapingSession.jobs_found).label('total_found'),
            func.sum(ScrapingSession.jobs_saved).label('total_saved')
        ).filter(
            ScrapingSession.status == ScrapingStatus.COMPLETED
        ).first()
        
        total_jobs_found = result.total_found or 0
        total_jobs_saved = result.total_saved or 0
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'failed_sessions': failed_sessions,
            'running_sessions': running_sessions,
            'total_jobs_found': total_jobs_found,
            'total_jobs_saved': total_jobs_saved,
            'success_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        }