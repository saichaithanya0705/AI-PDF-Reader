"""
🤖 AI-Powered Persona and Job Classification System
Intelligently matches user intent to available personas and jobs using NLP models
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
import re
from dataclasses import dataclass

# Try to import ML libraries, fallback if not available
try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available, using fallback persona classification")

# Don't import sentence_transformers at module level to avoid issues
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None

def _try_import_sentence_transformers():
    """Try to import sentence transformers at runtime"""
    global SENTENCE_TRANSFORMERS_AVAILABLE, SentenceTransformer
    try:
        from sentence_transformers import SentenceTransformer as ST
        SentenceTransformer = ST
        SENTENCE_TRANSFORMERS_AVAILABLE = True
        return True
    except ImportError as e:
        print(f"⚠️ sentence-transformers not available: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Failed to import sentence-transformers: {e}")
        return False


@dataclass
class PersonaMatch:
    persona: str
    confidence: float
    reasoning: str


@dataclass
class JobMatch:
    job: str
    confidence: float
    reasoning: str


@dataclass
class ClassificationResult:
    persona_match: PersonaMatch
    job_match: JobMatch
    combined_confidence: float
    suggestions: List[str]


class PersonaJobClassifier:
    """AI-powered classifier for matching user intent to personas and jobs"""
    
    def __init__(self):
        # Initialize the sentence transformer model with fallback
        self.model = None

        # Try to import and initialize sentence transformers
        if _try_import_sentence_transformers():
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ SentenceTransformer model loaded successfully")
            except Exception as e:
                print(f"⚠️ Failed to load SentenceTransformer model: {e}")
        else:
            print("⚠️ Using fallback persona classification without embeddings")
        
        # Predefined personas with enhanced descriptions
        self.personas = {
            'Undergraduate Chemistry Student': {
                'keywords': ['student', 'undergraduate', 'chemistry', 'study', 'exam', 'homework', 'assignment', 'lab', 'course', 'college', 'university'],
                'description': 'A student studying chemistry at undergraduate level, focusing on learning concepts, preparing for exams, and completing assignments',
                'related_domains': ['education', 'science', 'chemistry', 'learning']
            },
            'Graduate Research Student': {
                'keywords': ['graduate', 'research', 'phd', 'masters', 'thesis', 'dissertation', 'publication', 'methodology', 'analysis', 'academic'],
                'description': 'A graduate student conducting research, writing thesis, analyzing data, and preparing publications',
                'related_domains': ['research', 'academia', 'methodology', 'analysis']
            },
            'Travel Planner': {
                'keywords': ['travel', 'trip', 'vacation', 'itinerary', 'destination', 'budget', 'hotel', 'flight', 'tourism', 'planner'],
                'description': 'Someone planning trips, managing travel budgets, creating itineraries, and organizing travel logistics',
                'related_domains': ['travel', 'planning', 'tourism', 'logistics']
            },
            'HR Professional': {
                'keywords': ['hr', 'human resources', 'employee', 'recruitment', 'hiring', 'compliance', 'policy', 'workforce', 'personnel'],
                'description': 'Human resources professional managing employees, recruitment, compliance, and organizational policies',
                'related_domains': ['human resources', 'management', 'compliance', 'organizational']
            },
            'Food Contractor': {
                'keywords': ['food', 'catering', 'contractor', 'menu', 'dietary', 'nutrition', 'cooking', 'restaurant', 'chef', 'culinary'],
                'description': 'Food service professional managing catering, menu planning, dietary requirements, and food preparation',
                'related_domains': ['food service', 'catering', 'nutrition', 'culinary']
            },
            'Legal Professional': {
                'keywords': ['legal', 'lawyer', 'attorney', 'law', 'contract', 'regulation', 'compliance', 'litigation', 'counsel'],
                'description': 'Legal professional working with contracts, regulations, compliance, and legal documentation',
                'related_domains': ['legal', 'law', 'contracts', 'compliance']
            },
            'Medical Professional': {
                'keywords': ['medical', 'doctor', 'physician', 'healthcare', 'diagnosis', 'treatment', 'patient', 'clinical', 'medicine'],
                'description': 'Healthcare professional involved in diagnosis, treatment, patient care, and medical procedures',
                'related_domains': ['healthcare', 'medicine', 'clinical', 'patient care']
            },
            'Business Analyst': {
                'keywords': ['business', 'analyst', 'requirements', 'process', 'optimization', 'strategy', 'analysis', 'consulting'],
                'description': 'Business professional analyzing requirements, processes, and business strategies for optimization',
                'related_domains': ['business', 'analysis', 'strategy', 'consulting']
            },
            'Technical Writer': {
                'keywords': ['technical', 'writer', 'documentation', 'manual', 'guide', 'instructions', 'API', 'software', 'procedure'],
                'description': 'Professional creating technical documentation, manuals, guides, and instructional content',
                'related_domains': ['technical writing', 'documentation', 'instruction', 'communication']
            },
            'Financial Analyst': {
                'keywords': ['financial', 'finance', 'analyst', 'investment', 'budget', 'accounting', 'economic', 'market', 'money'],
                'description': 'Financial professional analyzing investments, budgets, market trends, and financial data',
                'related_domains': ['finance', 'investment', 'economics', 'analysis']
            },
            'Software Engineer': {
                'keywords': ['software', 'engineer', 'programming', 'coding', 'development', 'API', 'system', 'technology', 'computer'],
                'description': 'Software professional developing applications, systems, and technical solutions',
                'related_domains': ['software development', 'programming', 'technology', 'engineering']
            },
            'Data Scientist': {
                'keywords': ['data', 'scientist', 'machine learning', 'analytics', 'statistics', 'AI', 'modeling', 'insights', 'algorithm'],
                'description': 'Professional analyzing data, building models, and extracting insights using statistical and ML methods',
                'related_domains': ['data science', 'analytics', 'machine learning', 'statistics']
            },
            'Marketing Professional': {
                'keywords': ['marketing', 'promotion', 'advertising', 'campaign', 'brand', 'customer', 'social media', 'content'],
                'description': 'Marketing professional managing campaigns, brand promotion, and customer engagement strategies',
                'related_domains': ['marketing', 'advertising', 'branding', 'customer engagement']
            },
            'Project Manager': {
                'keywords': ['project', 'manager', 'management', 'coordination', 'timeline', 'milestone', 'team', 'delivery', 'planning'],
                'description': 'Professional managing projects, coordinating teams, and ensuring timely delivery of objectives',
                'related_domains': ['project management', 'coordination', 'planning', 'leadership']
            },
            'General Reader': {
                'keywords': ['general', 'reader', 'reading', 'learning', 'understanding', 'knowledge', 'information', 'curious'],
                'description': 'Someone interested in general reading, learning, and understanding various topics',
                'related_domains': ['general knowledge', 'learning', 'reading', 'education']
            }
        }
        
        # Predefined jobs with enhanced descriptions
        self.jobs = {
            'Identify key concepts and mechanisms for exam preparation': {
                'keywords': ['exam', 'study', 'concepts', 'mechanisms', 'preparation', 'test', 'quiz', 'learning'],
                'description': 'Preparing for academic examinations by identifying and understanding key concepts',
                'related_domains': ['education', 'examination', 'study', 'learning']
            },
            'Extract research methodologies and findings': {
                'keywords': ['research', 'methodology', 'findings', 'analysis', 'study', 'investigation', 'results'],
                'description': 'Analyzing research papers to understand methodologies and extract key findings',
                'related_domains': ['research', 'methodology', 'analysis', 'academic']
            },
            'Plan trip itineraries and budget allocation': {
                'keywords': ['trip', 'itinerary', 'budget', 'travel', 'vacation', 'planning', 'destination', 'cost'],
                'description': 'Planning travel itineraries and managing travel budgets and expenses',
                'related_domains': ['travel', 'planning', 'budgeting', 'logistics']
            },
            'Review compliance requirements and procedures': {
                'keywords': ['compliance', 'requirements', 'procedures', 'regulation', 'policy', 'audit', 'standards'],
                'description': 'Reviewing and ensuring compliance with regulations, policies, and procedures',
                'related_domains': ['compliance', 'regulation', 'policy', 'audit']
            },
            'Analyze dietary requirements and menu planning': {
                'keywords': ['dietary', 'menu', 'nutrition', 'food', 'planning', 'requirements', 'health', 'meal'],
                'description': 'Planning menus and analyzing dietary requirements for food service',
                'related_domains': ['nutrition', 'food service', 'health', 'planning']
            },
            'Review contract terms and legal obligations': {
                'keywords': ['contract', 'legal', 'terms', 'obligations', 'agreement', 'law', 'clause', 'liability'],
                'description': 'Reviewing contracts and understanding legal terms and obligations',
                'related_domains': ['legal', 'contracts', 'law', 'obligations']
            },
            'Understand diagnosis and treatment protocols': {
                'keywords': ['diagnosis', 'treatment', 'protocol', 'medical', 'healthcare', 'patient', 'clinical', 'therapy'],
                'description': 'Understanding medical diagnosis processes and treatment protocols',
                'related_domains': ['healthcare', 'medicine', 'treatment', 'clinical']
            },
            'Identify business requirements and processes': {
                'keywords': ['business', 'requirements', 'processes', 'workflow', 'analysis', 'optimization', 'efficiency'],
                'description': 'Analyzing business processes and identifying requirements for improvement',
                'related_domains': ['business analysis', 'process', 'requirements', 'optimization']
            },
            'Create documentation and user guides': {
                'keywords': ['documentation', 'guide', 'manual', 'instructions', 'technical writing', 'help', 'tutorial'],
                'description': 'Creating technical documentation, user guides, and instructional materials',
                'related_domains': ['documentation', 'technical writing', 'instruction', 'communication']
            },
            'Analyze financial data and trends': {
                'keywords': ['financial', 'data', 'trends', 'analysis', 'market', 'investment', 'economics', 'budget'],
                'description': 'Analyzing financial data, market trends, and investment opportunities',
                'related_domains': ['finance', 'analysis', 'market', 'investment']
            },
            'Understand technical specifications and APIs': {
                'keywords': ['technical', 'specifications', 'API', 'software', 'system', 'development', 'programming'],
                'description': 'Understanding technical specifications, APIs, and software system requirements',
                'related_domains': ['software', 'technical', 'API', 'development']
            },
            'Extract insights from data and research': {
                'keywords': ['insights', 'data', 'research', 'analysis', 'patterns', 'findings', 'statistics'],
                'description': 'Extracting meaningful insights and patterns from data and research',
                'related_domains': ['data analysis', 'research', 'insights', 'statistics']
            },
            'Develop marketing strategies and campaigns': {
                'keywords': ['marketing', 'strategy', 'campaigns', 'promotion', 'advertising', 'brand', 'customer'],
                'description': 'Developing marketing strategies and managing promotional campaigns',
                'related_domains': ['marketing', 'strategy', 'promotion', 'campaigns']
            },
            'Track project milestones and deliverables': {
                'keywords': ['project', 'milestones', 'deliverables', 'tracking', 'management', 'timeline', 'progress'],
                'description': 'Managing project timelines, tracking milestones, and ensuring deliverable completion',
                'related_domains': ['project management', 'tracking', 'milestones', 'delivery']
            },
            'General understanding and learning': {
                'keywords': ['general', 'understanding', 'learning', 'knowledge', 'education', 'comprehension', 'study'],
                'description': 'General learning and understanding of various topics and subjects',
                'related_domains': ['learning', 'education', 'knowledge', 'comprehension']
            }
        }
        
        # Pre-compute embeddings for faster matching (if model available)
        if self.model:
            self._precompute_embeddings()
        else:
            # Fallback: use keyword-based matching
            self.persona_names = list(self.personas.keys())
            self.job_names = list(self.jobs.keys())
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for all personas and jobs"""
        if not self.model:
            return

        # Persona embeddings
        persona_texts = []
        for persona, info in self.personas.items():
            # Combine persona name, description, and keywords
            text = f"{persona} {info['description']} {' '.join(info['keywords'])}"
            persona_texts.append(text)

        self.persona_embeddings = self.model.encode(persona_texts)
        self.persona_names = list(self.personas.keys())

        # Job embeddings
        job_texts = []
        for job, info in self.jobs.items():
            # Combine job name, description, and keywords
            text = f"{job} {info['description']} {' '.join(info['keywords'])}"
            job_texts.append(text)

        self.job_embeddings = self.model.encode(job_texts)
        self.job_names = list(self.jobs.keys())
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from user input"""
        # Remove common stop words and extract meaningful terms
        text = text.lower()
        # Simple keyword extraction (can be enhanced with spaCy/NLTK)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        
        # Filter out very common words
        stop_words = {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from', 'they', 'have', 'been', 'will'}
        keywords = [word for word in words if word not in stop_words]
        
        return keywords

    def _classify_persona_fallback(self, user_input: str) -> PersonaMatch:
        """Fallback persona classification using keyword matching"""
        user_input_lower = user_input.lower()

        best_persona = "General Reader"
        best_confidence = 0.3
        best_reasoning = "Default fallback classification"
        max_score = 0

        for persona, info in self.personas.items():
            score = 0
            matched_keywords = []

            for keyword in info['keywords']:
                if keyword.lower() in user_input_lower:
                    score += 1
                    matched_keywords.append(keyword)

            # Normalize by number of keywords
            normalized_score = score / len(info['keywords']) if info['keywords'] else 0

            if normalized_score > max_score:
                max_score = normalized_score
                best_persona = persona
                best_confidence = min(0.9, 0.3 + normalized_score * 0.6)
                if matched_keywords:
                    best_reasoning = f"Matched keywords: {', '.join(matched_keywords[:3])}"
                else:
                    best_reasoning = "Keyword-based classification (fallback)"

        return PersonaMatch(
            persona=best_persona,
            confidence=best_confidence,
            reasoning=best_reasoning
        )

    def _classify_job_fallback(self, user_input: str, persona_context: str = "") -> JobMatch:
        """Fallback job classification using keyword matching"""
        full_input = f"{user_input} {persona_context}".lower()

        best_job = "General understanding and learning"
        best_confidence = 0.3
        best_reasoning = "Default fallback classification"
        max_score = 0

        for job, info in self.jobs.items():
            score = 0
            matched_keywords = []

            for keyword in info['keywords']:
                if keyword.lower() in full_input:
                    score += 1
                    matched_keywords.append(keyword)

            # Normalize by number of keywords
            normalized_score = score / len(info['keywords']) if info['keywords'] else 0

            if normalized_score > max_score:
                max_score = normalized_score
                best_job = job
                best_confidence = min(0.9, 0.3 + normalized_score * 0.6)
                if matched_keywords:
                    best_reasoning = f"Matched keywords: {', '.join(matched_keywords[:3])}"
                else:
                    best_reasoning = "Keyword-based classification (fallback)"

        return JobMatch(
            job=best_job,
            confidence=best_confidence,
            reasoning=best_reasoning
        )
    
    def _calculate_keyword_match(self, user_keywords: List[str], target_keywords: List[str]) -> float:
        """Calculate keyword-based similarity"""
        if not user_keywords or not target_keywords:
            return 0.0
        
        matches = sum(1 for keyword in user_keywords if any(keyword in target for target in target_keywords))
        return matches / len(user_keywords)
    
    def classify_persona(self, user_input: str) -> PersonaMatch:
        """Classify user input to best matching persona"""
        if not self.model or not SKLEARN_AVAILABLE:
            return self._classify_persona_fallback(user_input)

        # Encode user input
        user_embedding = self.model.encode([user_input])

        # Calculate semantic similarity
        similarities = cosine_similarity(user_embedding, self.persona_embeddings)[0]
        
        # Extract keywords for additional matching
        user_keywords = self._extract_keywords(user_input)
        
        # Combine semantic and keyword-based scoring
        best_score = 0
        best_persona = None
        best_reasoning = ""
        
        for i, (persona_name, persona_info) in enumerate(self.personas.items()):
            semantic_score = similarities[i]
            keyword_score = self._calculate_keyword_match(user_keywords, persona_info['keywords'])
            
            # Weighted combination (60% semantic, 40% keyword)
            combined_score = 0.6 * semantic_score + 0.4 * keyword_score
            
            if combined_score > best_score:
                best_score = combined_score
                best_persona = persona_name
                
                # Generate reasoning
                matched_keywords = [kw for kw in user_keywords if any(kw in target for target in persona_info['keywords'])]
                if matched_keywords:
                    best_reasoning = f"Matched keywords: {', '.join(matched_keywords[:3])}. Semantic similarity: {semantic_score:.2f}"
                else:
                    best_reasoning = f"High semantic similarity ({semantic_score:.2f}) with {persona_name.lower()} context"
        
        return PersonaMatch(
            persona=best_persona or 'General Reader',
            confidence=min(best_score, 1.0),
            reasoning=best_reasoning
        )
    
    def classify_job(self, user_input: str, persona_context: str = "") -> JobMatch:
        """Classify user input to best matching job"""
        if not self.model or not SKLEARN_AVAILABLE:
            return self._classify_job_fallback(user_input, persona_context)

        # Combine user input with persona context for better job matching
        full_input = f"{user_input} {persona_context}"

        # Encode input
        user_embedding = self.model.encode([full_input])
        
        # Calculate semantic similarity
        similarities = cosine_similarity(user_embedding, self.job_embeddings)[0]
        
        # Extract keywords
        user_keywords = self._extract_keywords(user_input)
        
        # Find best matching job
        best_score = 0
        best_job = None
        best_reasoning = ""
        
        for i, (job_name, job_info) in enumerate(self.jobs.items()):
            semantic_score = similarities[i]
            keyword_score = self._calculate_keyword_match(user_keywords, job_info['keywords'])
            
            # Weighted combination (70% semantic, 30% keyword for jobs)
            combined_score = 0.7 * semantic_score + 0.3 * keyword_score
            
            if combined_score > best_score:
                best_score = combined_score
                best_job = job_name
                
                # Generate reasoning
                matched_keywords = [kw for kw in user_keywords if any(kw in target for target in job_info['keywords'])]
                if matched_keywords:
                    best_reasoning = f"Matched keywords: {', '.join(matched_keywords[:3])}. Task similarity: {semantic_score:.2f}"
                else:
                    best_reasoning = f"High task similarity ({semantic_score:.2f}) with {job_name.lower()}"
        
        return JobMatch(
            job=best_job or 'General understanding and learning',
            confidence=min(best_score, 1.0),
            reasoning=best_reasoning
        )
    
    def classify_intent(self, user_input: str) -> ClassificationResult:
        """Classify user input into both persona and job with comprehensive analysis"""
        # Classify persona
        persona_match = self.classify_persona(user_input)
        
        # Classify job with persona context
        job_match = self.classify_job(user_input, persona_match.persona)
        
        # Calculate combined confidence
        combined_confidence = (persona_match.confidence + job_match.confidence) / 2
        
        # Generate suggestions for improvement
        suggestions = []
        
        if combined_confidence < 0.5:
            suggestions.append("Try being more specific about your role or task")
            suggestions.append("Include keywords related to your field or objective")
        elif combined_confidence < 0.7:
            suggestions.append("Consider adding more context about your specific needs")
        
        if persona_match.confidence < 0.4:
            suggestions.append("Specify your professional role or background")
        
        if job_match.confidence < 0.4:
            suggestions.append("Describe what you want to accomplish or learn")
        
        return ClassificationResult(
            persona_match=persona_match,
            job_match=job_match,
            combined_confidence=combined_confidence,
            suggestions=suggestions
        )
    
    def get_alternative_suggestions(self, user_input: str, top_k: int = 3) -> Dict[str, List[Tuple[str, float]]]:
        """Get alternative persona and job suggestions"""
        user_embedding = self.model.encode([user_input])
        
        # Get top persona suggestions
        persona_similarities = cosine_similarity(user_embedding, self.persona_embeddings)[0]
        persona_indices = np.argsort(persona_similarities)[::-1][:top_k]
        persona_suggestions = [(self.persona_names[i], persona_similarities[i]) for i in persona_indices]
        
        # Get top job suggestions
        job_similarities = cosine_similarity(user_embedding, self.job_embeddings)[0]
        job_indices = np.argsort(job_similarities)[::-1][:top_k]
        job_suggestions = [(self.job_names[i], job_similarities[i]) for i in job_indices]
        
        return {
            'personas': persona_suggestions,
            'jobs': job_suggestions
        }


# Global classifier instance
classifier = PersonaJobClassifier()


def classify_user_intent(user_input: str) -> Dict:
    """Main function to classify user intent into persona and job"""
    try:
        result = classifier.classify_intent(user_input)
        
        return {
            'persona': {
                'name': result.persona_match.persona,
                'confidence': result.persona_match.confidence,
                'reasoning': result.persona_match.reasoning
            },
            'job': {
                'name': result.job_match.job,
                'confidence': result.job_match.confidence,
                'reasoning': result.job_match.reasoning
            },
            'combined_confidence': result.combined_confidence,
            'suggestions': result.suggestions,
            'status': 'success'
        }
    
    except Exception as e:
        return {
            'persona': {'name': 'General Reader', 'confidence': 0.5, 'reasoning': 'Fallback due to error'},
            'job': {'name': 'General understanding and learning', 'confidence': 0.5, 'reasoning': 'Fallback due to error'},
            'combined_confidence': 0.5,
            'suggestions': ['Please try rephrasing your request'],
            'status': 'error',
            'error': str(e)
        }


def get_persona_job_suggestions(user_input: str, top_k: int = 3) -> Dict:
    """Get alternative suggestions for persona and job"""
    try:
        suggestions = classifier.get_alternative_suggestions(user_input, top_k)
        return {
            'personas': [{'name': name, 'confidence': conf} for name, conf in suggestions['personas']],
            'jobs': [{'name': name, 'confidence': conf} for name, conf in suggestions['jobs']],
            'status': 'success'
        }
    
    except Exception as e:
        return {
            'personas': [],
            'jobs': [],
            'status': 'error',
            'error': str(e)
        }
