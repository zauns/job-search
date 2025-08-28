"""
Resume processing service for LaTeX resume handling
"""
import os
import subprocess
import tempfile
import shutil
import uuid
import platform
from pathlib import Path
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from ..database import get_db_context
from ..models import Resume
from ..models.validators import validate_latex_content, sanitize_filename
from ..config import get_settings
from .ai_matching_service import AIMatchingService, KeywordExtractionResult


class LaTeXCompilationError(Exception):
    """Exception raised when LaTeX compilation fails"""
    pass


class ResumeService:
    """Service for handling LaTeX resume operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_service = AIMatchingService()
    
    def upload_latex_resume(self, file_path: str, filename: Optional[str] = None) -> Resume:
        """
        Upload and store a LaTeX resume
        
        Args:
            file_path: Path to the LaTeX file
            filename: Optional custom filename
            
        Returns:
            Resume: Created resume object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If LaTeX content is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Resume file not found: {file_path}")
        
        # Read LaTeX content
        with open(file_path, 'r', encoding='utf-8') as f:
            latex_content = f.read()
        
        # Validate LaTeX content
        if not self.validate_latex(latex_content):
            raise ValueError("Invalid LaTeX content. File must contain \\documentclass, \\begin{document}, and \\end{document}")
        
        # Sanitize filename
        if filename is None:
            filename = os.path.basename(file_path)
        safe_filename = sanitize_filename(filename)
        
        # Create resume object
        with get_db_context() as db:
            resume = Resume(
                filename=safe_filename,
                latex_content=latex_content,
                extracted_keywords=[],
                user_keywords=[]
            )
            db.add(resume)
            db.commit()  # Commit to get the ID
            db.refresh(resume)  # Refresh to get all attributes
            
            # Store the data we need before session closes
            resume_data = {
                'id': resume.id,
                'filename': resume.filename,
                'latex_content': resume.latex_content,
                'extracted_keywords': resume.extracted_keywords,
                'user_keywords': resume.user_keywords
            }
        
        # Create a new Resume object with the data (not bound to session)
        result_resume = Resume(**resume_data)
        return result_resume
    
    def validate_latex(self, content: str) -> bool:
        """
        Validate LaTeX content
        
        Args:
            content: LaTeX content to validate
            
        Returns:
            bool: True if valid LaTeX
        """
        return validate_latex_content(content)
    

    def compile_to_pdf(self, latex_content: str, output_path: Optional[str] = None) -> bytes:
        """
        Compile LaTeX content to PDF
        
        Args:
            latex_content: LaTeX source code
            output_path: Optional path to save PDF file
            
        Returns:
            bytes: PDF content as bytes
            
        Raises:
            LaTeXCompilationError: If compilation fails
        """
        # Find pdflatex executable
        pdflatex_path = self._find_pdflatex()
        if not pdflatex_path:
            raise LaTeXCompilationError(
                "pdflatex not found. Please install a LaTeX distribution:\n"
                "• Windows: Install MiKTeX (https://miktex.org/) or TeX Live\n"
                "• After installation, restart your terminal/IDE"
            )
        
        # Note: Skipping MiKTeX update check to avoid timeouts
        
        # Create a temporary directory in the current working directory to avoid path issues
        current_dir = os.getcwd()
        temp_dir_name = f"latex_temp_{uuid.uuid4().hex[:8]}"
        temp_dir = os.path.join(current_dir, temp_dir_name)
        
        try:
            # Create temporary directory
            os.makedirs(temp_dir, exist_ok=True)
            
            tex_file = os.path.join(temp_dir, "resume.tex")
            pdf_file = os.path.join(temp_dir, "resume.pdf")
            
            # Write LaTeX content to temporary file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            # Run pdflatex in the temporary directory
            result = subprocess.run([
                pdflatex_path,
                '-interaction=nonstopmode',
                'resume.tex'
            ], capture_output=True, text=True, cwd=temp_dir, timeout=30)
            
            if result.returncode != 0:
                # Extract meaningful error from LaTeX log
                error_msg = self._extract_latex_error(result.stdout, result.stderr)
                raise LaTeXCompilationError(f"LaTeX compilation failed: {error_msg}")
            
            # Check if PDF was created
            if not os.path.exists(pdf_file):
                raise LaTeXCompilationError("PDF file was not created despite successful compilation")
            
            # Read PDF content
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
            
            # Optionally save to output path
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
            
            return pdf_content
            
        except subprocess.TimeoutExpired:
            raise LaTeXCompilationError("LaTeX compilation timed out (30 seconds)")
        except Exception as e:
            if "LaTeX compilation failed" in str(e):
                raise  # Re-raise LaTeX compilation errors as-is
            raise LaTeXCompilationError(f"Compilation error: {str(e)}")
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def _extract_latex_error(self, stdout: str, stderr: str) -> str:
        """
        Extract meaningful error message from LaTeX output
        
        Args:
            stdout: Standard output from pdflatex
            stderr: Standard error from pdflatex
            
        Returns:
            Cleaned error message
        """
        # Look for common LaTeX error patterns
        error_patterns = [
            "! LaTeX Error:",
            "! Undefined control sequence",
            "! Missing",
            "! Package",
            "! File",
        ]
        
        combined_output = stdout + "\n" + stderr
        lines = combined_output.split('\n')
        
        error_lines = []
        for line in lines:
            for pattern in error_patterns:
                if pattern in line:
                    error_lines.append(line.strip())
                    break
        
        if error_lines:
            return "; ".join(error_lines[:3])  # Return first 3 errors
        
        # If no specific errors found, return last few lines of stderr
        if stderr.strip():
            stderr_lines = [line.strip() for line in stderr.split('\n') if line.strip()]
            return "; ".join(stderr_lines[-2:]) if stderr_lines else "Unknown compilation error"
        
        return "Compilation failed with unknown error"
    
    def get_resume_by_id(self, resume_id: int) -> Optional[Resume]:
        """
        Get resume by ID
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Resume object or None if not found
        """
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return None
            
            # Create detached copy
            return Resume(
                id=resume.id,
                filename=resume.filename,
                latex_content=resume.latex_content,
                extracted_keywords=resume.extracted_keywords,
                user_keywords=resume.user_keywords
            )
    
    def get_all_resumes(self) -> List[Resume]:
        """
        Get all resumes
        
        Returns:
            List of all resume objects
        """
        with get_db_context() as db:
            resumes = db.query(Resume).all()
            
            # Create detached copies
            result = []
            for resume in resumes:
                result.append(Resume(
                    id=resume.id,
                    filename=resume.filename,
                    latex_content=resume.latex_content,
                    extracted_keywords=resume.extracted_keywords,
                    user_keywords=resume.user_keywords
                ))
            
            return result
    
    def update_resume_keywords(self, resume_id: int, extracted_keywords: List[str], user_keywords: List[str]) -> bool:
        """
        Update resume keywords
        
        Args:
            resume_id: Resume ID
            extracted_keywords: AI-extracted keywords
            user_keywords: User-defined keywords
            
        Returns:
            bool: True if successful
        """
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return False
            
            resume.extracted_keywords = extracted_keywords
            resume.user_keywords = user_keywords
            return True
    
    def delete_resume(self, resume_id: int) -> bool:
        """
        Delete a resume
        
        Args:
            resume_id: Resume ID
            
        Returns:
            bool: True if successful
        """
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return False
            
            db.delete(resume)
            return True
    
    def extract_keywords_with_ai(self, resume_id: int) -> KeywordExtractionResult:
        """
        Extract keywords from resume using AI
        
        Args:
            resume_id: Resume ID
            
        Returns:
            KeywordExtractionResult with extracted keywords and metadata
            
        Raises:
            ValueError: If resume not found
        """
        resume = self.get_resume_by_id(resume_id)
        if not resume:
            raise ValueError(f"Resume with ID {resume_id} not found")
        
        # Extract keywords using AI service
        result = self.ai_service.extract_resume_keywords(resume.latex_content)
        
        # Update resume with extracted keywords
        self.update_resume_keywords(resume_id, result.keywords, resume.user_keywords)
        
        return result
    
    def get_ai_service_info(self) -> dict:
        """
        Get information about AI service availability
        
        Returns:
            Dictionary with AI service status and model info
        """
        return self.ai_service.get_model_info()
    
    def add_user_keyword(self, resume_id: int, keyword: str) -> bool:
        """
        Add a user-defined keyword to a resume
        
        Args:
            resume_id: Resume ID
            keyword: Keyword to add
            
        Returns:
            bool: True if keyword was added, False if it already exists
        """
        keyword = keyword.strip().lower()
        if not keyword:
            return False
        
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return False
            
            # Check if keyword already exists in user keywords or extracted keywords
            if keyword in resume.user_keywords or keyword in resume.extracted_keywords:
                return False
            
            # Add keyword
            resume.add_user_keyword(keyword)
            return True
    
    def remove_user_keyword(self, resume_id: int, keyword: str) -> bool:
        """
        Remove a user-defined keyword from a resume
        
        Args:
            resume_id: Resume ID
            keyword: Keyword to remove
            
        Returns:
            bool: True if keyword was removed, False if not found
        """
        keyword = keyword.strip().lower()
        
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return False
            
            if keyword not in resume.user_keywords:
                return False
            
            # Remove keyword
            resume.remove_user_keyword(keyword)
            return True
    
    def clear_user_keywords(self, resume_id: int) -> bool:
        """
        Clear all user-defined keywords from a resume
        
        Args:
            resume_id: Resume ID
            
        Returns:
            bool: True if successful
        """
        with get_db_context() as db:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return False
            
            resume.user_keywords = []
            return True
    
    def get_resume_keywords(self, resume_id: int) -> dict:
        """
        Get all keywords for a resume
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Dictionary with extracted_keywords, user_keywords, and all_keywords
        """
        resume = self.get_resume_by_id(resume_id)
        if not resume:
            return {}
        
        return {
            'extracted_keywords': resume.extracted_keywords,
            'user_keywords': resume.user_keywords,
            'all_keywords': resume.all_keywords
        }
    