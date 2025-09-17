"""
Job scraping service for collecting job listings from multiple sources
"""
import time
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, quote_plus
from enum import Enum

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models.job_listing import JobListing, RemoteType, ExperienceLevel
from ..database import get_db_context


class ScrapingErrorType(Enum):
    """Types of scraping errors for better categorization"""
    RATE_LIMIT = "rate_limit"
    SITE_UNAVAILABLE = "site_unavailable"
    NETWORK_ERROR = "network_error"
    PARSING_ERROR = "parsing_error"
    AUTHENTICATION_ERROR = "authentication_error"
    BLOCKED_ERROR = "blocked_error"
    TIMEOUT_ERROR = "timeout_error"


class JobScrapingError(Exception):
    """Base exception for job scraping errors"""
    def __init__(self, message: str, error_type: ScrapingErrorType = None, site: str = None, retry_after: int = None):
        super().__init__(message)
        self.error_type = error_type
        self.site = site
        self.retry_after = retry_after
        self.user_message = self._generate_user_message()
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message"""
        if self.error_type == ScrapingErrorType.RATE_LIMIT:
            return f"Rate limit exceeded for {self.site or 'job site'}. Please try again in {self.retry_after or 60} seconds."
        elif self.error_type == ScrapingErrorType.SITE_UNAVAILABLE:
            return f"{self.site or 'Job site'} is currently unavailable. Please try again later."
        elif self.error_type == ScrapingErrorType.NETWORK_ERROR:
            return "Network connection issues detected. Please check your internet connection and try again."
        elif self.error_type == ScrapingErrorType.BLOCKED_ERROR:
            return f"Access to {self.site or 'job site'} has been temporarily blocked. This may be due to too many requests."
        elif self.error_type == ScrapingErrorType.TIMEOUT_ERROR:
            return f"Request to {self.site or 'job site'} timed out. The site may be experiencing high traffic."
        elif self.error_type == ScrapingErrorType.AUTHENTICATION_ERROR:
            return f"Authentication required for {self.site or 'job site'}. Some features may be limited."
        else:
            return f"An error occurred while scraping job listings: {str(self)}"


class RateLimitError(JobScrapingError):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str, site: str = None, retry_after: int = None):
        super().__init__(message, ScrapingErrorType.RATE_LIMIT, site, retry_after)


class SiteUnavailableError(JobScrapingError):
    """Exception raised when a job site is unavailable"""
    def __init__(self, message: str, site: str = None):
        super().__init__(message, ScrapingErrorType.SITE_UNAVAILABLE, site)


class NetworkError(JobScrapingError):
    """Exception raised for network-related errors"""
    def __init__(self, message: str, site: str = None):
        super().__init__(message, ScrapingErrorType.NETWORK_ERROR, site)


class BlockedError(JobScrapingError):
    """Exception raised when access is blocked"""
    def __init__(self, message: str, site: str = None):
        super().__init__(message, ScrapingErrorType.BLOCKED_ERROR, site)


class TimeoutError(JobScrapingError):
    """Exception raised for timeout errors"""
    def __init__(self, message: str, site: str = None):
        super().__init__(message, ScrapingErrorType.TIMEOUT_ERROR, site)


class ScrapingResult:
    """Container for scraping results with error information"""
    def __init__(self):
        self.jobs: List[JobListing] = []
        self.errors: List[JobScrapingError] = []
        self.site_results: Dict[str, Tuple[List[JobListing], Optional[JobScrapingError]]] = {}
        self.total_jobs_found = 0
        self.total_jobs_saved = 0
        self.successful_sites: List[str] = []
        self.failed_sites: List[str] = []
    
    def add_site_result(self, site: str, jobs: List[JobListing], error: Optional[JobScrapingError] = None):
        """Add results for a specific site"""
        self.site_results[site] = (jobs, error)
        if error:
            self.errors.append(error)
            self.failed_sites.append(site)
        else:
            self.successful_sites.append(site)
        self.jobs.extend(jobs)
        self.total_jobs_found += len(jobs)
    
    def has_errors(self) -> bool:
        """Check if any errors occurred"""
        return len(self.errors) > 0
    
    def has_jobs(self) -> bool:
        """Check if any jobs were found"""
        return len(self.jobs) > 0
    
    def get_summary(self) -> str:
        """Get a summary of scraping results"""
        summary_parts = []
        
        if self.has_jobs():
            summary_parts.append(f"Found {self.total_jobs_found} jobs")
            if self.total_jobs_saved > 0:
                summary_parts.append(f"saved {self.total_jobs_saved} new jobs")
        
        if self.successful_sites:
            summary_parts.append(f"successful sites: {', '.join(self.successful_sites)}")
        
        if self.failed_sites:
            summary_parts.append(f"failed sites: {', '.join(self.failed_sites)}")
        
        return "; ".join(summary_parts) if summary_parts else "No results"


class JobScrapingService:
    """Service for scraping job listings from multiple sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1  # Base delay in seconds
        self.max_delay = 300  # Maximum delay in seconds (5 minutes)
        self.backoff_factor = 2  # Exponential backoff multiplier
        
        # Site-specific configurations
        self.site_configs = {
            'indeed': {
                'base_delay': 2,
                'max_pages_per_request': 5,
                'timeout': 30,
                'user_agent_rotation': True
            },
            'linkedin': {
                'base_delay': 3,
                'max_pages_per_request': 3,
                'timeout': 45,
                'user_agent_rotation': True
            }
        }
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and rate limiting"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers to avoid bot detection
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def _calculate_retry_delay(self, attempt: int, base_delay: int = None) -> int:
        """Calculate delay for retry with exponential backoff and jitter"""
        if base_delay is None:
            base_delay = self.base_delay
        
        # Exponential backoff: base_delay * (backoff_factor ^ attempt)
        delay = base_delay * (self.backoff_factor ** attempt)
        
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.1, 0.3) * delay
        delay += jitter
        
        # Cap at maximum delay
        return min(int(delay), self.max_delay)
    
    def _handle_request_error(self, error: Exception, site: str, url: str) -> JobScrapingError:
        """Convert request errors to appropriate JobScrapingError types"""
        error_str = str(error).lower()
        
        if isinstance(error, requests.exceptions.Timeout):
            self.logger.warning(f"Timeout error for {site}: {error}")
            return TimeoutError(f"Request timeout for {site}", site)
        
        elif isinstance(error, requests.exceptions.ConnectionError):
            self.logger.warning(f"Connection error for {site}: {error}")
            return NetworkError(f"Connection failed for {site}", site)
        
        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, 'status_code', None) if hasattr(error, 'response') else None
            
            if status_code == 429 or '429' in error_str or 'rate limit' in error_str:
                # Extract retry-after header if available
                retry_after = None
                if hasattr(error, 'response') and error.response:
                    retry_after = error.response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except ValueError:
                            retry_after = 60  # Default to 1 minute
                
                self.logger.warning(f"Rate limit error for {site}: {error}")
                return RateLimitError(f"Rate limit exceeded for {site}", site, retry_after or 60)
            
            elif status_code in [403, 401]:
                self.logger.warning(f"Authentication/authorization error for {site}: {error}")
                return BlockedError(f"Access denied for {site} (status: {status_code})", site)
            
            elif status_code in [503, 502, 500]:
                self.logger.warning(f"Server error for {site}: {error}")
                return SiteUnavailableError(f"{site} server error (status: {status_code})", site)
            
            else:
                self.logger.error(f"HTTP error for {site}: {error}")
                return JobScrapingError(f"HTTP error for {site}: {error}", site=site)
        
        else:
            self.logger.error(f"Unexpected error for {site}: {error}")
            return JobScrapingError(f"Unexpected error for {site}: {error}", site=site)
    
    def _make_request_with_retry(self, url: str, site: str, max_retries: int = None) -> requests.Response:
        """Make HTTP request with retry logic and exponential backoff"""
        if max_retries is None:
            max_retries = self.max_retries
        
        site_config = self.site_configs.get(site, {})
        timeout = site_config.get('timeout', 30)
        base_delay = site_config.get('base_delay', self.base_delay)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"Attempting request to {site} (attempt {attempt + 1}/{max_retries + 1}): {url}")
                
                # Rotate user agent if configured
                if site_config.get('user_agent_rotation', False) and attempt > 0:
                    self._rotate_user_agent()
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                # Log successful request
                self.logger.debug(f"Successful request to {site} after {attempt + 1} attempts")
                return response
                
            except Exception as e:
                last_error = self._handle_request_error(e, site, url)
                
                # Don't retry for certain error types
                if isinstance(last_error, (BlockedError, TimeoutError)) and attempt < max_retries:
                    # For blocked/timeout errors, wait longer before retry
                    delay = self._calculate_retry_delay(attempt + 1, base_delay * 2)
                elif isinstance(last_error, RateLimitError):
                    # For rate limits, use the retry-after value if available
                    delay = last_error.retry_after or self._calculate_retry_delay(attempt + 1, base_delay)
                elif isinstance(last_error, NetworkError) and attempt < max_retries:
                    # For network errors, use standard backoff
                    delay = self._calculate_retry_delay(attempt, base_delay)
                else:
                    # For other errors or final attempt, don't retry
                    if attempt == max_retries:
                        break
                    delay = self._calculate_retry_delay(attempt, base_delay)
                
                if attempt < max_retries:
                    self.logger.info(f"Request failed for {site}, retrying in {delay} seconds: {last_error.user_message}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed for {site}: {last_error.user_message}")
        
        # If we get here, all retries failed
        raise last_error
    
    def _rotate_user_agent(self):
        """Rotate user agent to avoid detection"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents)
        })

    def scrape_indeed(self, keywords: List[str], location: str = "", max_pages: int = 5) -> List[JobListing]:
        """
        Scrape job listings from Indeed
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of JobListing objects
        """
        site = 'indeed'
        jobs = []
        query = " ".join(keywords)
        
        self.logger.info(f"Starting Indeed scraping for keywords: {keywords}, location: {location}, max_pages: {max_pages}")
        
        try:
            for page in range(max_pages):
                start = page * 10  # Indeed shows 10 jobs per page
                url = self._build_indeed_url(query, location, start)
                
                self.logger.info(f"Scraping Indeed page {page + 1}/{max_pages}")
                
                try:
                    # Use retry logic for the request
                    response = self._make_request_with_retry(url, site)
                    
                    # Add delay between pages to be respectful
                    site_config = self.site_configs.get(site, {})
                    delay = site_config.get('base_delay', 2)
                    time.sleep(delay)
                    
                    # Parse the page
                    page_jobs = self._parse_indeed_page(response.text, url)
                    jobs.extend(page_jobs)
                    
                    self.logger.info(f"Found {len(page_jobs)} jobs on Indeed page {page + 1}")
                    
                    # If we got fewer than 10 jobs, we've reached the end
                    if len(page_jobs) < 10:
                        self.logger.info(f"Reached end of Indeed results (found {len(page_jobs)} < 10 jobs)")
                        break
                        
                except JobScrapingError as e:
                    # Log the error and decide whether to continue or stop
                    self.logger.warning(f"Error scraping Indeed page {page + 1}: {e.user_message}")
                    
                    # For rate limits or blocks, stop scraping this site
                    if isinstance(e, (RateLimitError, BlockedError)):
                        self.logger.error(f"Stopping Indeed scraping due to: {e.user_message}")
                        raise e
                    
                    # For other errors, continue to next page
                    continue
                    
        except JobScrapingError:
            # Re-raise JobScrapingError without wrapping
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error scraping Indeed: {e}")
            raise SiteUnavailableError(f"Indeed scraping failed due to unexpected error: {e}", site)
        
        self.logger.info(f"Completed Indeed scraping: {len(jobs)} total jobs found")
        return jobs

    def scrape_linkedin(self, keywords: List[str], location: str = "", max_pages: int = 5) -> List[JobListing]:
        """
        Scrape job listings from LinkedIn
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of JobListing objects
        """
        site = 'linkedin'
        jobs = []
        query = " ".join(keywords)
        
        self.logger.info(f"Starting LinkedIn scraping for keywords: {keywords}, location: {location}, max_pages: {max_pages}")
        
        try:
            for page in range(max_pages):
                start = page * 25  # LinkedIn shows 25 jobs per page
                url = self._build_linkedin_url(query, location, start)
                
                self.logger.info(f"Scraping LinkedIn page {page + 1}/{max_pages}")
                
                try:
                    # Use retry logic for the request
                    response = self._make_request_with_retry(url, site)
                    
                    # Add delay between pages (LinkedIn is more strict)
                    site_config = self.site_configs.get(site, {})
                    delay = site_config.get('base_delay', 3)
                    time.sleep(delay)
                    
                    # Parse the page
                    page_jobs = self._parse_linkedin_page(response.text, url)
                    jobs.extend(page_jobs)
                    
                    self.logger.info(f"Found {len(page_jobs)} jobs on LinkedIn page {page + 1}")
                    
                    # If we got fewer than 25 jobs, we've reached the end
                    if len(page_jobs) < 25:
                        self.logger.info(f"Reached end of LinkedIn results (found {len(page_jobs)} < 25 jobs)")
                        break
                        
                except JobScrapingError as e:
                    # Log the error and decide whether to continue or stop
                    self.logger.warning(f"Error scraping LinkedIn page {page + 1}: {e.user_message}")
                    
                    # For rate limits or blocks, stop scraping this site
                    if isinstance(e, (RateLimitError, BlockedError)):
                        self.logger.error(f"Stopping LinkedIn scraping due to: {e.user_message}")
                        raise e
                    
                    # For other errors, continue to next page
                    continue
                    
        except JobScrapingError:
            # Re-raise JobScrapingError without wrapping
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error scraping LinkedIn: {e}")
            raise SiteUnavailableError(f"LinkedIn scraping failed due to unexpected error: {e}", site)
        
        self.logger.info(f"Completed LinkedIn scraping: {len(jobs)} total jobs found")
        return jobs

    def _build_indeed_url(self, query: str, location: str, start: int) -> str:
        """Build Indeed search URL"""
        base_url = "https://www.indeed.com/jobs"
        params = {
            'q': quote_plus(query),
            'l': quote_plus(location) if location else '',
            'start': start,
            'sort': 'date'  # Sort by most recent
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items() if v is not None and v != ''])
        return f"{base_url}?{param_string}"

    def _build_linkedin_url(self, query: str, location: str, start: int) -> str:
        """Build LinkedIn search URL"""
        base_url = "https://www.linkedin.com/jobs/search"
        params = {
            'keywords': quote_plus(query),
            'location': quote_plus(location) if location else '',
            'start': start,
            'sortBy': 'DD'  # Sort by most recent
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items() if v is not None and v != ''])
        return f"{base_url}?{param_string}"

    def _parse_indeed_page(self, html: str, source_url: str) -> List[JobListing]:
        """Parse Indeed search results page"""
        jobs = []
        parsing_errors = 0
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', {'data-jk': True})
            self.logger.debug(f"Found {len(job_cards)} job cards on Indeed page")
            
            if not job_cards:
                self.logger.warning("No job cards found on Indeed page - page structure may have changed")
                return jobs
            
            for i, card in enumerate(job_cards):
                try:
                    job_data = self._extract_indeed_job_data(card, source_url)
                    if job_data:
                        job = self.normalize_job_data(job_data)
                        jobs.append(job)
                    else:
                        self.logger.debug(f"Skipped Indeed job card {i+1} - missing required fields")
                        
                except Exception as e:
                    parsing_errors += 1
                    self.logger.warning(f"Error parsing Indeed job card {i+1}: {e}")
                    continue
            
            if parsing_errors > 0:
                self.logger.warning(f"Failed to parse {parsing_errors}/{len(job_cards)} Indeed job cards")
            
        except Exception as e:
            self.logger.error(f"Error parsing Indeed page HTML: {e}")
            raise JobScrapingError(f"Failed to parse Indeed page: {e}", ScrapingErrorType.PARSING_ERROR, "indeed")
        
        self.logger.debug(f"Successfully parsed {len(jobs)} jobs from Indeed page")
        return jobs

    def _parse_linkedin_page(self, html: str, source_url: str) -> List[JobListing]:
        """Parse LinkedIn search results page"""
        jobs = []
        parsing_errors = 0
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', {'data-entity-urn': True})
            self.logger.debug(f"Found {len(job_cards)} job cards on LinkedIn page")
            
            if not job_cards:
                self.logger.warning("No job cards found on LinkedIn page - page structure may have changed")
                return jobs
            
            for i, card in enumerate(job_cards):
                try:
                    job_data = self._extract_linkedin_job_data(card, source_url)
                    if job_data:
                        job = self.normalize_job_data(job_data)
                        jobs.append(job)
                    else:
                        self.logger.debug(f"Skipped LinkedIn job card {i+1} - missing required fields")
                        
                except Exception as e:
                    parsing_errors += 1
                    self.logger.warning(f"Error parsing LinkedIn job card {i+1}: {e}")
                    continue
            
            if parsing_errors > 0:
                self.logger.warning(f"Failed to parse {parsing_errors}/{len(job_cards)} LinkedIn job cards")
            
        except Exception as e:
            self.logger.error(f"Error parsing LinkedIn page HTML: {e}")
            raise JobScrapingError(f"Failed to parse LinkedIn page: {e}", ScrapingErrorType.PARSING_ERROR, "linkedin")
        
        self.logger.debug(f"Successfully parsed {len(jobs)} jobs from LinkedIn page")
        return jobs 
    def _extract_indeed_job_data(self, card, source_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from Indeed job card"""
        try:
            # Extract basic information
            title_elem = card.find('h2', class_='jobTitle')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else None
            
            location_elem = card.find('div', {'data-testid': 'job-location'})
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract job URL
            job_link = card.find('h2', class_='jobTitle').find('a') if title_elem else None
            job_url = urljoin('https://www.indeed.com', job_link['href']) if job_link else None
            
            # Extract description snippet
            description_elem = card.find('div', {'data-testid': 'job-snippet'})
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            if not all([title, company]):
                return None
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source_url': job_url or source_url,
                'application_url': job_url,
                'source_site': 'indeed',
                'raw_data': {
                    'remote_indicators': self._extract_remote_indicators(title + " " + description),
                    'experience_indicators': self._extract_experience_indicators(title + " " + description),
                    'technology_keywords': self._extract_technology_keywords(title + " " + description)
                }
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting Indeed job data: {e}")
            return None

    def _extract_linkedin_job_data(self, card, source_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from LinkedIn job card"""
        try:
            # Extract basic information
            title_elem = card.find('h3', class_='base-search-card__title')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            company = company_elem.get_text(strip=True) if company_elem else None
            
            location_elem = card.find('span', class_='job-search-card__location')
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract job URL
            job_link = card.find('a', {'data-tracking-control-name': 'public_jobs_jserp-result_search-card'})
            job_url = job_link['href'] if job_link else None
            
            # Extract description snippet
            description_elem = card.find('p', class_='job-search-card__snippet')
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            if not all([title, company]):
                return None
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'source_url': job_url or source_url,
                'application_url': job_url,
                'source_site': 'linkedin',
                'raw_data': {
                    'remote_indicators': self._extract_remote_indicators(title + " " + description),
                    'experience_indicators': self._extract_experience_indicators(title + " " + description),
                    'technology_keywords': self._extract_technology_keywords(title + " " + description)
                }
            }
            
        except Exception as e:
            self.logger.warning(f"Error extracting LinkedIn job data: {e}")
            return None

    def _extract_remote_indicators(self, text: str) -> List[str]:
        """Extract remote work indicators from text"""
        text_lower = text.lower()
        indicators = []
        
        if any(word in text_lower for word in ['remote', 'trabalho remoto', 'home office']):
            indicators.append('remote')
        if any(word in text_lower for word in ['hybrid', 'híbrido', 'presencial/remoto']):
            indicators.append('hybrid')
        if any(word in text_lower for word in ['on-site', 'onsite', 'presencial', 'escritório']):
            indicators.append('onsite')
            
        return indicators

    def _extract_experience_indicators(self, text: str) -> List[str]:
        """Extract experience level indicators from text"""
        text_lower = text.lower()
        indicators = []
        
        if any(word in text_lower for word in ['intern', 'estagiário', 'estágio']):
            indicators.append('intern')
        if any(word in text_lower for word in ['junior', 'jr', 'iniciante']):
            indicators.append('junior')
        if any(word in text_lower for word in ['senior', 'sr', 'sênior']):
            indicators.append('senior')
        if any(word in text_lower for word in ['lead', 'tech lead', 'líder']):
            indicators.append('lead')
        if any(word in text_lower for word in ['manager', 'gerente', 'coordenador']):
            indicators.append('manager')
            
        return indicators

    def _extract_technology_keywords(self, text: str) -> List[str]:
        """Extract technology keywords from text"""
        # Common technology keywords
        tech_keywords = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'django', 'flask', 'spring', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'git', 'jenkins', 'ci/cd', 'agile', 'scrum', 'machine learning',
            'data science', 'artificial intelligence', 'ai', 'ml'
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords 
    def normalize_job_data(self, raw_data: Dict[str, Any]) -> JobListing:
        """
        Normalize raw job data into a consistent JobListing structure
        
        Args:
            raw_data: Raw job data from scraping
            
        Returns:
            JobListing object
        """
        # Determine remote type
        remote_type = None
        if raw_data.get('raw_data', {}).get('remote_indicators'):
            indicators = raw_data['raw_data']['remote_indicators']
            if 'remote' in indicators:
                remote_type = RemoteType.REMOTE
            elif 'hybrid' in indicators:
                remote_type = RemoteType.HYBRID
            elif 'onsite' in indicators:
                remote_type = RemoteType.ONSITE
        
        # Determine experience level
        experience_level = None
        if raw_data.get('raw_data', {}).get('experience_indicators'):
            indicators = raw_data['raw_data']['experience_indicators']
            # Take the first (most specific) indicator
            if 'intern' in indicators:
                experience_level = ExperienceLevel.INTERN
            elif 'junior' in indicators:
                experience_level = ExperienceLevel.JUNIOR
            elif 'senior' in indicators:
                experience_level = ExperienceLevel.SENIOR
            elif 'lead' in indicators:
                experience_level = ExperienceLevel.LEAD
            elif 'manager' in indicators:
                experience_level = ExperienceLevel.MANAGER
            else:
                experience_level = ExperienceLevel.MID  # Default to mid-level
        
        # Extract technologies
        technologies = raw_data.get('raw_data', {}).get('technology_keywords', [])
        
        return JobListing(
            title=raw_data['title'],
            company=raw_data['company'],
            location=raw_data.get('location'),
            remote_type=remote_type,
            experience_level=experience_level,
            technologies=technologies,
            description=raw_data.get('description', ''),
            source_url=raw_data['source_url'],
            application_url=raw_data.get('application_url'),
            source_site=raw_data['source_site'],
            scraped_at=datetime.now(timezone.utc)
        )

    def save_jobs_to_database(self, jobs: List[JobListing]) -> int:
        """
        Save job listings to database with enhanced error handling
        
        Args:
            jobs: List of JobListing objects to save
            
        Returns:
            Number of jobs saved
        """
        if not jobs:
            self.logger.debug("No jobs to save to database")
            return 0
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        self.logger.info(f"Attempting to save {len(jobs)} jobs to database")
        
        try:
            with get_db_context() as session:
                for i, job in enumerate(jobs):
                    try:
                        # Validate job data before saving
                        if not job.title or not job.company:
                            self.logger.warning(f"Skipping job {i+1} - missing required fields (title: {job.title}, company: {job.company})")
                            error_count += 1
                            continue
                        
                        # Check if job already exists (by source_url)
                        existing = session.query(JobListing).filter_by(source_url=job.source_url).first()
                        if not existing:
                            session.add(job)
                            saved_count += 1
                            self.logger.debug(f"Added new job: {job.title} at {job.company}")
                        else:
                            # Update existing job with new data
                            existing.title = job.title
                            existing.company = job.company
                            existing.location = job.location
                            existing.remote_type = job.remote_type
                            existing.experience_level = job.experience_level
                            existing.technologies = job.technologies
                            existing.description = job.description
                            existing.scraped_at = job.scraped_at
                            updated_count += 1
                            self.logger.debug(f"Updated existing job: {job.title} at {job.company}")
                            
                    except Exception as e:
                        error_count += 1
                        self.logger.error(f"Error processing job {i+1} ({job.title if hasattr(job, 'title') else 'unknown'}): {e}")
                        continue
                
                # Commit all changes
                session.commit()
                self.logger.info(f"Database operation completed: {saved_count} new jobs saved, {updated_count} jobs updated, {error_count} errors")
                
        except Exception as e:
            self.logger.error(f"Database transaction failed: {e}")
            raise JobScrapingError(f"Failed to save jobs to database: {e}")
        
        return saved_count

    def scrape_all_sites(self, keywords: List[str], location: str = "", max_pages: int = 3) -> ScrapingResult:
        """
        Scrape job listings from all supported sites
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_pages: Maximum number of pages to scrape per site
            
        Returns:
            ScrapingResult object containing jobs and error information
        """
        result = ScrapingResult()
        
        self.logger.info(f"Starting comprehensive scraping for keywords: {keywords}, location: {location}")
        
        # Define sites to scrape
        sites = [
            ('indeed', self.scrape_indeed),
            ('linkedin', self.scrape_linkedin)
        ]
        
        for site_name, scrape_method in sites:
            self.logger.info(f"Starting {site_name} scraping...")
            
            try:
                site_jobs = scrape_method(keywords, location, max_pages)
                result.add_site_result(site_name, site_jobs)
                self.logger.info(f"Successfully scraped {len(site_jobs)} jobs from {site_name}")
                
            except JobScrapingError as e:
                # Add the error to results but continue with other sites
                result.add_site_result(site_name, [], e)
                self.logger.error(f"Failed to scrape {site_name}: {e.user_message}")
                
            except Exception as e:
                # Handle unexpected errors
                error = JobScrapingError(f"Unexpected error scraping {site_name}: {e}", site=site_name)
                result.add_site_result(site_name, [], error)
                self.logger.error(f"Unexpected error scraping {site_name}: {e}")
        
        # Check if we got any jobs at all
        if not result.has_jobs():
            if result.has_errors():
                # All sites failed - create a comprehensive error message
                error_messages = [error.user_message for error in result.errors]
                comprehensive_error = SiteUnavailableError(
                    f"All scraping attempts failed. Errors: {'; '.join(error_messages)}"
                )
                self.logger.error(f"Complete scraping failure: {comprehensive_error.user_message}")
                raise comprehensive_error
            else:
                # No errors but no jobs found
                self.logger.warning("No jobs found from any site")
        
        # Save jobs to database
        if result.has_jobs():
            try:
                saved_count = self.save_jobs_to_database(result.jobs)
                result.total_jobs_saved = saved_count
                self.logger.info(f"Saved {saved_count} new jobs to database")
            except Exception as e:
                self.logger.error(f"Error saving jobs to database: {e}")
                # Add database error to results but don't fail the entire operation
                db_error = JobScrapingError(f"Failed to save jobs to database: {e}")
                result.errors.append(db_error)
        
        # Log final summary
        summary = result.get_summary()
        self.logger.info(f"Scraping operation completed: {summary}")
        
        return result
    
    def scrape_all_sites_legacy(self, keywords: List[str], location: str = "", max_pages: int = 3) -> List[JobListing]:
        """
        Legacy method that returns just the job list for backward compatibility
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_pages: Maximum number of pages to scrape per site
            
        Returns:
            List of all scraped JobListing objects
        """
        result = self.scrape_all_sites(keywords, location, max_pages)
        return result.jobs