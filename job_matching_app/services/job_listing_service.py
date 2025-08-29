"""
Job listing service for managing job data retrieval and display
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_

from ..database import get_db_context
from ..models.job_listing import JobListing, RemoteType, ExperienceLevel
from ..models.job_match import JobMatch
from ..config import get_settings


logger = logging.getLogger(__name__)


class JobListingService:
    """Service for managing job listings display and pagination"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def get_job_listings_paginated(
        self,
        page: int = 1,
        per_page: Optional[int] = None,
        sort_by: str = "scraped_at",
        sort_order: str = "desc",
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[JobListing], int, int]:
        """
        Get paginated job listings with optional filtering and sorting
        
        Args:
            page: Page number (1-based)
            per_page: Items per page (defaults to config setting)
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            filters: Optional filters dictionary
            
        Returns:
            Tuple of (job_listings, total_count, total_pages)
        """
        if per_page is None:
            per_page = self.settings.jobs_per_page
        
        with get_db_context() as session:
            query = session.query(JobListing)
            
            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply sorting
            query = self._apply_sorting(query, sort_by, sort_order)
            
            # Apply pagination
            offset = (page - 1) * per_page
            job_listings = query.offset(offset).limit(per_page).all()
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page
            
            return job_listings, total_count, total_pages
    
    def get_job_listings_with_matches(
        self,
        resume_id: int,
        page: int = 1,
        per_page: Optional[int] = None,
        sort_by: str = "compatibility_score",
        sort_order: str = "desc",
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Tuple[JobListing, Optional[JobMatch]]], int, int]:
        """
        Get paginated job listings with their match scores for a specific resume
        
        Args:
            resume_id: Resume ID to get matches for
            page: Page number (1-based)
            per_page: Items per page (defaults to config setting)
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            filters: Optional filters dictionary
            
        Returns:
            Tuple of (job_listings_with_matches, total_count, total_pages)
        """
        if per_page is None:
            per_page = self.settings.jobs_per_page
        
        with get_db_context() as session:
            # Join job listings with job matches
            query = session.query(JobListing, JobMatch).outerjoin(
                JobMatch,
                and_(
                    JobListing.id == JobMatch.job_listing_id,
                    JobMatch.resume_id == resume_id
                )
            )
            
            # Apply filters
            if filters:
                query = self._apply_filters_with_matches(query, filters)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply sorting (considering match scores)
            query = self._apply_sorting_with_matches(query, sort_by, sort_order)
            
            # Apply pagination
            offset = (page - 1) * per_page
            results = query.offset(offset).limit(per_page).all()
            
            # Convert to list of tuples
            job_listings_with_matches = [(job_listing, job_match) for job_listing, job_match in results]
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page
            
            return job_listings_with_matches, total_count, total_pages
    
    def get_job_by_id(self, job_id: int) -> Optional[JobListing]:
        """
        Get a specific job listing by ID
        
        Args:
            job_id: Job listing ID
            
        Returns:
            JobListing object or None if not found
        """
        with get_db_context() as session:
            return session.query(JobListing).filter(JobListing.id == job_id).first()
    
    def get_job_with_match(self, job_id: int, resume_id: int) -> Tuple[Optional[JobListing], Optional[JobMatch]]:
        """
        Get a job listing with its match score for a specific resume
        
        Args:
            job_id: Job listing ID
            resume_id: Resume ID
            
        Returns:
            Tuple of (JobListing, JobMatch) or (JobListing, None) if no match exists
        """
        with get_db_context() as session:
            result = session.query(JobListing, JobMatch).outerjoin(
                JobMatch,
                and_(
                    JobListing.id == JobMatch.job_listing_id,
                    JobMatch.resume_id == resume_id
                )
            ).filter(JobListing.id == job_id).first()
            
            if result:
                return result
            else:
                job_listing = session.query(JobListing).filter(JobListing.id == job_id).first()
                return job_listing, None
    
    def search_jobs(
        self,
        search_term: str,
        page: int = 1,
        per_page: Optional[int] = None,
        sort_by: str = "scraped_at",
        sort_order: str = "desc"
    ) -> Tuple[List[JobListing], int, int]:
        """
        Search job listings by title, company, or description
        
        Args:
            search_term: Search term to look for
            page: Page number (1-based)
            per_page: Items per page (defaults to config setting)
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Tuple of (job_listings, total_count, total_pages)
        """
        if per_page is None:
            per_page = self.settings.jobs_per_page
        
        search_pattern = f"%{search_term.lower()}%"
        
        with get_db_context() as session:
            query = session.query(JobListing).filter(
                or_(
                    func.lower(JobListing.title).like(search_pattern),
                    func.lower(JobListing.company).like(search_pattern),
                    func.lower(JobListing.description).like(search_pattern)
                )
            )
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply sorting
            query = self._apply_sorting(query, sort_by, sort_order)
            
            # Apply pagination
            offset = (page - 1) * per_page
            job_listings = query.offset(offset).limit(per_page).all()
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page
            
            return job_listings, total_count, total_pages
    
    def get_available_filters(self) -> Dict[str, List[str]]:
        """
        Get available filter options from existing job listings
        
        Returns:
            Dictionary with available filter values
        """
        with get_db_context() as session:
            # Get unique companies
            companies = session.query(JobListing.company).distinct().order_by(JobListing.company).all()
            companies = [company[0] for company in companies if company[0]]
            
            # Get unique locations
            locations = session.query(JobListing.location).distinct().order_by(JobListing.location).all()
            locations = [location[0] for location in locations if location[0]]
            
            # Get unique source sites
            source_sites = session.query(JobListing.source_site).distinct().order_by(JobListing.source_site).all()
            source_sites = [site[0] for site in source_sites if site[0]]
            
            # Get all technologies (flatten JSON arrays)
            tech_results = session.query(JobListing.technologies).filter(JobListing.technologies.isnot(None)).all()
            all_technologies = set()
            for tech_list in tech_results:
                if tech_list[0]:  # tech_list is a tuple
                    all_technologies.update(tech_list[0])
            technologies = sorted(list(all_technologies))
            
            return {
                'companies': companies[:50],  # Limit to top 50
                'locations': locations[:50],
                'source_sites': source_sites,
                'technologies': technologies[:100],  # Limit to top 100
                'remote_types': [rt.value for rt in RemoteType],
                'experience_levels': [el.value for el in ExperienceLevel]
            }
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to job listing query"""
        if 'company' in filters and filters['company']:
            query = query.filter(JobListing.company.ilike(f"%{filters['company']}%"))
        
        if 'location' in filters and filters['location']:
            query = query.filter(JobListing.location.ilike(f"%{filters['location']}%"))
        
        if 'remote_type' in filters and filters['remote_type']:
            if isinstance(filters['remote_type'], list):
                query = query.filter(JobListing.remote_type.in_(filters['remote_type']))
            else:
                query = query.filter(JobListing.remote_type == filters['remote_type'])
        
        if 'experience_level' in filters and filters['experience_level']:
            if isinstance(filters['experience_level'], list):
                query = query.filter(JobListing.experience_level.in_(filters['experience_level']))
            else:
                query = query.filter(JobListing.experience_level == filters['experience_level'])
        
        if 'source_site' in filters and filters['source_site']:
            if isinstance(filters['source_site'], list):
                query = query.filter(JobListing.source_site.in_(filters['source_site']))
            else:
                query = query.filter(JobListing.source_site == filters['source_site'])
        
        if 'technologies' in filters and filters['technologies']:
            # Filter jobs that contain any of the specified technologies
            tech_filters = []
            for tech in filters['technologies']:
                tech_filters.append(JobListing.technologies.contains([tech]))
            query = query.filter(or_(*tech_filters))
        
        if 'min_compatibility' in filters and filters['min_compatibility'] is not None:
            # This filter only works with the matches query
            pass
        
        return query
    
    def _apply_filters_with_matches(self, query, filters: Dict[str, Any]):
        """Apply filters to job listing query with matches"""
        # Apply regular filters to JobListing
        if 'company' in filters and filters['company']:
            query = query.filter(JobListing.company.ilike(f"%{filters['company']}%"))
        
        if 'location' in filters and filters['location']:
            query = query.filter(JobListing.location.ilike(f"%{filters['location']}%"))
        
        if 'remote_type' in filters and filters['remote_type']:
            if isinstance(filters['remote_type'], list):
                query = query.filter(JobListing.remote_type.in_(filters['remote_type']))
            else:
                query = query.filter(JobListing.remote_type == filters['remote_type'])
        
        if 'experience_level' in filters and filters['experience_level']:
            if isinstance(filters['experience_level'], list):
                query = query.filter(JobListing.experience_level.in_(filters['experience_level']))
            else:
                query = query.filter(JobListing.experience_level == filters['experience_level'])
        
        if 'source_site' in filters and filters['source_site']:
            if isinstance(filters['source_site'], list):
                query = query.filter(JobListing.source_site.in_(filters['source_site']))
            else:
                query = query.filter(JobListing.source_site == filters['source_site'])
        
        if 'technologies' in filters and filters['technologies']:
            tech_filters = []
            for tech in filters['technologies']:
                tech_filters.append(JobListing.technologies.contains([tech]))
            query = query.filter(or_(*tech_filters))
        
        # Apply match-specific filters
        if 'min_compatibility' in filters and filters['min_compatibility'] is not None:
            query = query.filter(
                or_(
                    JobMatch.compatibility_score >= filters['min_compatibility'],
                    JobMatch.compatibility_score.is_(None)  # Include jobs without matches
                )
            )
        
        return query
    
    def _apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to job listing query"""
        sort_column = getattr(JobListing, sort_by, JobListing.scraped_at)
        
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        return query
    
    def _apply_sorting_with_matches(self, query, sort_by: str, sort_order: str):
        """Apply sorting to job listing query with matches"""
        if sort_by == 'compatibility_score':
            # Sort by compatibility score, putting unmatched jobs at the end
            if sort_order.lower() == 'asc':
                query = query.order_by(asc(JobMatch.compatibility_score.nullslast()))
            else:
                query = query.order_by(desc(JobMatch.compatibility_score.nullslast()))
        else:
            # Sort by job listing fields
            sort_column = getattr(JobListing, sort_by, JobListing.scraped_at)
            if sort_order.lower() == 'asc':
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
        
        return query
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about job listings
        
        Returns:
            Dictionary with job listing statistics
        """
        with get_db_context() as session:
            total_jobs = session.query(JobListing).count()
            
            # Count by remote type
            remote_counts = session.query(
                JobListing.remote_type,
                func.count(JobListing.id)
            ).group_by(JobListing.remote_type).all()
            
            # Count by experience level
            experience_counts = session.query(
                JobListing.experience_level,
                func.count(JobListing.id)
            ).group_by(JobListing.experience_level).all()
            
            # Count by source site
            source_counts = session.query(
                JobListing.source_site,
                func.count(JobListing.id)
            ).group_by(JobListing.source_site).all()
            
            return {
                'total_jobs': total_jobs,
                'remote_type_distribution': {rt: count for rt, count in remote_counts if rt},
                'experience_level_distribution': {el: count for el, count in experience_counts if el},
                'source_site_distribution': {site: count for site, count in source_counts if site}
            }