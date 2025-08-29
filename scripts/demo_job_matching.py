#!/usr/bin/env python3
"""
Demonstration script for job matching and ranking algorithm
"""
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_matching_app.services.ai_matching_service import AIMatchingService, OllamaConnectionError
from job_matching_app.models.job_listing import JobListing, RemoteType, ExperienceLevel


def create_sample_jobs():
    """Create sample job listings for demonstration"""
    return [
        JobListing(
            id=1,
            title="Senior Python Developer",
            company="TechCorp Brasil",
            location="São Paulo",
            remote_type=RemoteType.HYBRID,
            experience_level=ExperienceLevel.SENIOR,
            technologies=['python', 'django', 'postgresql', 'docker', 'kubernetes'],
            description="""
            Estamos procurando um desenvolvedor Python sênior com experiência em Django.
            O candidato deve ter conhecimento em PostgreSQL, Docker e Kubernetes.
            Experiência com desenvolvimento de APIs REST é obrigatória.
            Conhecimento em AWS e CI/CD é um diferencial.
            """,
            source_url="https://example.com/job/1",
            application_url="https://example.com/apply/1",
            source_site="linkedin",
            scraped_at=datetime.now()
        ),
        JobListing(
            id=2,
            title="Full Stack Developer",
            company="StartupXYZ",
            location="Remote",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.MID,
            technologies=['python', 'react', 'mongodb', 'node.js'],
            description="""
            We are looking for a full-stack developer with Python and React experience.
            Knowledge of MongoDB and Node.js is preferred.
            Experience with modern web development practices and agile methodologies required.
            """,
            source_url="https://example.com/job/2",
            application_url="https://example.com/apply/2",
            source_site="indeed",
            scraped_at=datetime.now()
        ),
        JobListing(
            id=3,
            title="DevOps Engineer",
            company="CloudTech Solutions",
            location="Brasília",
            remote_type=RemoteType.REMOTE,
            experience_level=ExperienceLevel.SENIOR,
            technologies=['docker', 'kubernetes', 'aws', 'terraform', 'python'],
            description="""
            DevOps engineer with strong containerization and cloud experience.
            Docker, Kubernetes, and AWS expertise required.
            Python scripting and Terraform knowledge preferred.
            Experience with monitoring and CI/CD pipelines essential.
            """,
            source_url="https://example.com/job/3",
            application_url="https://example.com/apply/3",
            source_site="linkedin",
            scraped_at=datetime.now()
        ),
        JobListing(
            id=4,
            title="Java Backend Developer",
            company="Enterprise Inc",
            location="Rio de Janeiro",
            remote_type=RemoteType.ONSITE,
            experience_level=ExperienceLevel.MID,
            technologies=['java', 'spring boot', 'oracle', 'microservices'],
            description="""
            Java backend developer position with Spring Boot experience.
            Oracle database knowledge and microservices architecture experience required.
            Strong understanding of enterprise software development needed.
            """,
            source_url="https://example.com/job/4",
            application_url="https://example.com/apply/4",
            source_site="indeed",
            scraped_at=datetime.now()
        ),
        JobListing(
            id=5,
            title="Data Scientist",
            company="AI Analytics",
            location="São Paulo",
            remote_type=RemoteType.HYBRID,
            experience_level=ExperienceLevel.SENIOR,
            technologies=['python', 'machine learning', 'pandas', 'scikit-learn', 'tensorflow'],
            description="""
            Data scientist position focusing on machine learning and AI.
            Strong Python skills with pandas, scikit-learn, and TensorFlow required.
            Experience with data analysis and statistical modeling essential.
            """,
            source_url="https://example.com/job/5",
            application_url="https://example.com/apply/5",
            source_site="linkedin",
            scraped_at=datetime.now()
        )
    ]


def demo_job_matching():
    """Demonstrate job matching and ranking functionality"""
    print("🔍 Job Matching and Ranking Algorithm Demo")
    print("=" * 50)
    
    try:
        # Initialize AI service
        print("Initializing AI Matching Service...")
        ai_service = AIMatchingService()
        print(f"✅ Connected to Ollama model: {ai_service.model_name}")
        print()
        
    except OllamaConnectionError as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print("Please ensure Ollama is running and properly configured.")
        return
    
    # Sample resume keywords (mix of Portuguese and English)
    resume_keywords = [
        'python', 'django', 'postgresql', 'docker', 'kubernetes',
        'desenvolvimento web', 'api rest', 'aws', 'machine learning',
        'banco de dados', 'ci/cd'
    ]
    
    print("📄 Resume Keywords:")
    print(f"   {', '.join(resume_keywords)}")
    print()
    
    # Create sample job listings
    job_listings = create_sample_jobs()
    print(f"💼 Analyzing {len(job_listings)} job listings...")
    print()
    
    # Rank jobs by compatibility
    ranked_results = ai_service.rank_jobs_by_compatibility(resume_keywords, job_listings)
    
    # Display results
    print("🏆 Job Ranking Results (Best to Worst Match):")
    print("-" * 80)
    
    for i, result in enumerate(ranked_results, 1):
        job = result.job_listing
        
        print(f"{i}. {job.title} at {job.company}")
        print(f"   📍 {job.display_location} | {job.experience_level.value.title()} Level")
        print(f"   🔧 Technologies: {', '.join(job.technologies[:5])}")
        print(f"   📊 Compatibility Score: {result.compatibility_score:.1%}")
        print(f"   ✅ Matching Keywords ({len(result.matching_keywords)}): {', '.join(result.matching_keywords[:8])}")
        if result.missing_keywords:
            print(f"   ❌ Missing Keywords ({len(result.missing_keywords)}): {', '.join(result.missing_keywords[:5])}")
        print(f"   🎯 Technical Match: {result.technical_match_score:.1%}")
        print(f"   🌐 Language Bonus: {result.language_match_bonus:.1%}")
        print()
    
    # Show detailed analysis for top match
    if ranked_results:
        top_match = ranked_results[0]
        print("🔬 Detailed Analysis of Top Match:")
        print("-" * 40)
        print(f"Job: {top_match.job_listing.title}")
        print(f"Overall Compatibility: {top_match.compatibility_score:.1%}")
        print(f"Keyword Match Ratio: {top_match.keyword_match_ratio:.1%}")
        print(f"Technical Skills Match: {top_match.technical_match_score:.1%}")
        print(f"Total Keywords Analyzed: {len(resume_keywords)}")
        print(f"Keywords Found: {len(top_match.matching_keywords)}")
        print(f"Keywords Missing: {len(top_match.missing_keywords)}")
        print()
    
    # Demonstrate multilingual matching
    print("🌍 Multilingual Matching Demo:")
    print("-" * 30)
    
    # Test with Portuguese-heavy keywords
    pt_keywords = ['python', 'desenvolvimento', 'programação', 'banco de dados', 'django']
    print(f"Portuguese Keywords: {', '.join(pt_keywords)}")
    
    # Calculate compatibility for first job
    first_job = job_listings[0]
    pt_compatibility = ai_service.calculate_job_compatibility(pt_keywords, first_job.description, first_job.technologies)
    print(f"Compatibility with '{first_job.title}': {pt_compatibility:.1%}")
    print()
    
    print("✨ Demo completed successfully!")
    print("The algorithm successfully:")
    print("  • Ranked jobs by compatibility with resume keywords")
    print("  • Handled multilingual content (Portuguese + English)")
    print("  • Provided detailed matching metrics")
    print("  • Identified technical vs. general keywords")
    print("  • Applied similarity matching for partial matches")


if __name__ == "__main__":
    demo_job_matching()