"""
Enhanced LLM Service for Adobe Hackathon
Uses provided chat_with_llm.py for all LLM interactions
Implements core hackathon features: text selection, cross-document search, snippets, insights
"""

import os
import json
import re
import asyncio
from typing import Dict, List, Optional, Any
import logging

# Try to import the provided scripts, fallback if not available
try:
    from .chat_with_llm import get_llm_response
    CHAT_LLM_AVAILABLE = True
except ImportError:
    CHAT_LLM_AVAILABLE = False
    print("⚠️ chat_with_llm.py not available, using fallback")

try:
    from .generate_audio import generate_audio
    AUDIO_AVAILABLE = True
    print("✅ generate_audio.py loaded successfully")
except ImportError as e:
    AUDIO_AVAILABLE = False
    generate_audio = None
    print(f"⚠️ generate_audio.py not available: {e}")
    print("📢 Using TTS service instead for audio generation")

logger = logging.getLogger(__name__)

ALLOWED_INSIGHT_TYPES = {
    "key-takeaway",
    "key-insight",
    "did-you-know",
    "counterpoint",
    "connection",
    "practical-tip",
    "deep-dive",
    "study-tip",
    "historical-context",
    "future-implications",
}

_INSIGHT_TYPE_ALIASES = {
    "summary": "key-takeaway",
    "takeaway": "key-takeaway",
    "key-point": "key-takeaway",
    "key-insight": "key-insight",
    "did-you-know": "did-you-know",
    "fact": "did-you-know",
    "alternative": "counterpoint",
    "counter-argument": "counterpoint",
    "cross-reference": "connection",
    "link": "connection",
    "tip": "practical-tip",
    "actionable-advice": "practical-tip",
    "analysis": "deep-dive",
    "study": "study-tip",
}


class EnhancedLLMService:
    """Enhanced LLM service using provided hackathon scripts"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        logger.info(f"✅ Enhanced LLM Service initialized with provider: {self.provider}")

    @staticmethod
    def _strip_json_fences(response: str) -> str:
        cleaned = (response or "").strip()
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    @staticmethod
    def _unwrap_insight_payload(payload: Any) -> Optional[List[Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("insights", "items", "data"):
                nested = payload.get(key)
                if isinstance(nested, list):
                    return nested
        return None

    def _extract_json_array(self, response: str) -> List[Any]:
        cleaned = self._strip_json_fences(response)
        if not cleaned:
            raise RuntimeError("LLM returned an empty insights response")

        try:
            parsed = json.loads(cleaned)
            unwrapped = self._unwrap_insight_payload(parsed)
            if unwrapped is not None:
                return unwrapped
        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        for idx, ch in enumerate(cleaned):
            if ch not in "[{":
                continue
            try:
                parsed, _ = decoder.raw_decode(cleaned, idx)
                unwrapped = self._unwrap_insight_payload(parsed)
                if unwrapped is not None:
                    return unwrapped
            except json.JSONDecodeError:
                continue

        raise RuntimeError("LLM insights payload was not a JSON array")

    @staticmethod
    def _normalize_insight_type(raw_type: Any) -> str:
        if not isinstance(raw_type, str) or not raw_type.strip():
            return "key-takeaway"
        normalized = re.sub(r"[\s_]+", "-", raw_type.strip().lower())
        if normalized in ALLOWED_INSIGHT_TYPES:
            return normalized
        return _INSIGHT_TYPE_ALIASES.get(normalized, "key-takeaway")

    def _parse_json_array(self, response: str) -> List[Any]:
        payload = json.loads(self._strip_json_fences(response))
        if not isinstance(payload, list):
            logger.warning("LLM response was not a JSON array")
            return []
        return payload

    def _coerce_related_section(self, item: Dict[str, Any], all_sections: List[Dict]) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        section_id = item.get('section_id')
        if isinstance(section_id, bool) or not isinstance(section_id, int):
            return None
        if section_id < 0 or section_id >= len(all_sections):
            return None

        try:
            relevance_score = float(item.get('relevance_score', 0))
        except (TypeError, ValueError):
            relevance_score = 0.0
        relevance_score = max(0.0, min(1.0, relevance_score))

        original_section = all_sections[section_id]
        return {
            "section_id": section_id,
            "relevance_score": relevance_score,
            "snippet": str(item.get("snippet", "")),
            "connection_type": str(item.get("connection_type", "similar")),
            "document_id": original_section.get('document_id'),
            "document_name": original_section.get('document_name'),
            "page": original_section.get('page', 1),
            "title": original_section.get('title', 'Untitled Section')
        }
    
    async def generate_text_selection_insights(self, selected_text: str, context: str, persona: str = None, job: str = None) -> Dict[str, Any]:
        """Generate insights for selected text - core hackathon feature"""
        try:
            if not CHAT_LLM_AVAILABLE:
                # Fallback implementation
                return {
                    "explanation": f"Selected text analysis: {selected_text[:100]}...",
                    "key_points": ["Text selected for analysis", "Context provided"],
                    "connections": ["Related to document content"],
                    "questions": ["What specific aspect interests you?"]
                }

            messages = [
                {"role": "system", "content": f"""You are an AI assistant for Adobe's PDF Intelligence System.
