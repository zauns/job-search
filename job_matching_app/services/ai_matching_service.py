"""
AI-powered matching service using Ollama for keyword extraction and job matching
"""
import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

from ..config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class KeywordExtractionResult:
    """Result of keyword extraction"""
    keywords: List[str]
    confidence: float
    language_detected: str
    fallback_used: bool = False


class OllamaConnectionError(Exception):
    """Exception raised when Ollama service is unavailable"""
    pass


class AIMatchingService:
    """Service for AI-powered keyword extraction and job matching using Ollama"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize AI matching service
        
        Args:
            model_name: Ollama model to use for text processing (defaults to config setting)
        """
        self.settings = get_settings()
        self.model_name = model_name or self.settings.ollama_model
        self.client = None
        self._initialize_client()
        
        # Fallback keywords for different domains
        self.fallback_keywords = {
            'tech': [
                'python', 'javascript', 'java', 'react', 'node.js', 'sql', 'git',
                'docker', 'kubernetes', 'aws', 'machine learning', 'data science',
                'web development', 'software engineering', 'api', 'database'
            ],
            'general': [
                'communication', 'teamwork', 'leadership', 'problem solving',
                'project management', 'analytical thinking', 'creativity',
                'time management', 'adaptability', 'customer service'
            ]
        }
    
    def _initialize_client(self) -> None:
        """Initialize Ollama client and check availability"""
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama library not available. Falling back to manual keyword extraction.")
            return
        
        if not self.settings.ollama_enabled:
            logger.info("Ollama disabled in configuration. Using fallback extraction.")
            return
        
        try:
            # Test connection to Ollama
            response = ollama.list()
            self.client = ollama
            logger.info("Ollama client initialized successfully")
            
            # Check if our model is available
            models_list = response.models if hasattr(response, 'models') else response.get('models', [])
            available_models = []
            
            for model in models_list:
                if hasattr(model, 'model'):
                    # New ollama library returns Model objects with 'model' attribute
                    available_models.append(model.model)
                elif isinstance(model, dict) and 'name' in model:
                    # Older versions might return dicts with 'name'
                    available_models.append(model['name'])
                elif isinstance(model, str):
                    # Some versions might return model names as strings
                    available_models.append(model)
            
            if self.model_name not in available_models:
                logger.warning(f"Model {self.model_name} not found. Available models: {available_models}")
                # Try to use the first available model
                if available_models:
                    self.model_name = available_models[0]
                    logger.info(f"Using model: {self.model_name}")
                else:
                    logger.error("No models available in Ollama")
                    self.client = None
                    
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama service is available"""
        return self.client is not None
    
    def extract_resume_keywords(self, latex_content: str) -> KeywordExtractionResult:
        """
        Extract keywords from LaTeX resume content
        
        Args:
            latex_content: LaTeX source code of the resume
            
        Returns:
            KeywordExtractionResult with extracted keywords and metadata
        """
        # Clean LaTeX content first
        clean_text = self._clean_latex_content(latex_content)
        
        # Detect language
        language = self._detect_language(clean_text)
        
        # Try Ollama extraction first
        if self.is_ollama_available():
            try:
                return self._extract_keywords_with_ollama(clean_text, language)
            except Exception as e:
                logger.warning(f"Ollama extraction failed: {e}. Using fallback method.")
        
        # Fallback to rule-based extraction
        return self._extract_keywords_fallback(clean_text, language)
    
    def _clean_latex_content(self, latex_content: str) -> str:
        """
        Clean LaTeX content to extract readable text
        
        Args:
            latex_content: Raw LaTeX content
            
        Returns:
            Cleaned text content
        """
        # Remove LaTeX commands and environments
        text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})*', ' ', latex_content)
        
        # Remove LaTeX comments
        text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)
        
        # Remove special characters and normalize whitespace
        text = re.sub(r'[{}\\]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common LaTeX document structure
        text = re.sub(r'\\begin\{[^}]+\}|\\end\{[^}]+\}', ' ', text)
        
        return text.strip()
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language of the text (Portuguese or English)
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code ('pt' or 'en')
        """
        # Simple heuristic based on common words
        portuguese_indicators = [
            'experiência', 'formação', 'educação', 'habilidades', 'competências',
            'trabalho', 'empresa', 'projeto', 'desenvolvimento', 'conhecimento',
            'universidade', 'curso', 'graduação', 'mestrado', 'doutorado',
            'desenvolvedor', 'engenheiro', 'bacharelado', 'ciência', 'computação'
        ]
        
        english_indicators = [
            'experience', 'education', 'skills', 'work', 'company', 'project',
            'development', 'knowledge', 'university', 'degree', 'bachelor',
            'master', 'phd', 'software', 'engineer', 'developer', 'computer',
            'science'
        ]
        
        text_lower = text.lower()
        pt_count = sum(1 for word in portuguese_indicators if word in text_lower)
        en_count = sum(1 for word in english_indicators if word in text_lower)
        
        # If no clear indicators, check for Portuguese-specific characters/patterns
        if pt_count == en_count:
            portuguese_patterns = ['ção', 'ões', 'ão', 'ã', 'ê', 'ô', 'ç']
            pt_pattern_count = sum(1 for pattern in portuguese_patterns if pattern in text_lower)
            if pt_pattern_count > 2:
                return 'pt'
        
        return 'pt' if pt_count > en_count else 'en'
    
    def _extract_keywords_with_ollama(self, text: str, language: str) -> KeywordExtractionResult:
        """
        Extract keywords using Ollama
        
        Args:
            text: Cleaned text content
            language: Detected language ('pt' or 'en')
            
        Returns:
            KeywordExtractionResult with extracted keywords
        """
        if language == 'pt':
            prompt = f"""
Analise o seguinte texto de currículo e extraia as palavras-chave mais importantes relacionadas a:
1. Habilidades técnicas (linguagens de programação, ferramentas, tecnologias)
2. Competências profissionais
3. Áreas de conhecimento
4. Certificações ou qualificações

Texto: {text}

IMPORTANTE: Retorne APENAS uma lista de palavras-chave separadas por vírgula. Não inclua explicações, introduções ou comentários.
Formato esperado: python, django, react, postgresql, docker
Máximo 15 palavras-chave, priorizando termos técnicos e específicos.
"""
        else:
            prompt = f"""
Analyze the following resume text and extract the most important keywords related to:
1. Technical skills (programming languages, tools, technologies)
2. Professional competencies
3. Knowledge areas
4. Certifications or qualifications

Text: {text}

IMPORTANT: Return ONLY a comma-separated list of keywords. Do not include explanations, introductions, or comments.
Expected format: python, django, react, postgresql, docker
Maximum 15 keywords, prioritizing technical and specific terms.
"""
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': self.settings.ollama_temperature,
                    'top_p': 0.9,
                    'num_predict': 200  # Limit response length
                }
            )
            
            # Extract keywords from response
            keywords_text = response['response'].strip()
            
            # Clean up the response - remove explanatory text and extract just the keywords
            keywords_text = self._extract_keywords_from_response(keywords_text)
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            
            # Clean and validate keywords
            keywords = self._clean_keywords(keywords)
            
            return KeywordExtractionResult(
                keywords=keywords,
                confidence=0.8,  # High confidence for Ollama extraction
                language_detected=language,
                fallback_used=False
            )
            
        except Exception as e:
            logger.error(f"Ollama keyword extraction failed: {e}")
            raise OllamaConnectionError(f"Failed to extract keywords with Ollama: {e}")
    
    def _extract_keywords_fallback(self, text: str, language: str) -> KeywordExtractionResult:
        """
        Fallback keyword extraction using rule-based approach
        
        Args:
            text: Cleaned text content
            language: Detected language
            
        Returns:
            KeywordExtractionResult with extracted keywords
        """
        keywords = []
        text_lower = text.lower()
        
        # Technical keywords patterns - more comprehensive
        tech_patterns = [
            r'\b(python|java|javascript|typescript|c\+\+|c#|php|ruby|go|rust|swift|kotlin|scala)\b',
            r'\b(react|angular|vue|django|flask|spring|express|laravel|fastapi|nodejs|node\.js)\b',
            r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|sqlite|oracle)\b',
            r'\b(docker|kubernetes|aws|azure|gcp|jenkins|git|github|gitlab|ci/cd|devops)\b',
            r'\b(machine learning|data science|artificial intelligence|deep learning|ai|ml)\b',
            r'\b(api|rest|graphql|microservices|web services|backend|frontend)\b',
            r'\b(linux|unix|windows|macos|bash|shell|powershell)\b',
            r'\b(html|css|sass|scss|bootstrap|tailwind)\b'
        ]
        
        # Extract technical keywords using patterns
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            keywords.extend(matches)
        
        # Look for specific technology mentions in the text
        tech_keywords_to_find = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'django', 'flask', 'spring', 'node.js', 'nodejs', 'express',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'git', 'jenkins',
            'machine learning', 'data science', 'api', 'rest', 'microservices',
            'linux', 'html', 'css', 'bootstrap'
        ]
        
        for keyword in tech_keywords_to_find:
            if keyword in text_lower:
                keywords.append(keyword)
        
        # Add domain-specific fallback keywords based on content
        if any(word in text_lower for word in ['software', 'developer', 'engineer', 'programming', 'development']):
            keywords.extend(self.fallback_keywords['tech'][:8])
        
        # Add general skills if professional content is detected
        if any(word in text_lower for word in ['experience', 'work', 'project', 'team', 'management']):
            keywords.extend(self.fallback_keywords['general'][:5])
        
        # Remove duplicates, clean, and limit
        keywords = list(set(keywords))
        keywords = self._clean_keywords(keywords)
        
        return KeywordExtractionResult(
            keywords=keywords[:15],  # Limit to 15 keywords
            confidence=0.5,  # Lower confidence for fallback
            language_detected=language,
            fallback_used=True
        )
    
    def _extract_keywords_from_response(self, response_text: str) -> str:
        """
        Extract just the keywords from AI response, removing explanatory text
        
        Args:
            response_text: Raw AI response
            
        Returns:
            Cleaned keywords text
        """
        # Remove common AI response patterns
        text = response_text.lower()
        
        # Remove introductory phrases
        intro_patterns = [
            r'here are the.*?keywords:?\s*',
            r'the.*?keywords are:?\s*',
            r'extracted keywords:?\s*',
            r'keywords:?\s*',
            r'here are.*?:\s*'
        ]
        
        for pattern in intro_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove explanatory sentences at the end
        end_patterns = [
            r'\s*let me know.*',
            r'\s*i removed.*',
            r'\s*these are.*',
            r'\s*note:.*',
            r'\s*please.*'
        ]
        
        for pattern in end_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Split by lines and take only lines that look like keyword lists
        lines = text.split('\n')
        keyword_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that are clearly explanatory
            if any(phrase in line for phrase in ['let me know', 'i removed', 'these are', 'note:', 'please']):
                continue
            
            # Keep lines that contain commas (likely keyword lists) or single technical terms
            if ',' in line or self._looks_like_keyword(line):
                keyword_lines.append(line)
        
        return ' '.join(keyword_lines)
    
    def _looks_like_keyword(self, text: str) -> bool:
        """Check if text looks like a single keyword"""
        text = text.strip()
        # Single words or short phrases without explanatory language
        return (len(text.split()) <= 3 and 
                not any(word in text for word in ['the', 'are', 'is', 'was', 'were', 'have', 'has']))
    
    def _clean_keywords(self, keywords: List[str]) -> List[str]:
        """
        Clean and validate extracted keywords
        
        Args:
            keywords: Raw keywords list
            
        Returns:
            Cleaned keywords list
        """
        cleaned = []
        for keyword in keywords:
            # Remove extra whitespace and convert to lowercase
            kw = keyword.strip().lower()
            
            # Skip empty or very short keywords
            if len(kw) < 2:
                continue
            
            # Skip explanatory phrases that might have slipped through
            skip_phrases = [
                "i've limited", "prioritizing", "as requested", "technical and specific",
                "terms as requested", "limited the list", "focusing on", "removed some"
            ]
            
            if any(phrase in kw for phrase in skip_phrases):
                continue
            
            # Clean up partial keywords (remove trailing punctuation/incomplete text)
            kw = re.sub(r'\s*\([^)]*$', '', kw)  # Remove incomplete parentheses
            kw = re.sub(r'[^\w\s\.\-\+#]', '', kw)  # Keep only word chars, spaces, dots, hyphens, plus, hash
            kw = kw.strip()
            
            if len(kw) < 2:
                continue
            
            # Skip common stop words
            stop_words = {
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
                'after', 'above', 'below', 'between', 'among', 'throughout', 'despite',
                'towards', 'upon', 'concerning', 'regarding', 'according', 'including'
            }
            
            if kw not in stop_words:
                cleaned.append(kw)
        
        return cleaned[:15]  # Limit to 15 keywords
    
    def calculate_job_compatibility(self, resume_keywords: List[str], job_description: str) -> float:
        """
        Calculate compatibility score between resume keywords and job description
        
        Args:
            resume_keywords: Keywords extracted from resume
            job_description: Job description text
            
        Returns:
            Compatibility score between 0.0 and 1.0
        """
        if not resume_keywords or not job_description:
            return 0.0
        
        job_text = job_description.lower()
        matches = 0
        
        for keyword in resume_keywords:
            if keyword.lower() in job_text:
                matches += 1
        
        # Calculate basic compatibility score
        compatibility = matches / len(resume_keywords)
        
        # Boost score for exact technical matches
        tech_keywords = [kw for kw in resume_keywords if self._is_technical_keyword(kw)]
        tech_matches = sum(1 for kw in tech_keywords if kw.lower() in job_text)
        
        if tech_keywords:
            tech_boost = (tech_matches / len(tech_keywords)) * 0.3
            compatibility = min(1.0, compatibility + tech_boost)
        
        return round(compatibility, 3)
    
    def _is_technical_keyword(self, keyword: str) -> bool:
        """Check if a keyword is technical/skill-related"""
        technical_indicators = [
            'python', 'java', 'javascript', 'react', 'sql', 'docker', 'aws',
            'machine learning', 'api', 'git', 'linux', 'database', 'framework',
            'library', 'algorithm', 'programming', 'development', 'software'
        ]
        
        keyword_lower = keyword.lower()
        return any(indicator in keyword_lower for indicator in technical_indicators)
    
    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current Ollama model
        
        Returns:
            Dictionary with model information
        """
        if not self.is_ollama_available():
            return {
                'status': 'unavailable',
                'model': 'none',
                'fallback': 'rule-based extraction'
            }
        
        try:
            models = self.client.list()
            models_list = models.models if hasattr(models, 'models') else models.get('models', [])
            current_model = None
            
            for model in models_list:
                model_name = None
                if hasattr(model, 'model'):
                    model_name = model.model
                elif isinstance(model, dict) and 'name' in model:
                    model_name = model['name']
                elif isinstance(model, str):
                    model_name = model
                
                if model_name == self.model_name:
                    if hasattr(model, 'size'):
                        current_model = {'name': model_name, 'size': model.size}
                    elif isinstance(model, dict):
                        current_model = model
                    else:
                        current_model = {'name': model_name, 'size': 'unknown'}
                    break
            
            return {
                'status': 'available',
                'model': self.model_name,
                'size': current_model.get('size', 'unknown') if current_model else 'unknown',
                'fallback': 'none'
            }
        except Exception as e:
            return {
                'status': 'error',
                'model': self.model_name,
                'error': str(e),
                'fallback': 'rule-based extraction'
            }