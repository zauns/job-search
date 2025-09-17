#!/usr/bin/env python3
"""
Test script to demonstrate enhanced error handling in job scraping service
"""
import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_matching_app.services.job_scraping_service import (
    JobScrapingService,
    JobScrapingError,
    RateLimitError,
    SiteUnavailableError,
    NetworkError,
    BlockedError,
    TimeoutError,
    ScrapingResult
)

def setup_logging():
    """Setup logging to see detailed error handling"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_error_handling():
    """Test the enhanced error handling functionality"""
    print("=== Testing Enhanced Error Handling for Job Scraping ===\n")
    
    setup_logging()
    
    # Create scraping service
    scraping_service = JobScrapingService()
    
    print("1. Testing Error Message Generation:")
    print("-" * 40)
    
    # Test different error types
    errors = [
        RateLimitError("Rate limit exceeded", "indeed", 120),
        SiteUnavailableError("Site is down", "linkedin"),
        NetworkError("Connection failed", "indeed"),
        BlockedError("Access denied", "linkedin"),
        TimeoutError("Request timeout", "indeed"),
        JobScrapingError("Generic error", site="test_site")
    ]
    
    for error in errors:
        print(f"Error Type: {error.__class__.__name__}")
        print(f"User Message: {error.user_message}")
        print(f"Site: {error.site}")
        if hasattr(error, 'retry_after') and error.retry_after:
            print(f"Retry After: {error.retry_after} seconds")
        print()
    
    print("2. Testing Retry Delay Calculation:")
    print("-" * 40)
    
    for attempt in range(5):
        delay = scraping_service._calculate_retry_delay(attempt)
        print(f"Attempt {attempt + 1}: {delay} seconds delay")
    
    print()
    
    print("3. Testing ScrapingResult:")
    print("-" * 40)
    
    # Create a sample result
    result = ScrapingResult()
    
    # Add some successful results
    from job_matching_app.models.job_listing import JobListing
    from datetime import datetime, timezone
    
    job1 = JobListing(
        title="Python Developer",
        company="Tech Corp",
        description="Python development role",
        source_url="https://example.com/job1",
        source_site="indeed",
        scraped_at=datetime.now(timezone.utc)
    )
    
    result.add_site_result("indeed", [job1])
    result.total_jobs_saved = 1
    
    # Add a failed result
    error = RateLimitError("Rate limit exceeded", "linkedin", 60)
    result.add_site_result("linkedin", [], error)
    
    print(f"Has jobs: {result.has_jobs()}")
    print(f"Has errors: {result.has_errors()}")
    print(f"Successful sites: {result.successful_sites}")
    print(f"Failed sites: {result.failed_sites}")
    print(f"Summary: {result.get_summary()}")
    
    print("\n4. Testing Site Configuration:")
    print("-" * 40)
    
    for site, config in scraping_service.site_configs.items():
        print(f"Site: {site}")
        for key, value in config.items():
            print(f"  {key}: {value}")
        print()
    
    print("=== Error Handling Test Complete ===")

if __name__ == "__main__":
    test_error_handling()