User Profile: {persona or 'General Reader'}
Task: {job or 'Document Analysis'}

Your job is to provide intelligent insights about selected text from PDF documents."""},
                {"role": "user", "content": f"""
Analyze this selected text and provide insights:

SELECTED TEXT: "{selected_text}"
CONTEXT: {context}

Provide a JSON response with:
1. "explanation": Clear explanation of the selected text (2-3 sentences)
2. "key_points": List of 2-3 main takeaways
3. "connections": Potential connections to other concepts
4. "questions": 1-2 follow-up questions to explore

Format as valid JSON.
"""}
            ]

            response = await asyncio.to_thread(get_llm_response, messages)

            try:
                parsed = json.loads(self._strip_json_fences(response))
                if isinstance(parsed, dict):
                    return parsed
                raise RuntimeError("Selection insights response was not a JSON object")
            except json.JSONDecodeError as exc:
                raise RuntimeError("Failed to parse selection insights response as JSON") from exc

        except Exception as e:
            logger.error(f"Error generating text selection insights: {e}")
            raise RuntimeError(f"Error generating text selection insights: {e}") from e
    
    async def find_related_sections(self, selected_text: str, all_sections: List[Dict], persona: str = None, job: str = None, max_results: int = 5) -> List[Dict[str, Any]]:
        """Find related sections across documents - core hackathon feature"""
        try:
            if not CHAT_LLM_AVAILABLE:
                # Fallback: simple keyword matching
                results = []
                selected_words = set(selected_text.lower().split())

                for i, section in enumerate(all_sections[:max_results]):
                    section_text = section.get('content', '').lower()
                    common_words = selected_words.intersection(set(section_text.split()))
                    if common_words:
                        relevance = len(common_words) / len(selected_words) if selected_words else 0
                        results.append({
                            "section_id": i,
                            "relevance_score": min(relevance, 0.9),
                            "snippet": section.get('content', '')[:200] + "...",
                            "connection_type": "similar",
                            "document_id": section.get('document_id'),
                            "document_name": section.get('document_name'),
                            "page": section.get('page', 1),
                            "title": section.get('title', 'Untitled Section')
                        })

                return sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:max_results]

            # Prepare sections for analysis (0-based indices matching output schema)
            sections_text = []
            for i, section in enumerate(all_sections[:20]):  # Limit for performance
                sections_text.append(f"Section {i}: {section.get('title', 'Untitled')} - {section.get('content', '')[:200]}")

            messages = [
                {"role": "system", "content": f"""You are an AI assistant for Adobe's PDF Intelligence System.
User Profile: {persona or 'General Reader'}
Task: {job or 'Document Analysis'}

Find the most relevant sections that relate to the selected text."""},
                {"role": "user", "content": f"""
Selected Text: "{selected_text}"

Available Sections:
{chr(10).join(sections_text)}

Find the top {max_results} most relevant sections and return as JSON array:
[
  {{
    "section_id": 0,
    "relevance_score": 0.95,
    "snippet": "2-4 sentence extract explaining relevance",
    "connection_type": "similar|complementary|contradictory|example"
  }}
]

