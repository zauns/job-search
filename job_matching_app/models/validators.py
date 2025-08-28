"""
Model validation utilities
"""
import re
from typing import List, Optional


def validate_latex_content(content: str) -> bool:
    """
    Validate that content appears to be valid LaTeX
    
    Args:
        content: LaTeX content to validate
        
    Returns:
        True if content appears to be valid LaTeX
    """
    if not content or not isinstance(content, str):
        return False
    
    # Check for basic LaTeX structure
    has_documentclass = '\\documentclass' in content
    has_begin_document = '\\begin{document}' in content
    has_end_document = '\\end{document}' in content
    
    return has_documentclass and has_begin_document and has_end_document


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears valid
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def validate_keywords(keywords: List[str]) -> bool:
    """
    Validate keywords list
    
    Args:
        keywords: List of keywords to validate
        
    Returns:
        True if keywords list is valid
    """
    if not isinstance(keywords, list):
        return False
    
    # Check that all items are strings and not empty
    for keyword in keywords:
        if not isinstance(keyword, str) or not keyword.strip():
            return False
    
    return True


def validate_compatibility_score(score: float) -> bool:
    """
    Validate compatibility score is between 0 and 1
    
    Args:
        score: Compatibility score to validate
        
    Returns:
        True if score is valid
    """
    return isinstance(score, (int, float)) and 0.0 <= score <= 1.0


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "untitled"
    
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        sanitized = name[:max_name_length] + ('.' + ext if ext else '')
    
    return sanitized


def extract_technologies_from_text(text: str, max_technologies: int = 10) -> List[str]:
    """
    Extract technology keywords from job description text
    
    Args:
        text: Text to extract technologies from
        max_technologies: Maximum number of technologies to return
        
    Returns:
        List of extracted technology keywords
    """
    if not text:
        return []
    
    # Common technology keywords (this could be expanded or loaded from a file)
    tech_keywords = {
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
        'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'laravel',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'sqlite',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'jenkins',
        'git', 'linux', 'nginx', 'apache', 'graphql', 'rest', 'api',
        'machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch'
    }
    
    text_lower = text.lower()
    found_technologies = []
    
    for tech in tech_keywords:
        if tech in text_lower:
            found_technologies.append(tech)
    
    return found_technologies[:max_technologies]