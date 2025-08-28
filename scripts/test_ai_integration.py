#!/usr/bin/env python3
"""
Test script to demonstrate AI integration functionality
"""
import sys
import os
import tempfile

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from job_matching_app.services import ResumeService, AIMatchingService


def create_sample_resume():
    """Create a sample LaTeX resume for testing"""
    latex_content = """
\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\begin{document}

\\section{Experience}
Senior Software Engineer at TechCorp (2020-2023)
- Developed scalable web applications using Python and Django
- Implemented microservices architecture with Docker and Kubernetes
- Worked with PostgreSQL, Redis, and Elasticsearch
- Built REST APIs and integrated third-party services

\\section{Skills}
Programming: Python, JavaScript, TypeScript, Java
Frameworks: Django, React, Spring Boot, Express.js
Databases: PostgreSQL, MongoDB, Redis, Elasticsearch
DevOps: Docker, Kubernetes, AWS, Jenkins, Git

\\section{Education}
Master of Science in Computer Science
University of Technology (2018-2020)

\\end{document}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as f:
        f.write(latex_content)
        return f.name


def test_ai_service():
    """Test AI service functionality"""
    print("=== Testing AI Matching Service ===")
    
    ai_service = AIMatchingService()
    
    # Check AI service status
    print(f"Ollama available: {ai_service.is_ollama_available()}")
    model_info = ai_service.get_model_info()
    print(f"Model info: {model_info}")
    
    # Test keyword extraction
    sample_latex = """
    \\documentclass{article}
    \\begin{document}
    Senior Python Developer with experience in Django, React, and AWS.
    Worked with PostgreSQL databases and Docker containers.
    \\end{document}
    """
    
    print("\n--- Testing Keyword Extraction ---")
    result = ai_service.extract_resume_keywords(sample_latex)
    print(f"Language detected: {result.language_detected}")
    print(f"Confidence: {result.confidence}")
    print(f"Keywords: {result.keywords}")
    
    # Test job compatibility
    print("\n--- Testing Job Compatibility ---")
    job_description = """
    We are looking for a Python developer with Django experience.
    Knowledge of React, PostgreSQL, and Docker is required.
    AWS experience is a plus.
    """
    
    compatibility = ai_service.calculate_job_compatibility(result.keywords, job_description)
    print(f"Compatibility score: {compatibility}")


def test_resume_service():
    """Test resume service with AI integration"""
    print("\n=== Testing Resume Service with AI ===")
    
    resume_service = ResumeService()
    
    # Create and upload a sample resume
    resume_file = create_sample_resume()
    try:
        print(f"Created sample resume: {resume_file}")
        
        # Upload resume
        resume = resume_service.upload_latex_resume(resume_file, "sample_resume.tex")
        print(f"Uploaded resume with ID: {resume.id}")
        
        # Extract keywords with AI
        print("\n--- Extracting Keywords with AI ---")
        result = resume_service.extract_keywords_with_ai(resume.id)
        print(f"Language detected: {result.language_detected}")
        print(f"Confidence: {result.confidence}")
        print(f"Extracted keywords: {result.keywords}")
        
        # Get updated resume
        updated_resume = resume_service.get_resume_by_id(resume.id)
        print(f"Resume keywords in database: {updated_resume.extracted_keywords}")
        
        # Get AI service info
        ai_info = resume_service.get_ai_service_info()
        print(f"AI service info: {ai_info}")
        
    finally:
        # Cleanup
        if os.path.exists(resume_file):
            os.unlink(resume_file)
            print(f"Cleaned up temporary file: {resume_file}")


def main():
    """Main function"""
    print("AI Integration Test Script")
    print("=" * 50)
    
    try:
        test_ai_service()
        test_resume_service()
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())