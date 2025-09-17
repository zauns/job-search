"""
Scraping integration manager for coordinated scraping operations
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session

from .job_scraping_service import JobScrapingService, JobScrapingError, RateLimitError, SiteUnavailableError
from .data_freshness_checker import DataFreshnessChecker
from .scraping_session_service import ScrapingSessionService
from ..models.scraping_session import ScrapingSession, ScrapingStatus
from ..models.job_listing import JobListing
from ..database import get_db_context
from ..config import get_settings


class ScrapingIntegrationManager:
    """Manager for coordinated scraping operations with progress tracking and error handling"""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the scraping integration manager
        
        Args:
            db_session: Optional database session. If not provided, will create its own.
        """
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Initialize services
        self.scraping_service = JobScrapingService()
        self.freshness_checker = DataFreshnessChecker(db_session)
    
    def auto_scrape_if_needed(self, 
                             keywords: Optional[List[str]] = None, 
                             location: str = "",
                             force_scrape: bool = False,
                             progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Automatically trigger scraping based on data freshness and configuration
        
        Args:
            keywords: List of keywords to search for. If None, uses default from config.
            location: Location to search in
            force_scrape: If True, skip freshness check and scrape anyway
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing scraping results and status
        """
        if keywords is None:
            keywords = getattr(self.settings, 'default_scraping_keywords', ['python', 'software engineer'])
        
        self.logger.info(f"Checking if auto-scraping is needed for keywords: {keywords}")
        
        # Check if scraping is needed
        if not force_scrape and not self.freshness_checker.should_auto_scrape():
            freshness_status = self.freshness_checker.get_data_freshness_status()
            self.logger.info("Data is fresh, skipping auto-scrape")
            return {
                'scraping_triggered': False,
                'reason': 'Data is fresh',
                'freshness_status': freshness_status,
                'jobs_found': 0,
                'jobs_saved': 0,
                'errors': []
            }
        
        # Trigger scraping
        self.logger.info("Data is stale or insufficient, triggering auto-scrape")
        return self.scrape_with_progress(
            keywords=keywords,
            location=location,
            max_pages=getattr(self.settings, 'max_scraping_pages', 3),
            progress_callback=progress_callback
        )
    
    def scrape_with_progress(self, 
                           keywords: List[str], 
                           location: str = "",
                           max_pages: int = 3,
                           progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Scrape with progress callbacks for UI feedback
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in
            max_pages: Maximum number of pages to scrape per site
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing scraping results and status
        """
        scraping_session = None
        all_jobs = []
        errors = []
        
        try:
            # Create scraping session for tracking
            session_service = ScrapingSessionService(self.db_session) if self.db_session else None
            if session_service:
                scraping_session = session_service.create_session(keywords, location)
            else:
                with get_db_context() as db:
                    session_service = ScrapingSessionService(db)
                    scraping_session = session_service.create_session(keywords, location)
            
            self.logger.info(f"Started scraping session {scraping_session.id}")
            
            # Notify progress start
            if progress_callback:
                progress_callback("started", {
                    'session_id': scraping_session.id,
                    'keywords': keywords,
                    'location': location,
                    'max_pages': max_pages
                })
            
            # Scrape Indeed
            try:
                if progress_callback:
                    progress_callback("scraping_site", {'site': 'Indeed', 'status': 'starting'})
                
                indeed_jobs = self.scraping_service.scrape_indeed(keywords, location, max_pages)
                all_jobs.extend(indeed_jobs)
                
                self.logger.info(f"Successfully scraped {len(indeed_jobs)} jobs from Indeed")
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'Indeed', 
                        'status': 'completed',
                        'jobs_found': len(indeed_jobs)
                    })
                
            except RateLimitError as e:
                error_msg = f"Rate limit exceeded for Indeed: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'Indeed', 'type': 'rate_limit'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'Indeed', 
                        'status': 'rate_limited',
                        'error': error_msg
                    })
                
            except SiteUnavailableError as e:
                error_msg = f"Indeed unavailable: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'Indeed', 'type': 'site_unavailable'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'Indeed', 
                        'status': 'failed',
                        'error': error_msg
                    })
            
            except Exception as e:
                error_msg = f"Unexpected error scraping Indeed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'Indeed', 'type': 'unexpected'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'Indeed', 
                        'status': 'failed',
                        'error': error_msg
                    })
            
            # Scrape LinkedIn
            try:
                if progress_callback:
                    progress_callback("scraping_site", {'site': 'LinkedIn', 'status': 'starting'})
                
                linkedin_jobs = self.scraping_service.scrape_linkedin(keywords, location, max_pages)
                all_jobs.extend(linkedin_jobs)
                
                self.logger.info(f"Successfully scraped {len(linkedin_jobs)} jobs from LinkedIn")
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'LinkedIn', 
                        'status': 'completed',
                        'jobs_found': len(linkedin_jobs)
                    })
                
            except RateLimitError as e:
                error_msg = f"Rate limit exceeded for LinkedIn: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'LinkedIn', 'type': 'rate_limit'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'LinkedIn', 
                        'status': 'rate_limited',
                        'error': error_msg
                    })
                
            except SiteUnavailableError as e:
                error_msg = f"LinkedIn unavailable: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'LinkedIn', 'type': 'site_unavailable'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'LinkedIn', 
                        'status': 'failed',
                        'error': error_msg
                    })
            
            except Exception as e:
                error_msg = f"Unexpected error scraping LinkedIn: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                
                if scraping_session and session_service:
                    session_service.add_session_error(scraping_session.id, error_msg, {'site': 'LinkedIn', 'type': 'unexpected'})
                
                if progress_callback:
                    progress_callback("scraping_site", {
                        'site': 'LinkedIn', 
                        'status': 'failed',
                        'error': error_msg
                    })
            
            # Save jobs to database
            if progress_callback:
                progress_callback("saving", {'status': 'starting', 'total_jobs': len(all_jobs)})
            
            jobs_saved = self.scraping_service.save_jobs_to_database(all_jobs)
            
            if progress_callback:
                progress_callback("saving", {
                    'status': 'completed', 
                    'jobs_saved': jobs_saved,
                    'total_jobs': len(all_jobs)
                })
            
            # Update scraping session
            if scraping_session and session_service:
                session_service.complete_session(scraping_session.id, len(all_jobs), jobs_saved)
            
            # Final progress callback
            if progress_callback:
                progress_callback("completed", {
                    'session_id': scraping_session.id if scraping_session else None,
                    'total_jobs_found': len(all_jobs),
                    'jobs_saved': jobs_saved,
                    'errors': errors
                })
            
            self.logger.info(f"Scraping completed: {len(all_jobs)} jobs found, {jobs_saved} saved")
            
            return {
                'scraping_triggered': True,
                'session_id': scraping_session.id if scraping_session else None,
                'jobs_found': len(all_jobs),
                'jobs_saved': jobs_saved,
                'errors': errors,
                'success': len(all_jobs) > 0 or len(errors) == 0
            }
            
        except Exception as e:
            error_msg = f"Critical error during scraping: {str(e)}"
            self.logger.error(error_msg)
            
            # Mark session as failed
            if scraping_session and session_service:
                session_service.fail_session(scraping_session.id, error_msg)
            
            if progress_callback:
                progress_callback("failed", {
                    'session_id': scraping_session.id if scraping_session else None,
                    'error': error_msg
                })
            
            return {
                'scraping_triggered': True,
                'session_id': scraping_session.id if scraping_session else None,
                'jobs_found': len(all_jobs),
                'jobs_saved': 0,
                'errors': errors + [error_msg],
                'success': False
            }
    
    def handle_scraping_errors(self, errors: List[str]) -> Dict[str, Any]:
        """
        Centralized error handling for scraping failures
        
        Args:
            errors: List of error messages
            
        Returns:
            Dictionary containing error analysis and recommendations
        """
        if not errors:
            return {'has_errors': False, 'recommendations': []}
        
        error_analysis = {
            'has_errors': True,
            'total_errors': len(errors),
            'error_types': {},
            'recommendations': []
        }
        
        # Analyze error types
        rate_limit_errors = [e for e in errors if 'rate limit' in e.lower()]
        site_unavailable_errors = [e for e in errors if 'unavailable' in e.lower() and 'rate limit' not in e.lower()]
        network_errors = [e for e in errors if any(term in e.lower() for term in ['network', 'connection', 'timeout']) and 'unavailable' not in e.lower() and 'rate limit' not in e.lower()]
        
        error_analysis['error_types'] = {
            'rate_limit': len(rate_limit_errors),
            'site_unavailable': len(site_unavailable_errors),
            'network': len(network_errors),
            'other': len(errors) - len(rate_limit_errors) - len(site_unavailable_errors) - len(network_errors)
        }
        
        # Generate recommendations
        if rate_limit_errors:
            error_analysis['recommendations'].append(
                "Rate limiting detected. Consider increasing delays between requests or trying again later."
            )
        
        if site_unavailable_errors:
            error_analysis['recommendations'].append(
                "Some job sites are currently unavailable. This may be temporary - try again later."
            )
        
        if network_errors:
            error_analysis['recommendations'].append(
                "Network connectivity issues detected. Check your internet connection and try again."
            )
        
        if len(errors) == error_analysis['error_types']['rate_limit'] + error_analysis['error_types']['site_unavailable']:
            error_analysis['recommendations'].append(
                "All errors appear to be temporary. The scraping service itself is working correctly."
            )
        
        return error_analysis
    
    def get_scraping_status(self) -> Dict[str, Any]:
        """
        Get current scraping status and statistics
        
        Returns:
            Dictionary containing scraping status information
        """
        freshness_status = self.freshness_checker.get_data_freshness_status()
        
        # Get session statistics
        session_stats = {}
        active_session_count = 0
        active_session_ids = []
        
        if self.db_session:
            session_service = ScrapingSessionService(self.db_session)
            session_stats = session_service.get_session_statistics()
            active_sessions = session_service.get_active_sessions()
            active_session_count = len(active_sessions)
            active_session_ids = [s.id for s in active_sessions]
        else:
            with get_db_context() as db:
                session_service = ScrapingSessionService(db)
                session_stats = session_service.get_session_statistics()
                active_sessions = session_service.get_active_sessions()
                active_session_count = len(active_sessions)
                active_session_ids = [s.id for s in active_sessions]
        
        return {
            'data_freshness': freshness_status,
            'session_statistics': session_stats,
            'active_sessions': active_session_count,
            'active_session_ids': active_session_ids,
            'scraping_available': True,
            'auto_scrape_enabled': getattr(self.settings, 'auto_scrape_enabled', True)
        }
    
    def cancel_active_sessions(self) -> int:
        """
        Cancel all active scraping sessions
        
        Returns:
            Number of sessions cancelled
        """
        cancelled_count = 0
        
        if self.db_session:
            session_service = ScrapingSessionService(self.db_session)
            active_sessions = session_service.get_active_sessions()
            
            for session in active_sessions:
                try:
                    session_service.cancel_session(session.id)
                    cancelled_count += 1
                    self.logger.info(f"Cancelled scraping session {session.id}")
                except Exception as e:
                    self.logger.error(f"Error cancelling session {session.id}: {e}")
        else:
            with get_db_context() as db:
                session_service = ScrapingSessionService(db)
                active_sessions = session_service.get_active_sessions()
                
                for session in active_sessions:
                    try:
                        session_service.cancel_session(session.id)
                        cancelled_count += 1
                        self.logger.info(f"Cancelled scraping session {session.id}")
                    except Exception as e:
                        self.logger.error(f"Error cancelling session {session.id}: {e}")
        
        return cancelled_count