"""
Resume processing service for LaTeX resume handling
"""
import os
import subprocess
import tempfile
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
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "resume.tex"
            pdf_file = temp_path / "resume.pdf"
            
            # Write LaTeX content to temporary file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            try:
                # Run pdflatex
                result = subprocess.run([
                    'pdflatex',
                    '-interaction=nonstopmode',
                    '-output-directory', str(temp_path),
                    str(tex_file)
                ], capture_output=True, text=True, cwd=temp_path)
                
                if result.returncode != 0:
                    raise LaTeXCompilationError(f"LaTeX compilation failed: {result.stderr}")
                
                # Check if PDF was created
                if not pdf_file.exists():
                    raise LaTeXCompilationError("PDF file was not created")
                
                # Read PDF content
                with open(pdf_file, 'rb') as f:
                    pdf_content = f.read()
                
                # Optionally save to output path
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(pdf_content)
                
                return pdf_content
                
            except FileNotFoundError:
                raise LaTeXCompilationError(
                    "pdflatex not found. Please install a LaTeX distribution (e.g., TeX Live, MiKTeX)"
                )
            except Exception as e:
                raise LaTeXCompilationError(f"Compilation error: {str(e)}")
    
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
    
    def check_latex_installation(self) -> Tuple[bool, str]:
        """
        Check if LaTeX is properly installed
        
        Returns:
            Tuple of (is_installed, version_info)
        """
        try:
            result = subprocess.run(['pdflatex', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return True, version_line
            else:
                return False, "pdflatex command failed"
        except FileNotFoundError:
            return False, "pdflatex not found in PATH"
        except Exception as e:
            return False, f"Error checking LaTeX: {str(e)}"