Focus on semantic relevance, not just keyword matching.
"""}
            ]

            response = await asyncio.to_thread(get_llm_response, messages)

            try:
                related = self._parse_json_array(response)
                enhanced_results = []
                for item in related[:max_results]:
                    result = self._coerce_related_section(item, all_sections)
                    if result:
                        enhanced_results.append(result)

                return enhanced_results

            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON, using fallback")
                return []

        except Exception as e:
            logger.error(f"Error finding related sections: {e}")
            return []
    
    async def generate_insights_bulb(self, content: str, related_sections: List[Dict], persona: str = None, job: str = None) -> List[Dict[str, Any]]:
        """Generate insights bulb content - bonus feature (+5 points)"""
        try:
            # Check for quota exceeded and provide fallback insights
            if self._is_quota_exceeded():
                return self._generate_fallback_insights(content, persona, job)
            # Prepare related content
            related_content = ""
            for section in related_sections[:3]:
                related_content += f"- {section.get('title', 'Section')}: {section.get('snippet', '')}\n"
            
            messages = [
                {"role": "system", "content": f"""You are an AI assistant for Adobe's PDF Intelligence System.
User Profile: {persona or 'General Reader'}
Task: {job or 'Document Analysis'}

Generate diverse insights that add value beyond basic understanding.
Return ONLY a valid JSON array with no markdown fences or extra commentary."""},
                {"role": "user", "content": f"""
Main Content: {content[:12000]}

Related Sections:
{related_content}

Generate exactly 5-6 different types of insights as JSON array:
[
  {{
    "type": "key-takeaway",
    "title": "Main Insight",
    "content": "Key point explained in 1-2 sentences"
  }},
  {{
    "type": "did-you-know",
    "title": "Interesting Fact",
    "content": "Surprising or lesser-known information"
  }},
  {{
    "type": "counterpoint",
    "title": "Alternative Perspective",
    "content": "Different viewpoint or potential contradiction"
  }},
  {{
    "type": "connection",
    "title": "Cross-Reference",
    "content": "How this connects to other concepts or documents"
  }},
  {{
    "type": "practical-tip",
    "title": "Actionable Advice",
    "content": "Practical application or actionable insight"
  }},
  {{
    "type": "deep-dive",
    "title": "Detailed Analysis",
    "content": "More thorough explanation of complex concepts"
  }}
]

Make insights specific and actionable for the user's persona and task.
Return ONLY a valid JSON array with no markdown fences or extra commentary.
"""}
            ]
            
            response = await asyncio.to_thread(get_llm_response, messages)
            
            insights = self._extract_json_array(response)

            validated: List[Dict[str, Any]] = []
            for i, raw_insight in enumerate(insights):
                if not isinstance(raw_insight, dict):
                    continue
                content_text = str(raw_insight.get('content') or raw_insight.get('text') or '').strip()
                title_text = str(raw_insight.get('title') or '').strip()
                if not title_text or not content_text:
                    continue
                item = dict(raw_insight)
                item['id'] = str(item.get('id') or (i + 1))
                item['type'] = self._normalize_insight_type(item.get('type'))
                item['title'] = title_text
                item['content'] = content_text
                relevance = item.get('relevance', 0.8)
                item['relevance'] = relevance
                item['persona_relevance'] = item.get('persona_relevance', relevance)
                validated.append(item)

            if not validated:
                raise RuntimeError("LLM returned zero valid insight items")

            print(f"✅ Successfully parsed {len(validated)} insights")
            return validated[:6]
                
        except Exception as e:
            logger.error(f"Error generating insights bulb: {e}")
            raise RuntimeError(f"Insight generation failed: {e}") from e
    
    async def generate_podcast_script(self, content: str, related_sections: List[Dict], insights: List[Dict], persona: str = None, job: str = None) -> Dict[str, Any]:
        """Generate 2-speaker podcast script - bonus feature (+5 points)"""
        try:
            # Prepare content summary
            content_summary = content[:800] if content else "No content provided"
            insights_summary = "\n".join([f"- {insight.get('title', '')}: {insight.get('content', '')}" for insight in insights[:3]])
            
            messages = [
                {"role": "system", "content": f"""You are an AI assistant creating engaging podcast scripts.
User Profile: {persona or 'General Reader'}
Task: {job or 'Document Analysis'}

