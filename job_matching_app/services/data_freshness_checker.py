"""
Data freshness detection service for job listings
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.job_listing import JobListing
from ..database import get_db_context
from ..config import get_settings


class DataFreshnessChecker:
    """Service for checking if job data is stale and needs refreshing"""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the data freshness checker
        
        Args:
            db_session: Optional database session. If not provided, will create its own.
        """
        self.db_session = db_session
        self.settings = get_settings()
    
    def is_data_stale(self, threshold_hours: Optional[int] = None) -> bool:
        """
        Check if job data is older than the specified threshold
        
        Args:
            threshold_hours: Hours threshold for considering data stale.
                           If None, uses configuration default.
        
        Returns:
            True if data is stale or no data exists, False otherwise
        """
        if threshold_hours is None:
            threshold_hours = getattr(self.settings, 'job_data_freshness_hours', 24)
        
        last_scrape_time = self.get_last_scrape_time()
        
        if last_scrape_time is None:
            # No data exists, consider it stale
            return True
        
        threshold_time = datetime.utcnow() - timedelta(hours=threshold_hours)
        return last_scrape_time < threshold_time
    
    def get_last_scrape_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the most recent scraping operation
        
        Returns:
            DateTime of the most recent scrape, or None if no data exists
        """
        if self.db_session:
            return self._get_last_scrape_time_with_session(self.db_session)
        else:
            with get_db_context() as db:
                return self._get_last_scrape_time_with_session(db)
    
    def _get_last_scrape_time_with_session(self, db: Session) -> Optional[datetime]:
        """
        Get the last scrape time using the provided database session
        
        Args:
            db: Database session
            
        Returns:
            DateTime of the most recent scrape, or None if no data exists
        """
        result = db.query(func.max(JobListing.scraped_at)).scalar()
        return result
    
    def should_auto_scrape(self, 
                          job_count_threshold: Optional[int] = None,
                          threshold_hours: Optional[int] = None) -> bool:
        """
        Determine if automatic scraping should be triggered based on data freshness
        and job count
        
        Args:
            job_count_threshold: Minimum number of jobs before considering auto-scrape.
                               If None, uses configuration default.
            threshold_hours: Hours threshold for considering data stale.
                           If None, uses configuration default.
        
        Returns:
            True if auto-scraping should be triggered, False otherwise
        """
        if job_count_threshold is None:
            job_count_threshold = getattr(self.settings, 'min_jobs_before_scrape', 10)
        
        # Check if data is stale
        if self.is_data_stale(threshold_hours):
            return True
        
        # Check if we have enough jobs
        job_count = self.get_total_job_count()
        if job_count < job_count_threshold:
            return True
        
        return False
    
    def get_total_job_count(self) -> int:
        """
        Get the total number of jobs in the database
        
        Returns:
            Total count of job listings
        """
        if self.db_session:
            return self._get_total_job_count_with_session(self.db_session)
        else:
            with get_db_context() as db:
                return self._get_total_job_count_with_session(db)
    
    def _get_total_job_count_with_session(self, db: Session) -> int:
        """
        Get the total job count using the provided database session
        
        Args:
            db: Database session
            
        Returns:
            Total count of job listings
        """
        return db.query(JobListing).count()
    
    def get_data_freshness_status(self, threshold_hours: Optional[int] = None) -> dict:
        """
        Get comprehensive data freshness status information
        
        Args:
            threshold_hours: Hours threshold for considering data stale.
                           If None, uses configuration default.
        
        Returns:
            Dictionary containing freshness status information
        """
        if threshold_hours is None:
            threshold_hours = getattr(self.settings, 'job_data_freshness_hours', 24)
        
        last_scrape_time = self.get_last_scrape_time()
        total_jobs = self.get_total_job_count()
        is_stale = self.is_data_stale(threshold_hours)
        should_scrape = self.should_auto_scrape(threshold_hours=threshold_hours)
        
        status = {
            'last_scrape_time': last_scrape_time,
            'total_jobs': total_jobs,
            'is_stale': is_stale,
            'should_auto_scrape': should_scrape,
            'threshold_hours': threshold_hours,
            'has_data': last_scrape_time is not None
        }
        
        if last_scrape_time:
            age_hours = (datetime.utcnow() - last_scrape_time).total_seconds() / 3600
            status['data_age_hours'] = round(age_hours, 2)
        else:
            status['data_age_hours'] = None
        
        return status