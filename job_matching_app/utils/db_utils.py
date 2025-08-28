"""
Database utility functions
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from job_matching_app.database import get_db_context
from job_matching_app.models import Resume, JobListing, JobMatch, AdaptedResumeDraft


def create_sample_data():
    """Create sample data for testing and development"""
    with get_db_context() as db:
        # Create sample resume
        sample_resume = Resume(
            filename="sample_resume.tex",
            latex_content=r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\title{John Doe - Software Developer}
\author{John Doe}
\date{}

\begin{document}
\maketitle

\section{Experience}
Senior Python Developer with 5 years of experience in web development using Django and Flask.
Proficient in PostgreSQL, Redis, and Docker. Experience with machine learning and data analysis.

\section{Skills}
\begin{itemize}
    \item Python, Django, Flask
    \item PostgreSQL, MongoDB, Redis
    \item Docker, Kubernetes, AWS
    \item Machine Learning, Data Science
    \item Git, Linux, CI/CD
\end{itemize}

\section{Education}
Bachelor of Science in Computer Science

\end{document}
            """.strip(),
            extracted_keywords=["python", "django", "flask", "postgresql", "redis", "docker", "machine learning"],
            user_keywords=["kubernetes", "aws", "data science"]
        )
        
        db.add(sample_resume)
        db.flush()  # Get the ID
        
        # Create sample job listings
        sample_jobs = [
            JobListing(
                title="Senior Python Developer",
                company="Tech Innovations Inc",
                location="San Francisco, CA",
                remote_type="hybrid",
                experience_level="senior",
                technologies=["python", "django", "postgresql", "redis", "docker"],
                description="We are seeking a Senior Python Developer to join our team. You will work with Django, PostgreSQL, and modern DevOps tools.",
                source_url="https://example.com/job/1",
                application_url="https://example.com/apply/1",
                source_site="example",
                scraped_at=db.execute("SELECT datetime('now')").scalar()
            ),
            JobListing(
                title="Full Stack Developer",
                company="StartupXYZ",
                location="New York, NY",
                remote_type="remote",
                experience_level="mid",
                technologies=["python", "react", "postgresql", "aws"],
                description="Full stack developer position working with Python backend and React frontend. AWS experience preferred.",
                source_url="https://example.com/job/2",
                application_url="https://example.com/apply/2",
                source_site="example",
                scraped_at=db.execute("SELECT datetime('now')").scalar()
            ),
            JobListing(
                title="Data Scientist",
                company="DataCorp",
                location="Boston, MA",
                remote_type="onsite",
                experience_level="senior",
                technologies=["python", "machine learning", "pandas", "tensorflow", "sql"],
                description="Data Scientist role focusing on machine learning and statistical analysis. Python and ML experience required.",
                source_url="https://example.com/job/3",
                application_url="https://example.com/apply/3",
                source_site="example",
                scraped_at=db.execute("SELECT datetime('now')").scalar()
            )
        ]
        
        for job in sample_jobs:
            db.add(job)
        
        db.flush()  # Get job IDs
        
        # Create sample job matches
        job_matches = [
            JobMatch(
                resume_id=sample_resume.id,
                job_listing_id=sample_jobs[0].id,
                compatibility_score=0.85,
                matching_keywords=["python", "django", "postgresql", "redis", "docker"],
                missing_keywords=["kubernetes"],
                algorithm_version=1
            ),
            JobMatch(
                resume_id=sample_resume.id,
                job_listing_id=sample_jobs[1].id,
                compatibility_score=0.65,
                matching_keywords=["python", "postgresql", "aws"],
                missing_keywords=["react", "frontend"],
                algorithm_version=1
            ),
            JobMatch(
                resume_id=sample_resume.id,
                job_listing_id=sample_jobs[2].id,
                compatibility_score=0.75,
                matching_keywords=["python", "machine learning"],
                missing_keywords=["pandas", "tensorflow"],
                algorithm_version=1
            )
        ]
        
        for match in job_matches:
            db.add(match)
        
        print("✅ Sample data created successfully!")
        print(f"   - Created 1 resume")
        print(f"   - Created {len(sample_jobs)} job listings")
        print(f"   - Created {len(job_matches)} job matches")


def clear_all_data():
    """Clear all data from the database (for testing)"""
    with get_db_context() as db:
        # Delete in order to respect foreign key constraints
        db.query(JobMatch).delete()
        db.query(AdaptedResumeDraft).delete()
        db.query(JobListing).delete()
        db.query(Resume).delete()
        
        print("✅ All data cleared from database")


def get_database_stats():
    """Get statistics about the database contents"""
    with get_db_context() as db:
        resume_count = db.query(Resume).count()
        job_count = db.query(JobListing).count()
        match_count = db.query(JobMatch).count()
        draft_count = db.query(AdaptedResumeDraft).count()
        
        print("📊 Database Statistics:")
        print(f"   - Resumes: {resume_count}")
        print(f"   - Job Listings: {job_count}")
        print(f"   - Job Matches: {match_count}")
        print(f"   - Adapted Resume Drafts: {draft_count}")
        
        return {
            "resumes": resume_count,
            "job_listings": job_count,
            "job_matches": match_count,
            "adapted_drafts": draft_count
        }


def find_resume_by_filename(filename: str) -> Optional[Resume]:
    """Find a resume by filename"""
    with get_db_context() as db:
        return db.query(Resume).filter(Resume.filename == filename).first()


def find_jobs_by_company(company: str) -> List[JobListing]:
    """Find jobs by company name"""
    with get_db_context() as db:
        return db.query(JobListing).filter(JobListing.company.ilike(f"%{company}%")).all()


def get_top_matches_for_resume(resume_id: int, limit: int = 10) -> List[JobMatch]:
    """Get top job matches for a resume"""
    with get_db_context() as db:
        return (db.query(JobMatch)
                .filter(JobMatch.resume_id == resume_id)
                .order_by(JobMatch.compatibility_score.desc())
                .limit(limit)
                .all())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create-sample":
            create_sample_data()
        elif command == "clear":
            clear_all_data()
        elif command == "stats":
            get_database_stats()
        else:
            print("Available commands: create-sample, clear, stats")
    else:
        print("Usage: python -m job_matching_app.utils.db_utils <command>")
        print("Commands: create-sample, clear, stats")