Create a natural 2-speaker conversation that's informative and engaging."""},
                {"role": "user", "content": f"""
Create a 2-5 minute podcast script with two speakers discussing:

Main Content: {content_summary}

Key Insights:
{insights_summary}

Format as JSON:
{{
  "title": "Podcast Episode Title",
  "duration_estimate": "3-4 minutes",
  "speakers": [
    {{"name": "Alex", "role": "Host", "voice": "alloy"}},
    {{"name": "Sam", "role": "Expert", "voice": "nova"}}
  ],
  "script": [
    {{"speaker": "Alex", "text": "Welcome to our discussion about..."}},
    {{"speaker": "Sam", "text": "Thanks Alex. This topic is fascinating because..."}}
  ]
}}

Make it conversational, informative, and tailored to the user's persona and goals.
Include natural transitions, questions, and insights from the analysis.
"""}
            ]
            
            response = await asyncio.to_thread(get_llm_response, messages)
            
            try:
                return json.loads(self._strip_json_fences(response))
            except json.JSONDecodeError:
                # Fallback script
                return {
                    "title": "Document Analysis Discussion",
                    "duration_estimate": "2-3 minutes",
                    "speakers": [
                        {"name": "Alex", "role": "Host", "voice": "alloy"},
                        {"name": "Sam", "role": "Expert", "voice": "nova"}
                    ],
                    "script": [
                        {"speaker": "Alex", "text": "Welcome to our document analysis discussion."},
                        {"speaker": "Sam", "text": "Thanks Alex. We've analyzed some interesting content that's relevant to document understanding."},
                        {"speaker": "Alex", "text": "That's fascinating. What are the key takeaways?"},
                        {"speaker": "Sam", "text": "The main insights show important connections across different sections of the documents."}
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error generating podcast script: {e}")
            return {
                "title": "Analysis Discussion",
                "duration_estimate": "2 minutes",
                "speakers": [{"name": "Host", "role": "Presenter", "voice": "alloy"}],
                "script": [{"speaker": "Host", "text": "Document analysis is currently unavailable."}]
            }
    
    async def generate_podcast_audio(self, script: Dict[str, Any], output_dir: str = "backend/data/audio") -> str:
        """Generate audio from podcast script using provided generate_audio.py"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate audio for each speaker segment
            audio_files = []
            speakers = script.get('speakers', [])
            script_segments = script.get('script', [])
            
            for i, segment in enumerate(script_segments):
                speaker_name = segment.get('speaker', 'Speaker')
                text = segment.get('text', '')
                
                # Find speaker voice
                voice = 'alloy'  # default
                for speaker in speakers:
                    if speaker.get('name') == speaker_name:
                        voice = speaker.get('voice', 'alloy')
                        break
                
                # Generate audio segment
                segment_file = os.path.join(output_dir, f"segment_{i:03d}.mp3")
                await asyncio.to_thread(generate_audio, text, segment_file, voice=voice)
                audio_files.append(segment_file)
            
            # For now, return the first segment (in production, would concatenate all)
            return audio_files[0] if audio_files else None
            
        except Exception as e:
            logger.error(f"Error generating podcast audio: {e}")
            return None

    def _is_quota_exceeded(self) -> bool:
        """Check if API quota has been exceeded"""
        # This is a simple check - in production you'd implement more sophisticated tracking
        return False  # For now, rely on exception handling

    def _generate_fallback_insights(self, content: str, persona: str = None, job: str = None) -> List[Dict[str, Any]]:
        """Generate fallback insights when API quota is exceeded"""
        logger.info("🔄 Generating fallback insights due to API limitations")

        # Extract key information from content
        content_preview = content[:200] if content else "Document content"
        doc_type = "document"

        if "hackathon" in content.lower():
            doc_type = "hackathon guide"
        elif "resume" in content.lower():
            doc_type = "resume"
        elif "project" in content.lower():
            doc_type = "project document"
        elif "payment" in content.lower():
            doc_type = "financial document"

        fallback_insights = [
            {
                "type": "key-takeaway",
                "title": "Document Overview",
                "content": f"This {doc_type} contains important information that requires careful review and analysis."
            },
            {
                "type": "did-you-know",
                "title": "Document Structure",
                "content": f"Well-organized {doc_type}s like this typically follow industry standards for clarity and accessibility."
            },
            {
                "type": "practical-tip",
                "title": "Review Strategy",
                "content": f"When analyzing a {doc_type}, focus on key sections and cross-reference with related materials for comprehensive understanding."
            },
            {
                "type": "connection",
                "title": "Related Context",
                "content": f"This {doc_type} likely connects to other documents in your collection - consider reviewing them together for better insights."
            },
            {
                "type": "deep-dive",
                "title": "Further Analysis",
                "content": f"For deeper understanding of this {doc_type}, consider the context, purpose, and intended audience when interpreting the content."
            }
        ]

        # Customize based on persona
        if persona and "student" in persona.lower():
            fallback_insights.append({
                "type": "study-tip",
                "title": "Learning Approach",
                "content": f"As a student, break down this {doc_type} into manageable sections and create summaries for better retention."
            })

        return fallback_insights
