"""
LaTeX editor service for reviewing and editing adapted resumes
"""
import os
import tempfile
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from .resume_service import ResumeService


@dataclass
class LaTeXValidationResult:
    """Result of LaTeX validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class LaTeXEditorService:
    """Service for LaTeX editing and validation"""
    
    def __init__(self):
        self.resume_service = ResumeService()
    
    def get_adapted_resume_for_editing(self, draft_id: int) -> Optional[Dict]:
        """
        Get adapted resume draft for editing
        
        Args:
            draft_id: ID of the adapted resume draft
            
        Returns:
            Dictionary with draft information and LaTeX content
        """
        return self.resume_service.get_adapted_resume_draft(draft_id)
    
    def save_edited_resume(self, draft_id: int, latex_content: str) -> Tuple[bool, List[str]]:
        """
        Save edited resume content with validation
        
        Args:
            draft_id: ID of the adapted resume draft
            latex_content: Updated LaTeX content
            
        Returns:
            Tuple of (success, error_messages)
        """
        try:
            # Validate LaTeX content first
            validation_result = self.validate_latex_content(latex_content)
            
            if not validation_result.is_valid:
                return False, validation_result.errors
            
            # Save the content
            success = self.resume_service.update_adapted_resume_draft(draft_id, latex_content)
            
            if success:
                return True, []
            else:
                return False, ["Failed to save resume draft"]
                
        except ValueError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Unexpected error: {str(e)}"]
    
    def validate_latex_content(self, latex_content: str) -> LaTeXValidationResult:
        """
        Validate LaTeX content for common issues
        
        Args:
            latex_content: LaTeX content to validate
            
        Returns:
            LaTeXValidationResult with validation details
        """
        errors = []
        warnings = []
        
        # Check for required LaTeX structure
        if '\\documentclass' not in latex_content:
            errors.append("Missing \\documentclass declaration")
        
        if '\\begin{document}' not in latex_content:
            errors.append("Missing \\begin{document}")
        
        if '\\end{document}' not in latex_content:
            errors.append("Missing \\end{document}")
        
        # Check for balanced braces
        open_braces = latex_content.count('{')
        close_braces = latex_content.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} opening, {close_braces} closing")
        
        # Check for common LaTeX environments balance
        environments_to_check = ['itemize', 'enumerate', 'description', 'center', 'flushleft', 'flushright']
        for env in environments_to_check:
            begin_count = latex_content.count(f'\\begin{{{env}}}')
            end_count = latex_content.count(f'\\end{{{env}}}')
            if begin_count != end_count:
                errors.append(f"Unbalanced {env} environment: {begin_count} begin, {end_count} end")
        
        # Check for potential issues (warnings)
        if '\\usepackage' not in latex_content:
            warnings.append("No packages imported - document might be very basic")
        
        if latex_content.count('\\section') == 0 and latex_content.count('\\subsection') == 0:
            warnings.append("No sections found - consider organizing content with sections")
        
        # Check for common LaTeX mistakes
        if '\\\\\\' in latex_content:
            warnings.append("Triple backslashes found - might cause spacing issues")
        
        if latex_content.count('\\item') > 0 and latex_content.count('\\begin{itemize}') == 0 and latex_content.count('\\begin{enumerate}') == 0:
            errors.append("\\item found outside of list environment")
        
        is_valid = len(errors) == 0
        
        return LaTeXValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    def preview_latex_compilation(self, latex_content: str) -> Tuple[bool, str]:
        """
        Preview LaTeX compilation without saving
        
        Args:
            latex_content: LaTeX content to compile
            
        Returns:
            Tuple of (success, error_message_or_success_message)
        """
        try:
            # Use resume service to compile
            pdf_content = self.resume_service.compile_to_pdf(latex_content)
            return True, f"Compilation successful. PDF size: {len(pdf_content)} bytes"
        except Exception as e:
            return False, str(e)
    
    def get_latex_editing_suggestions(self, latex_content: str) -> List[str]:
        """
        Get suggestions for improving LaTeX content
        
        Args:
            latex_content: LaTeX content to analyze
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for modern LaTeX practices
        if '\\documentclass{article}' in latex_content:
            suggestions.append("Consider using a more specialized document class like 'moderncv' or 'awesome-cv' for resumes")
        
        # Check for font usage
        if '\\usepackage{times}' in latex_content:
            suggestions.append("Consider using more modern font packages like 'fontspec' with XeLaTeX or LuaLaTeX")
        
        # Check for spacing
        if latex_content.count('\\\\') > latex_content.count('\\item') * 2:
            suggestions.append("Consider using proper LaTeX spacing commands instead of multiple \\\\ for vertical spacing")
        
        # Check for hyperlinks
        if 'http' in latex_content and '\\usepackage{hyperref}' not in latex_content:
            suggestions.append("Add \\usepackage{hyperref} to make URLs clickable")
        
        # Check for contact information formatting
        if '@' in latex_content and '\\href{mailto:' not in latex_content:
            suggestions.append("Consider using \\href{mailto:email@domain.com}{email@domain.com} for email addresses")
        
        return suggestions
    
    def format_latex_content(self, latex_content: str) -> str:
        """
        Basic formatting of LaTeX content for better readability
        
        Args:
            latex_content: LaTeX content to format
            
        Returns:
            Formatted LaTeX content
        """
        lines = latex_content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped_line = line.strip()
            
            # Skip empty lines
            if not stripped_line:
                formatted_lines.append('')
                continue
            
            # Decrease indent for end commands
            if stripped_line.startswith('\\end{') or stripped_line.startswith('}'):
                indent_level = max(0, indent_level - 1)
            
            # Add indentation
            formatted_line = '  ' * indent_level + stripped_line
            formatted_lines.append(formatted_line)
            
            # Increase indent for begin commands
            if stripped_line.startswith('\\begin{') or stripped_line.endswith('{'):
                indent_level += 1
        
        return '\n'.join(formatted_lines)
    
    def get_latex_template_suggestions(self) -> List[Dict[str, str]]:
        """
        Get suggestions for LaTeX resume templates
        
        Returns:
            List of template suggestions with descriptions
        """
        return [
            {
                'name': 'Modern CV',
                'description': 'Professional template with modern styling',
                'package': 'moderncv',
                'example': '\\documentclass[11pt,a4paper,sans]{moderncv}'
            },
            {
                'name': 'Awesome CV',
                'description': 'Clean and awesome LaTeX resume template',
                'package': 'awesome-cv',
                'example': '\\documentclass[11pt, a4paper]{awesome-cv}'
            },
            {
                'name': 'Classic Article',
                'description': 'Simple article-based resume',
                'package': 'article',
                'example': '\\documentclass[11pt,a4paper]{article}'
            }
        ]
    
    def compile_and_save_pdf(self, draft_id: int, output_path: Optional[str] = None) -> Tuple[bool, str, Optional[bytes]]:
        """
        Compile adapted resume to PDF and optionally save to file
        
        Args:
            draft_id: ID of the adapted resume draft
            output_path: Optional path to save PDF file
            
        Returns:
            Tuple of (success, message, pdf_content)
        """
        try:
            pdf_content = self.resume_service.compile_adapted_resume_to_pdf(draft_id, output_path)
            
            if output_path:
                message = f"PDF compiled and saved to {output_path}"
            else:
                message = f"PDF compiled successfully. Size: {len(pdf_content)} bytes"
            
            return True, message, pdf_content
            
        except Exception as e:
            return False, str(e), None