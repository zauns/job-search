"""
Tests for ScrapingSession model and ScrapingSessionService
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from job_matching_app.database import Base
from job_matching_app.models import ScrapingSession, ScrapingStatus
from job_matching_app.services.scraping_session_service import ScrapingSessionService


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestScrapingSessionModel:
    """Test cases for ScrapingSession model"""
    
    def test_scraping_session_creation(self, db_session: Session):
        """Test creating a new scraping session"""
        keywords = ["python", "django"]
        location = "San Francisco"
        started_at = datetime.utcnow()
        
        session = ScrapingSession(
            keywords=keywords,
            location=location,
            started_at=started_at,
            status=ScrapingStatus.RUNNING
        )
        
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        assert session.id is not None
        assert session.keywords == keywords
        assert session.location == location
        assert session.started_at == started_at
        assert session.status == ScrapingStatus.RUNNING
        assert session.jobs_found == 0
        assert session.jobs_saved == 0
        assert session.errors == []
        assert session.completed_at is None
    
    def test_scraping_session_properties(self, db_session: Session):
        """Test ScrapingSession properties"""
        session = ScrapingSession(
            keywords=["python"],
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING
        )
        
        # Test is_active property
        assert session.is_active is True
        assert session.is_completed is False
        
        # Test after completion
        session.status = ScrapingStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        
        assert session.is_active is False
        assert session.is_completed is True
        
        # Test duration calculation
        session.started_at = datetime.utcnow() - timedelta(minutes=5)
        duration = session.duration_seconds
        assert duration is not None
        assert duration > 0
    
    def test_add_error(self, db_session: Session):
        """Test adding errors to a scraping session"""
        session = ScrapingSession(
            keywords=["python"],
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING
        )
        
        # Test adding error without details
        session.add_error("Connection timeout")
        assert len(session.errors) == 1
        assert session.errors[0]["message"] == "Connection timeout"
        assert "timestamp" in session.errors[0]
        assert session.has_errors is True
        
        # Test adding error with details
        error_details = {"site": "indeed.com", "status_code": 503}
        session.add_error("Site unavailable", error_details)
        assert len(session.errors) == 2
        assert session.errors[1]["message"] == "Site unavailable"
        assert session.errors[1]["details"] == error_details
    
    def test_mark_completed(self, db_session: Session):
        """Test marking session as completed"""
        session = ScrapingSession(
            keywords=["python"],
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING
        )
        
        session.mark_completed(jobs_found=50, jobs_saved=45)
        
        assert session.status == ScrapingStatus.COMPLETED
        assert session.completed_at is not None
        assert session.jobs_found == 50
        assert session.jobs_saved == 45
        assert session.is_completed is True
    
    def test_mark_failed(self, db_session: Session):
        """Test marking session as failed"""
        session = ScrapingSession(
            keywords=["python"],
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING
        )
        
        session.mark_failed("All sites failed")
        
        assert session.status == ScrapingStatus.FAILED
        assert session.completed_at is not None
        assert len(session.errors) == 1
        assert session.errors[0]["message"] == "All sites failed"
    
    def test_mark_cancelled(self, db_session: Session):
        """Test marking session as cancelled"""
        session = ScrapingSession(
            keywords=["python"],
            started_at=datetime.utcnow(),
            status=ScrapingStatus.RUNNING
        )
        
        session.mark_cancelled()
        
        assert session.status == ScrapingStatus.CANCELLED
        assert session.completed_at is not None


class TestScrapingSessionService:
    """Test cases for ScrapingSessionService"""
    
    def test_create_session(self, db_session: Session):
        """Test creating a new scraping session via service"""
        service = ScrapingSessionService(db_session)
        keywords = ["python", "django"]
        location = "New York"
        
        session = service.create_session(keywords, location)
        
        assert session.id is not None
        assert session.keywords == keywords
        assert session.location == location
        assert session.status == ScrapingStatus.RUNNING
        assert session.started_at is not None
    
    def test_get_session(self, db_session: Session):
        """Test retrieving a scraping session by ID"""
        service = ScrapingSessionService(db_session)
        
        # Create a session
        session = service.create_session(["python"])
        session_id = session.id
        
        # Retrieve it
        retrieved_session = service.get_session(session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.id == session_id
        assert retrieved_session.keywords == ["python"]
        
        # Test non-existent session
        non_existent = service.get_session(99999)
        assert non_existent is None
    
    def test_get_sessions_by_status(self, db_session: Session):
        """Test retrieving sessions by status"""
        service = ScrapingSessionService(db_session)
        
        # Create sessions with different statuses
        running_session = service.create_session(["python"])
        completed_session = service.create_session(["java"])
        service.complete_session(completed_session.id, 10, 8)
        
        # Test getting running sessions
        running_sessions = service.get_sessions_by_status(ScrapingStatus.RUNNING)
        assert len(running_sessions) >= 1
        assert any(s.id == running_session.id for s in running_sessions)
        
        # Test getting completed sessions
        completed_sessions = service.get_sessions_by_status(ScrapingStatus.COMPLETED)
        assert len(completed_sessions) >= 1
        assert any(s.id == completed_session.id for s in completed_sessions)
    
    def test_get_active_sessions(self, db_session: Session):
        """Test retrieving active sessions"""
        service = ScrapingSessionService(db_session)
        
        # Create an active session
        active_session = service.create_session(["python"])
        
        active_sessions = service.get_active_sessions()
        assert len(active_sessions) >= 1
        assert any(s.id == active_session.id for s in active_sessions)
        assert all(s.status == ScrapingStatus.RUNNING for s in active_sessions)
    
    def test_update_session_progress(self, db_session: Session):
        """Test updating session progress"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Update progress
        updated_session = service.update_session_progress(session_id, jobs_found=25, jobs_saved=20)
        
        assert updated_session is not None
        assert updated_session.jobs_found == 25
        assert updated_session.jobs_saved == 20
        
        # Test partial update
        service.update_session_progress(session_id, jobs_found=30)
        refreshed_session = service.get_session(session_id)
        assert refreshed_session.jobs_found == 30
        assert refreshed_session.jobs_saved == 20  # Should remain unchanged
    
    def test_add_session_error(self, db_session: Session):
        """Test adding errors to a session via service"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Add error
        error_details = {"site": "linkedin.com", "error_code": "RATE_LIMITED"}
        updated_session = service.add_session_error(
            session_id, 
            "Rate limited by site", 
            error_details
        )
        
        assert updated_session is not None
        assert len(updated_session.errors) == 1
        assert updated_session.errors[0]["message"] == "Rate limited by site"
        assert updated_session.errors[0]["details"] == error_details
    
    def test_complete_session(self, db_session: Session):
        """Test completing a session via service"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Complete the session
        completed_session = service.complete_session(session_id, 100, 95)
        
        assert completed_session is not None
        assert completed_session.status == ScrapingStatus.COMPLETED
        assert completed_session.jobs_found == 100
        assert completed_session.jobs_saved == 95
        assert completed_session.completed_at is not None
    
    def test_fail_session(self, db_session: Session):
        """Test failing a session via service"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Fail the session
        failed_session = service.fail_session(session_id, "Network error")
        
        assert failed_session is not None
        assert failed_session.status == ScrapingStatus.FAILED
        assert failed_session.completed_at is not None
        assert len(failed_session.errors) == 1
        assert failed_session.errors[0]["message"] == "Network error"
    
    def test_cancel_session(self, db_session: Session):
        """Test cancelling a session via service"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Cancel the session
        cancelled_session = service.cancel_session(session_id)
        
        assert cancelled_session is not None
        assert cancelled_session.status == ScrapingStatus.CANCELLED
        assert cancelled_session.completed_at is not None
    
    def test_delete_session(self, db_session: Session):
        """Test deleting a session via service"""
        service = ScrapingSessionService(db_session)
        
        session = service.create_session(["python"])
        session_id = session.id
        
        # Verify session exists
        assert service.get_session(session_id) is not None
        
        # Delete the session
        result = service.delete_session(session_id)
        assert result is True
        
        # Verify session is deleted
        assert service.get_session(session_id) is None
        
        # Test deleting non-existent session
        result = service.delete_session(99999)
        assert result is False
    
    def test_get_session_statistics(self, db_session: Session):
        """Test getting session statistics"""
        service = ScrapingSessionService(db_session)
        
        # Create sessions with different statuses
        running_session = service.create_session(["python"])
        completed_session1 = service.create_session(["java"])
        completed_session2 = service.create_session(["javascript"])
        failed_session = service.create_session(["ruby"])
        
        # Complete some sessions
        service.complete_session(completed_session1.id, 50, 45)
        service.complete_session(completed_session2.id, 30, 28)
        service.fail_session(failed_session.id, "Error")
        
        # Get statistics
        stats = service.get_session_statistics()
        
        assert stats["total_sessions"] >= 4
        assert stats["completed_sessions"] >= 2
        assert stats["failed_sessions"] >= 1
        assert stats["running_sessions"] >= 1
        assert stats["total_jobs_found"] >= 80  # 50 + 30
        assert stats["total_jobs_saved"] >= 73  # 45 + 28
        assert 0 <= stats["success_rate"] <= 100