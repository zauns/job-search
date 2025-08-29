"""
Job scraping service for collecting job listings from multiple sources
"""
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models.job_listing import JobListing, RemoteType, ExperienceLevel
from ..database import get_db_context


class JobScrapingError(Exception):
    """Base exception for job scraping errors"""
    pass


class RateLimitError(JobScrapingError):
    """Exception raised when rate limit is exceeded"""
    pass


class SiteUnavailableError(JobScrapingError):
    """Exception raised when a job site is unavailable"""
    pass


class JobScrapingService:
    """Service for scraping job listings from multiple sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
        
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
        jobs = []
        query = " ".join(keywords)
        
        try:
            for page in range(max_pages):
                start = page * 10  # Indeed shows 10 jobs per page
                url = self._build_indeed_url(query, location, start)
                
                self.logger.info(f"Scraping Indeed page {page + 1}: {url}")
                
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # Add delay to avoid rate limiting
                    time.sleep(2)
                    
                    page_jobs = self._parse_indeed_page(response.text, url)
                    jobs.extend(page_jobs)
                    
                    # If we got fewer than 10 jobs, we've reached the end
                    if len(page_jobs) < 10:
                        break
                        
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error scraping Indeed page {page + 1}: {e}")
                    if "429" in str(e):
                        raise RateLimitError(f"Rate limit exceeded for Indeed: {e}")
                    continue
                    
        except RateLimitError:
            # Re-raise rate limit errors without wrapping
            raise
        except Exception as e:
            self.logger.error(f"Error scraping Indeed: {e}")
            raise SiteUnavailableError(f"Indeed scraping failed: {e}")
        
        self.logger.info(f"Scraped {len(jobs)} jobs from Indeed")
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
        jobs = []
        query = " ".join(keywords)
        
        try:
            for page in range(max_pages):
                start = page * 25  # LinkedIn shows 25 jobs per page
                url = self._build_linkedin_url(query, location, start)
                
                self.logger.info(f"Scraping LinkedIn page {page + 1}: {url}")
                
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # Add delay to avoid rate limiting
                    time.sleep(3)  # LinkedIn is more strict
                    
                    page_jobs = self._parse_linkedin_page(response.text, url)
                    jobs.extend(page_jobs)
                    
                    # If we got fewer than 25 jobs, we've reached the end
                    if len(page_jobs) < 25:
                        break
                        
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error scraping LinkedIn page {page + 1}: {e}")
                    if "429" in str(e):
                        raise RateLimitError(f"Rate limit exceeded for LinkedIn: {e}")
                    continue
                    
        except RateLimitError:
            # Re-raise rate limit errors without wrapping
            raise
        except Exception as e:
            self.logger.error(f"Error scraping LinkedIn: {e}")
            raise SiteUnavailableError(f"LinkedIn scraping failed: {e}")
        
        self.logger.info(f"Scraped {len(jobs)} jobs from LinkedIn")
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
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find job cards
        job_cards = soup.find_all('div', {'data-jk': True})
        
        for card in job_cards:
            try:
                job_data = self._extract_indeed_job_data(card, source_url)
                if job_data:
                    job = self.normalize_job_data(job_data)
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error parsing Indeed job card: {e}")
                continue
        
        return jobs

    def _parse_linkedin_page(self, html: str, source_url: str) -> List[JobListing]:
        """Parse LinkedIn search results page"""
        jobs = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find job cards
        job_cards = soup.find_all('div', {'data-entity-urn': True})
        
        for card in job_cards:
            try:
                job_data = self._extract_linkedin_job_data(card, source_url)
                if job_data:
                    job = self.normalize_job_data(job_data)
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error parsing LinkedIn job card: {e}")
                continue
        
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
        Save job listings to database
        
        Args:
            jobs: List of JobListing objects to save
            
        Returns:
            Number of jobs saved
        """
        if not jobs:
            return 0
        
        saved_count = 0
        
        with get_db_context() as session:
            for job in jobs:
                try:
                    # Check if job already exists (by source_url)
                    existing = session.query(JobListing).filter_by(source_url=job.source_url).first()
                    if not existing:
                        session.add(job)
                        saved_count += 1
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
                        
                except Exception as e:
                    self.logger.error(f"Error saving job to database: {e}")
                    continue
            
            session.commit()
        
        self.logger.info(f"Saved {saved_count} new jobs to database")
        return saved_count

    def scrape_all_sites(self, keywords: List[str], location: str = "", max_pages: int = 3) -> List[JobListing]:
        """
        Scrape job listings from all supported sites
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_pages: Maximum number of pages to scrape per site
            
        Returns:
            List of all scraped JobListing objects
        """
        all_jobs = []
        errors = []
        
        # Scrape Indeed
        try:
            indeed_jobs = self.scrape_indeed(keywords, location, max_pages)
            all_jobs.extend(indeed_jobs)
            self.logger.info(f"Successfully scraped {len(indeed_jobs)} jobs from Indeed")
        except Exception as e:
            error_msg = f"Failed to scrape Indeed: {e}"
            self.logger.error(error_msg)
            errors.append(error_msg)
        
        # Scrape LinkedIn
        try:
            linkedin_jobs = self.scrape_linkedin(keywords, location, max_pages)
            all_jobs.extend(linkedin_jobs)
            self.logger.info(f"Successfully scraped {len(linkedin_jobs)} jobs from LinkedIn")
        except Exception as e:
            error_msg = f"Failed to scrape LinkedIn: {e}"
            self.logger.error(error_msg)
            errors.append(error_msg)
        
        if errors and not all_jobs:
            raise SiteUnavailableError(f"All scraping attempts failed: {'; '.join(errors)}")
        
        # Save to database
        saved_count = self.save_jobs_to_database(all_jobs)
        
        self.logger.info(f"Scraping completed: {len(all_jobs)} total jobs found, {saved_count} new jobs saved")
        
        return all_jobs