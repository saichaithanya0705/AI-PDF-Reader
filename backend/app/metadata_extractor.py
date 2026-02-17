"""
Metadata Extractor Module
Extracts rich metadata from document text using LLM
"""
import json
import logging
from typing import Dict, Any, List, Optional
from .llm_providers import get_llm_provider

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """Extracts metadata from document text"""
    
    def __init__(self):
        self.llm_provider = get_llm_provider()
        
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from document text
        
        Args:
            text: Document text content (first few pages recommended)
            
        Returns:
            Dictionary containing metadata (summary, topics, entities, etc.)
        """
        try:
            # Truncate text if too long to avoid token limits
            # 10k chars is roughly 2-3k tokens, usually enough for a summary
            truncated_text = text[:10000]
            
            prompt = f"""
            Analyze the following document text and provide a structured summary and metadata.
            
            DOCUMENT TEXT:
            {truncated_text}
            
            INSTRUCTIONS:
            Provide a JSON response with the following fields:
            1. "summary": A concise 2-3 sentence summary of the document.
            2. "topics": A list of 5-7 key topics or themes.
            3. "document_type": The type of document (e.g., Invoice, Contract, Research Paper, Manual, etc.).
            4. "entities": A list of key entities (organizations, people, locations, products) mentioned.
            5. "key_dates": Any significant dates mentioned (optional).
            
            Ensure the response is valid JSON. Do not include markdown formatting like ```json.
            """
            
            response = await self.llm_provider.generate_text(prompt, max_tokens=1000)
            content = response.content.strip()
            
            # Clean up markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            try:
                metadata = json.loads(content)
                return metadata
            except json.JSONDecodeError:
                logger.error(f"Failed to parse metadata JSON: {content}")
                # Fallback
                return {
                    "summary": "Could not extract structured metadata.",
                    "topics": [],
                    "document_type": "Unknown",
                    "entities": []
                }
                
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {
                "summary": "Error during metadata extraction.",
                "topics": [],
                "document_type": "Unknown",
                "entities": []
            }

# Global instance
_metadata_extractor = None

def get_metadata_extractor() -> MetadataExtractor:
    global _metadata_extractor
    if _metadata_extractor is None:
        _metadata_extractor = MetadataExtractor()
    return _metadata_extractor
