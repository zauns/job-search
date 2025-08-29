"""
AI-powered matching service using Ollama for keyword extraction and job matching
"""
import re
import json
import logging
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

from ..config import get_settings
from ..models.job_listing import JobListing
from ..models.job_match import JobMatch


logger = logging.getLogger(__name__)


@dataclass
class KeywordExtractionResult:
    """Result of keyword extraction"""
    keywords: List[str]
    confidence: float
    language_detected: str


@dataclass
class JobMatchResult:
    """Result of job matching with detailed metrics"""
    job_listing: JobListing
    compatibility_score: float
    matching_keywords: List[str]
    missing_keywords: List[str]
    keyword_match_ratio: float
    technical_match_score: float
    language_match_bonus: float


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
    
    def _initialize_client(self) -> None:
        """Initialize Ollama client and require availability"""
        if not OLLAMA_AVAILABLE:
            raise OllamaConnectionError("Ollama library not available. Please install ollama package.")
        
        if not self.settings.ollama_enabled:
            raise OllamaConnectionError("Ollama disabled in configuration. Please enable Ollama to use AI matching service.")
        
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
                    raise OllamaConnectionError("No models available in Ollama. Please ensure models are installed.")
                    
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise OllamaConnectionError(f"Failed to initialize Ollama client: {e}")
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama service is available"""
        return self.client is not None
    
    def extract_resume_keywords(self, latex_content: str) -> KeywordExtractionResult:
        """
        Extract keywords from LaTeX resume content using Ollama
        
        Args:
            latex_content: LaTeX source code of the resume
            
        Returns:
            KeywordExtractionResult with extracted keywords and metadata
        """
        # Clean LaTeX content first
        clean_text = self._clean_latex_content(latex_content)
        
        # Detect language
        language = self._detect_language(clean_text)
        
        # Extract keywords using Ollama (required)
        return self._extract_keywords_with_ollama(clean_text, language)
    
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
                language_detected=language
            )
            
        except Exception as e:
            logger.error(f"Ollama keyword extraction failed: {e}")
            raise OllamaConnectionError(f"Failed to extract keywords with Ollama: {e}")
    

    
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
    
    def calculate_job_compatibility(self, resume_keywords: List[str], job_description: str, job_technologies: List[str] = None) -> float:
        """
        Calculate compatibility score between resume keywords and job description
        
        Args:
            resume_keywords: Keywords extracted from resume
            job_description: Job description text
            job_technologies: List of technologies from job listing (optional)
            
        Returns:
            Compatibility score between 0.0 and 1.0
        """
        if not resume_keywords or not job_description:
            return 0.0
        
        job_text = job_description.lower()
        job_tech_list = [tech.lower() for tech in (job_technologies or [])]
        
        # Find exact keyword matches in description
        exact_matches = []
        for keyword in resume_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in job_text or keyword_lower in job_tech_list:
                exact_matches.append(keyword)
        
        # Find partial/fuzzy matches using similarity
        partial_matches = []
        for keyword in resume_keywords:
            if keyword not in exact_matches:
                if self._find_similar_terms(keyword.lower(), job_text, threshold=0.7):
                    partial_matches.append(keyword)
        
        # Calculate base compatibility score
        total_matches = len(exact_matches) + (len(partial_matches) * 0.5)
        base_compatibility = total_matches / len(resume_keywords)
        
        # Apply technical keyword boost
        tech_keywords = [kw for kw in resume_keywords if self._is_technical_keyword(kw)]
        tech_exact_matches = [kw for kw in exact_matches if self._is_technical_keyword(kw)]
        tech_partial_matches = [kw for kw in partial_matches if self._is_technical_keyword(kw)]
        
        tech_boost = 0.0
        if tech_keywords:
            tech_match_score = (len(tech_exact_matches) + len(tech_partial_matches) * 0.5) / len(tech_keywords)
            tech_boost = tech_match_score * 0.2  # 20% boost for technical matches
        
        # Apply language consistency bonus
        job_language = self._detect_language(job_description)
        resume_language = self._detect_resume_language(resume_keywords)
        language_bonus = 0.05 if job_language == resume_language else 0.0
        
        # Calculate final score
        final_score = min(1.0, base_compatibility + tech_boost + language_bonus)
        return round(final_score, 3)
    
    def calculate_detailed_job_match(self, resume_keywords: List[str], job_listing: JobListing) -> JobMatchResult:
        """
        Calculate detailed job match with comprehensive metrics
        
        Args:
            resume_keywords: Keywords extracted from resume
            job_listing: Job listing to match against
            
        Returns:
            JobMatchResult with detailed matching information
        """
        if not resume_keywords:
            return JobMatchResult(
                job_listing=job_listing,
                compatibility_score=0.0,
                matching_keywords=[],
                missing_keywords=[],
                keyword_match_ratio=0.0,
                technical_match_score=0.0,
                language_match_bonus=0.0
            )
        
        job_text = job_listing.description.lower()
        job_tech_list = [tech.lower() for tech in (job_listing.technologies or [])]
        
        # Find matching and missing keywords
        matching_keywords = []
        missing_keywords = []
        
        for keyword in resume_keywords:
            keyword_lower = keyword.lower()
            if (keyword_lower in job_text or 
                keyword_lower in job_tech_list or 
                self._find_similar_terms(keyword_lower, job_text, threshold=0.8)):
                matching_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        # Calculate metrics
        keyword_match_ratio = len(matching_keywords) / len(resume_keywords) if resume_keywords else 0.0
        
        # Technical match score
        tech_keywords = [kw for kw in resume_keywords if self._is_technical_keyword(kw)]
        tech_matches = [kw for kw in matching_keywords if self._is_technical_keyword(kw)]
        technical_match_score = len(tech_matches) / len(tech_keywords) if tech_keywords else 0.0
        
        # Language match bonus
        job_language = self._detect_language(job_listing.description)
        resume_language = self._detect_resume_language(resume_keywords)
        language_match_bonus = 0.05 if job_language == resume_language else 0.0
        
        # Calculate overall compatibility
        compatibility_score = self.calculate_job_compatibility(
            resume_keywords, 
            job_listing.description, 
            job_listing.technologies
        )
        
        return JobMatchResult(
            job_listing=job_listing,
            compatibility_score=compatibility_score,
            matching_keywords=matching_keywords,
            missing_keywords=missing_keywords,
            keyword_match_ratio=keyword_match_ratio,
            technical_match_score=technical_match_score,
            language_match_bonus=language_match_bonus
        )
    
    def rank_jobs_by_compatibility(self, resume_keywords: List[str], job_listings: List[JobListing]) -> List[JobMatchResult]:
        """
        Rank job listings by compatibility with resume keywords
        
        Args:
            resume_keywords: Keywords extracted from resume
            job_listings: List of job listings to rank
            
        Returns:
            List of JobMatchResult sorted by compatibility score (highest first)
        """
        if not resume_keywords or not job_listings:
            return []
        
        # Calculate detailed matches for all jobs
        job_matches = []
        for job_listing in job_listings:
            match_result = self.calculate_detailed_job_match(resume_keywords, job_listing)
            job_matches.append(match_result)
        
        # Sort by compatibility score (descending) with secondary sorting criteria
        job_matches.sort(key=lambda x: (
            x.compatibility_score,           # Primary: overall compatibility
            x.technical_match_score,         # Secondary: technical match quality
            x.keyword_match_ratio,           # Tertiary: keyword coverage
            len(x.matching_keywords)         # Quaternary: absolute number of matches
        ), reverse=True)
        
        return job_matches
    
    def create_job_match_records(self, resume_id: int, job_match_results: List[JobMatchResult]) -> List[JobMatch]:
        """
        Create JobMatch database records from matching results
        
        Args:
            resume_id: ID of the resume
            job_match_results: List of job match results
            
        Returns:
            List of JobMatch objects ready for database insertion
        """
        job_matches = []
        
        for result in job_match_results:
            job_match = JobMatch(
                resume_id=resume_id,
                job_listing_id=result.job_listing.id,
                compatibility_score=result.compatibility_score,
                matching_keywords=result.matching_keywords,
                missing_keywords=result.missing_keywords,
                algorithm_version=2  # Updated algorithm version
            )
            job_matches.append(job_match)
        
        return job_matches
    
    def _is_technical_keyword(self, keyword: str) -> bool:
        """Check if a keyword is technical/skill-related"""
        technical_indicators = [
            'python', 'java', 'javascript', 'react', 'sql', 'docker', 'aws',
            'machine learning', 'api', 'git', 'linux', 'database', 'framework',
            'library', 'algorithm', 'programming', 'development', 'software',
            'typescript', 'node', 'angular', 'vue', 'mongodb', 'postgresql',
            'redis', 'kubernetes', 'jenkins', 'ci/cd', 'devops', 'cloud',
            'microservices', 'rest', 'graphql', 'agile', 'scrum', 'testing',
            'django', 'flask', 'spring', 'boot', 'hibernate', 'maven', 'gradle',
            'webpack', 'babel', 'sass', 'css', 'html', 'bootstrap', 'jquery'
        ]
        
        keyword_lower = keyword.lower()
        return any(indicator in keyword_lower for indicator in technical_indicators)
    
    def _find_similar_terms(self, keyword: str, text: str, threshold: float = 0.7) -> bool:
        """
        Find similar terms in text using simple string similarity
        
        Args:
            keyword: Keyword to search for
            text: Text to search in
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if similar terms found above threshold
        """
        # Split text into words and clean them
        words = re.findall(r'\b\w+\b', text.lower())
        
        for word in words:
            if len(word) < 3:  # Skip very short words
                continue
            
            # Calculate simple similarity score
            similarity = self._calculate_string_similarity(keyword, word)
            if similarity >= threshold:
                return True
        
        return False
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Jaccard similarity
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not str1 or not str2:
            return 0.0
        
        if str1 == str2:
            return 1.0
        
        # Use character n-grams for similarity
        def get_ngrams(text: str, n: int = 2) -> set:
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = get_ngrams(str1.lower())
        ngrams2 = get_ngrams(str2.lower())
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def _detect_resume_language(self, keywords: List[str]) -> str:
        """
        Detect language of resume based on keywords
        
        Args:
            keywords: List of keywords from resume
            
        Returns:
            Language code ('pt' or 'en')
        """
        if not keywords:
            return 'en'
        
        # Join keywords into text for language detection
        keywords_text = ' '.join(keywords)
        return self._detect_language(keywords_text)
    
    def _normalize_multilingual_keywords(self, keywords: List[str], target_language: str = 'en') -> List[str]:
        """
        Normalize keywords for multilingual matching
        
        Args:
            keywords: List of keywords to normalize
            target_language: Target language for normalization
            
        Returns:
            Normalized keywords list
        """
        # Simple translation mapping for common technical terms
        pt_to_en_mapping = {
            'desenvolvimento': 'development',
            'programação': 'programming',
            'banco de dados': 'database',
            'ciência de dados': 'data science',
            'aprendizado de máquina': 'machine learning',
            'inteligência artificial': 'artificial intelligence',
            'engenharia de software': 'software engineering',
            'desenvolvimento web': 'web development',
            'aplicação web': 'web application',
            'sistema': 'system',
            'arquitetura': 'architecture',
            'framework': 'framework',
            'biblioteca': 'library',
            'ferramenta': 'tool',
            'tecnologia': 'technology'
        }
        
        en_to_pt_mapping = {v: k for k, v in pt_to_en_mapping.items()}
        
        normalized = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            if target_language == 'en' and keyword_lower in pt_to_en_mapping:
                normalized.append(pt_to_en_mapping[keyword_lower])
            elif target_language == 'pt' and keyword_lower in en_to_pt_mapping:
                normalized.append(en_to_pt_mapping[keyword_lower])
            else:
                normalized.append(keyword)
        
        return normalized
    
    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current Ollama model
        
        Returns:
            Dictionary with Ollama model information
            
        Raises:
            OllamaConnectionError: If Ollama service is unavailable
        """
        if not self.is_ollama_available():
            raise OllamaConnectionError("Ollama service is not available. Please ensure Ollama is running and properly configured.")
        
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
            
            if not current_model:
                raise OllamaConnectionError(f"Ollama model '{self.model_name}' not found. Please ensure the model is installed.")
            
            return {
                'status': 'available',
                'model': self.model_name,
                'size': current_model.get('size', 'unknown') if current_model else 'unknown'
            }
        except OllamaConnectionError:
            raise
        except Exception as e:
            raise OllamaConnectionError(f"Failed to retrieve Ollama model information: {e}")
    
    def adapt_resume_content(self, original_latex: str, job_data: dict) -> str:
        """
        Adapt resume LaTeX content for a specific job using Ollama
        
        Args:
            original_latex: Original LaTeX resume content
            job_data: Dictionary with job information (title, company, description, technologies, etc.)
            
        Returns:
            Adapted LaTeX content
            
        Raises:
            OllamaConnectionError: If Ollama service is unavailable
        """
        if not self.is_ollama_available():
            raise OllamaConnectionError("Ollama service is not available for resume adaptation")
        
        # Extract key information from job data
        job_title = job_data.get('title', '')
        job_company = job_data.get('company', '')
        job_description = job_data.get('description', '')
        job_technologies = job_data.get('technologies', [])
        experience_level = job_data.get('experience_level', '')
        
        # Detect language of the original resume
        clean_text = self._clean_latex_content(original_latex)
        resume_language = self._detect_language(clean_text)
        
        # Create adaptation prompt based on language
        if resume_language == 'pt':
            prompt = self._create_portuguese_adaptation_prompt(
                original_latex, job_title, job_company, job_description, job_technologies, experience_level
            )
        else:
            prompt = self._create_english_adaptation_prompt(
                original_latex, job_title, job_company, job_description, job_technologies, experience_level
            )
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent output
                    'top_p': 0.8,
                    'num_predict': 2000  # Allow longer response for full LaTeX content
                }
            )
            
            adapted_latex = response['response'].strip()
            
            # Clean and validate the adapted LaTeX
            adapted_latex = self._clean_adapted_latex_response(adapted_latex)
            
            # Ensure the adapted content maintains LaTeX structure
            if not self._validate_latex_structure(adapted_latex):
                raise Exception("AI-generated LaTeX does not maintain proper document structure")
            
            return adapted_latex
            
        except Exception as e:
            logger.error(f"Resume adaptation failed: {e}")
            raise OllamaConnectionError(f"Failed to adapt resume with Ollama: {e}")
    
    def _create_portuguese_adaptation_prompt(self, original_latex: str, job_title: str, 
                                           job_company: str, job_description: str, 
                                           job_technologies: List[str], experience_level: str) -> str:
        """Create Portuguese adaptation prompt"""
        tech_list = ', '.join(job_technologies) if job_technologies else 'não especificadas'
        
        return f"""
Você é um especialista em adaptação de currículos para vagas específicas. Sua tarefa é adaptar o currículo LaTeX fornecido para otimizar as chances de aprovação no ATS (Applicant Tracking System) e impressionar recrutadores para a vaga específica.

INFORMAÇÕES DA VAGA:
- Título: {job_title}
- Empresa: {job_company}
- Nível: {experience_level}
- Tecnologias principais: {tech_list}

DESCRIÇÃO DA VAGA:
{job_description[:1000]}...

CURRÍCULO ORIGINAL (LaTeX):
{original_latex}

INSTRUÇÕES PARA ADAPTAÇÃO:
1. MANTENHA a estrutura LaTeX original intacta (\\documentclass, \\begin{{document}}, \\end{{document}}, etc.)
2. PRESERVE todas as seções principais do currículo
3. ADAPTE o conteúdo para destacar experiências e habilidades relevantes para esta vaga
4. INCLUA palavras-chave da descrição da vaga de forma natural no texto
5. AJUSTE a ordem das experiências para priorizar as mais relevantes
6. MANTENHA a veracidade das informações - apenas reorganize e enfatize, não invente
7. OTIMIZE para ATS incluindo tecnologias e termos técnicos mencionados na vaga

IMPORTANTE: Retorne APENAS o código LaTeX adaptado, sem explicações ou comentários adicionais.
"""
    
    def _create_english_adaptation_prompt(self, original_latex: str, job_title: str, 
                                        job_company: str, job_description: str, 
                                        job_technologies: List[str], experience_level: str) -> str:
        """Create English adaptation prompt"""
        tech_list = ', '.join(job_technologies) if job_technologies else 'not specified'
        
        return f"""
You are an expert in resume adaptation for specific job positions. Your task is to adapt the provided LaTeX resume to optimize chances of ATS (Applicant Tracking System) approval and impress recruiters for this specific position.

JOB INFORMATION:
- Title: {job_title}
- Company: {job_company}
- Level: {experience_level}
- Key Technologies: {tech_list}

JOB DESCRIPTION:
{job_description[:1000]}...

ORIGINAL RESUME (LaTeX):
{original_latex}

ADAPTATION INSTRUCTIONS:
1. MAINTAIN the original LaTeX structure intact (\\documentclass, \\begin{{document}}, \\end{{document}}, etc.)
2. PRESERVE all main resume sections
3. ADAPT content to highlight experiences and skills relevant to this position
4. INCLUDE keywords from the job description naturally in the text
5. ADJUST the order of experiences to prioritize the most relevant ones
6. MAINTAIN truthfulness of information - only reorganize and emphasize, don't fabricate
7. OPTIMIZE for ATS by including technologies and technical terms mentioned in the job posting

IMPORTANT: Return ONLY the adapted LaTeX code, without explanations or additional comments.
"""
    
    def _clean_adapted_latex_response(self, response: str) -> str:
        """
        Clean the AI response to extract only LaTeX content
        
        Args:
            response: Raw AI response
            
        Returns:
            Cleaned LaTeX content
        """
        # Remove any explanatory text before or after LaTeX content
        lines = response.split('\n')
        latex_lines = []
        in_latex = False
        
        for line in lines:
            # Start collecting when we see documentclass
            if '\\documentclass' in line:
                in_latex = True
            
            if in_latex:
                latex_lines.append(line)
            
            # Stop collecting after \end{document}
            if '\\end{document}' in line:
                break
        
        # If we didn't find proper LaTeX structure, try to extract from code blocks
        if not latex_lines:
            # Look for code blocks
            code_block_pattern = r'```(?:latex)?\s*\n(.*?)\n```'
            matches = re.findall(code_block_pattern, response, re.DOTALL)
            if matches:
                return matches[0].strip()
            
            # If no code blocks, return the original response cleaned
            return response.strip()
        
        return '\n'.join(latex_lines)
    
    def _validate_latex_structure(self, latex_content: str) -> bool:
        """
        Validate that LaTeX content maintains proper document structure
        
        Args:
            latex_content: LaTeX content to validate
            
        Returns:
            bool: True if structure is valid
        """
        required_elements = [
            r'\\documentclass',
            r'\\begin\{document\}',
            r'\\end\{document\}'
        ]
        
        for element in required_elements:
            if not re.search(element, latex_content):
                return False
        
        return True