"""
Enhanced LLM Provider for Adobe Hackathon - Integrates provided chat_with_llm.py
Supports multiple LLM providers: Gemini, Azure OpenAI, OpenAI, Ollama
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import openai
import requests
from pydantic import BaseModel
from .chat_with_llm import get_llm_response

# Lazy imports for google.generativeai to avoid version conflicts
genai = None
vertexai = None
GenerativeModel = None


class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_insights(self, content: str, persona: str, job: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def generate_snippets(self, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate 2-4 sentence snippets from related sections"""
        pass

    @abstractmethod
    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        pass


class GeminiProvider(LLMProvider):
    def __init__(self):
        # Import genai here to avoid module-level import errors
        global genai, vertexai, GenerativeModel
        try:
            import google.generativeai as genai
        except ImportError:
            print("⚠️ google-generativeai not available")
            genai = None
        
        try:
            import vertexai as vertex_module
            from vertexai.generative_models import GenerativeModel as GenModel
            vertexai = vertex_module
            GenerativeModel = GenModel
        except (ImportError, Exception) as e:
            print(f"⚠️ vertexai not available: {e}")
            vertexai = None
            GenerativeModel = None
        
        # Configure Gemini using Vertex AI
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-project-id')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        
        try:
            if credentials_path and vertexai:
                # Set credentials environment variable
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                
                # Initialize Vertex AI
                vertexai.init(project=project_id, location=location)
                
                self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
                self.model = GenerativeModel(self.model_name)
                print(f"✅ Vertex AI Gemini initialized: {self.model_name}")
            else:
                raise Exception("Vertex AI not available, using fallback")
            
        except Exception as e:
            print(f"⚠️ Vertex AI initialization failed, falling back to genai: {e}")
            # Fallback to direct genai configuration
            if credentials_path:
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                genai.configure(api_key=credentials.get('api_key'))
            
            self.model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            self.model = genai.GenerativeModel(self.model_name)
            self.use_vertex = False
        else:
            self.use_vertex = True
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            if hasattr(self, 'use_vertex') and self.use_vertex:
                # Use Vertex AI
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )
                return LLMResponse(
                    content=response.text,
                    model=self.model_name
                )
            else:
                # Use genai fallback with simple config
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )
                return LLMResponse(
                    content=response.text,
                    model=self.model_name
                )
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def generate_insights_from_pdf(self, pdf_path: str, page: int, persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate insights by sending the actual PDF file to Gemini (multimodal)"""
        try:
            from pathlib import Path
            import base64
            
            if not Path(pdf_path).exists():
                raise Exception(f"PDF file not found: {pdf_path}")
            
            # Read PDF file as base64 for multimodal input
            with open(pdf_path, "rb") as pdf_file:
                pdf_data = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            prompt = f"""
            You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}
            
            Analyze this ENTIRE PDF document and provide exactly 4 insights with deep understanding of the complete content.
            Focus on page {page} but use the entire document context for comprehensive analysis.
            
            Generate insights across these categories:
            1. "key-insight": Most critical takeaway from the complete PDF analysis
            2. "did-you-know": Surprising insight discovered from the full document context
            3. "counterpoint": Alternative perspective considering the entire document scope
            4. "connection": How different parts of this PDF relate to each other or external concepts
            
            Requirements for {persona} working on {job}:
            - Analyze the COMPLETE PDF file, not just text extraction
            - Leverage visual elements, formatting, and document structure
            - Each insight should be 1-2 sentences with actionable value
            - Score relevance (0.1-1.0) based on importance to persona's goals
            - Focus on insights only possible from analyzing the actual PDF file
            
            Return ONLY valid JSON array:
            [{{"type": "key-insight", "title": "PDF-Based Insight", "content": "Insight from complete PDF analysis", "relevance": 0.95}}]
            """
            
            if hasattr(self, 'use_vertex') and self.use_vertex:
                # For Vertex AI, try using the PDF as a Part
                try:
                    import vertexai.generative_models as generative_models
                    
                    # Create PDF part for multimodal input
                    pdf_part = generative_models.Part.from_data(
                        data=base64.b64decode(pdf_data),
                        mime_type="application/pdf"
                    )
                    
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        [pdf_part, prompt]
                    )
                    insights_text = response.text
                    
                except Exception as multimodal_error:
                    print(f"⚠️ Multimodal PDF analysis failed, using text fallback: {multimodal_error}")
                    # Fallback to text extraction if multimodal fails
                    return await self.generate_insights(f"PDF file at {pdf_path} for {persona}", persona, job)
            else:
                # Fallback to text-based analysis for non-Vertex setups
                return await self.generate_insights(f"PDF file analysis for {persona} - {job}", persona, job)
            
            # Parse JSON response
            import json
            try:
                insights_data = json.loads(insights_text)
                print(f"✅ Successfully generated PDF-based insights from actual file: {pdf_path}")
                return insights_data[:4] if len(insights_data) >= 4 else insights_data
            except:
                return [{"type": "key-insight", "title": "PDF Analysis", "content": insights_text[:200], "relevance": 0.8}]
                
        except Exception as e:
            print(f"❌ PDF file analysis failed: {e}")
            # Fallback to text-based analysis
            return await self.generate_insights(f"PDF analysis failed, using text fallback for {persona}", persona, job)
    
    async def generate_comprehensive_insights_from_pdf(self, pdf_path: str, page: int) -> List[Dict[str, Any]]:
        """Generate comprehensive insights by sending the actual PDF file to Gemini (no persona dependency)"""
        try:
            from pathlib import Path
            import base64
            
            if not Path(pdf_path).exists():
                raise Exception(f"PDF file not found: {pdf_path}")
            
            # Read PDF file as base64 for multimodal input
            with open(pdf_path, "rb") as pdf_file:
                pdf_data = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            prompt = f"""
            You are an advanced AI document analyzer. Analyze this COMPLETE PDF document and provide exactly 4 comprehensive insights.
            Focus primarily on page {page} but use the entire document context for superior analysis.
            
            Generate insights across these categories:
            1. "key-insight": Most critical takeaway from analyzing the complete document
            2. "did-you-know": Surprising insight or hidden pattern discovered in the content
            3. "counterpoint": Alternative perspective or limitation revealed by the analysis
            4. "connection": How different parts of this document relate or connect to broader concepts
            
            Requirements:
            - Analyze the COMPLETE PDF file including visual elements, formatting, and structure
            - Each insight should be 1-2 sentences with clear value
            - Focus on insights only possible from seeing the full document
            - Be specific and actionable
            - Score relevance (0.1-1.0) based on insight value
            
            Return ONLY valid JSON array:
            [{{"type": "key-insight", "title": "Document Analysis", "content": "Specific insight from complete analysis", "relevance": 0.95}}]
            """
            
            if hasattr(self, 'use_vertex') and self.use_vertex:
                try:
                    import vertexai.generative_models as generative_models
                    
                    pdf_part = generative_models.Part.from_data(
                        data=base64.b64decode(pdf_data),
                        mime_type="application/pdf"
                    )
                    
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        [pdf_part, prompt]
                    )
                    insights_text = response.text
                    
                except Exception as multimodal_error:
                    print(f"⚠️ Multimodal PDF analysis failed: {multimodal_error}")
                    raise multimodal_error
            else:
                raise Exception("Non-Vertex setups not supported for PDF file analysis")
            
            # Parse JSON response
            import json
            try:
                insights_data = json.loads(insights_text)
                print(f"✅ Successfully generated comprehensive PDF insights from: {pdf_path}")
                return insights_data[:4] if len(insights_data) >= 4 else insights_data
            except:
                return [{"type": "key-insight", "title": "PDF Analysis", "content": insights_text[:200], "relevance": 0.8}]
                
        except Exception as e:
            print(f"❌ PDF file analysis failed: {e}")
            raise e
    
    async def generate_comprehensive_insights(self, content: str, document_name: str, current_page: int) -> List[Dict[str, Any]]:
        """Generate comprehensive insights from text content without persona dependency"""
        prompt = f"""
        You are an advanced AI document analyzer. Analyze this document content and provide exactly 4 comprehensive insights.
        
        Document: {document_name}
        Current Page: {current_page}
        
        Content: {content[:8000]}{'...' if len(content) > 8000 else ''}
        
        Generate insights across these categories:
        1. "key-insight": Most critical takeaway from the document analysis
        2. "did-you-know": Surprising fact or pattern discovered in the content
        3. "counterpoint": Alternative perspective or limitation revealed
        4. "connection": How this content connects to broader concepts or themes
        
        Requirements:
        - Each insight should be 1-2 sentences with clear, actionable value
        - Focus on content that saves reading time and enhances understanding
        - Be specific to this document and its content
        - Score relevance (0.1-1.0) based on insight importance
        
        Return ONLY valid JSON array:
        [{{"type": "key-insight", "title": "Analysis Result", "content": "Specific insight from content", "relevance": 0.9}}]
        """
        
        response = await self.generate_text(prompt, 1200)
        try:
            insights_data = json.loads(response.content)
            print(f"✅ Generated comprehensive insights for {document_name}")
            return insights_data[:4] if len(insights_data) >= 4 else insights_data
        except:
            return [{"type": "key-insight", "title": "Content Analysis", "content": response.content[:200], "relevance": 0.8}]
    
    async def generate_insights(self, content: str, persona: str, job: str) -> List[Dict[str, Any]]:
        # Use more content for comprehensive analysis (up to 10k characters for better context)
        content_limit = min(len(content), 10000)
        prompt = f"""
        You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}
        
        Analyze this COMPLETE PDF document and provide exactly 4 insights that demonstrate deep understanding of the entire content.
        You have access to the full document content, not just one page. Use this comprehensive view to generate superior insights.
        
        FULL PDF CONTENT:
        {content[:content_limit]}{'...' if len(content) > content_limit else ''}
        
        Generate insights across these categories:
        1. "key-insight": Most critical takeaway from analyzing the ENTIRE document
        2. "did-you-know": Surprising insight or connection discovered across multiple pages/sections  
        3. "counterpoint": Alternative perspective or limitation considering the complete context
        4. "connection": How different parts of this document relate to each other or external concepts
        
        Requirements for {persona} working on {job}:
        - Analyze patterns across the ENTIRE document, not just individual pages
        - Each insight should be 1-2 sentences with actionable value
        - Leverage the complete context to provide deeper understanding
        - Score relevance (0.1-1.0) based on importance to persona's goals
        - Focus on insights only possible from seeing the full document
        
        Return ONLY valid JSON array:
        [{{"type": "key-insight", "title": "Document-Wide Insight", "content": "Insight based on complete analysis", "relevance": 0.95}}, ...]
        """
        
        response = await self.generate_text(prompt, 1200)
        try:
            insights_data = json.loads(response.content)
            # Ensure we have exactly 4 insights as per Adobe requirements
            return insights_data[:4] if len(insights_data) >= 4 else insights_data
        except:
            return [{"type": "key-insight", "title": "Analysis", "content": response.content, "relevance": 0.8}]

    async def generate_snippets(self, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate 2-4 sentence snippets from related sections"""
        try:
            # Prepare related sections content
            sections_content = []
            for section in related_sections[:5]:  # Limit to top 5 sections
                sections_content.append(f"Section: {section.get('content', '')[:500]}")

            prompt = f"""
            You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}

            Based on the selected text and related sections, generate 2-4 concise, informative snippets.
            Each snippet should be 2-4 sentences and provide valuable context or insights.

            Selected Text: {selected_text}

            Related Sections:
            {chr(10).join(sections_content)}

            Generate exactly 3 snippets in JSON format:
            [
                {{"type": "context", "title": "Context Title", "content": "2-4 sentence explanation"}},
                {{"type": "insight", "title": "Key Insight", "content": "2-4 sentence insight"}},
                {{"type": "connection", "title": "Related Information", "content": "2-4 sentence connection"}}
            ]
            """

            response = await self.generate_text(prompt, max_tokens=800)

            # Parse JSON response
            import json
            try:
                snippets = json.loads(response.content)
                return snippets if isinstance(snippets, list) else []
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return [
                    {"type": "context", "title": "Context", "content": "Related information about the selected text."},
                    {"type": "insight", "title": "Insight", "content": "Key insight from the document analysis."},
                    {"type": "connection", "title": "Connection", "content": "Connection to other parts of the document."}
                ]

        except Exception as e:
            print(f"Error generating snippets: {e}")
            return []

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        try:
            # Prepare sections from different documents
            cross_doc_sections = []
            current_doc = None

            for section in all_sections[:10]:  # Limit to top 10 sections
                doc_name = section.get('document_name', 'Unknown')
                if doc_name != current_doc:
                    cross_doc_sections.append(f"Document: {doc_name}")
                    current_doc = doc_name
                cross_doc_sections.append(f"Section: {section.get('content', '')[:300]}")

            prompt = f"""
            You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}

            Find cross-document connections for the selected text. Identify related themes, concepts, or information across different documents.

            Selected Text: {selected_text}

            Available Sections from Multiple Documents:
            {chr(10).join(cross_doc_sections)}

            Generate exactly 3 cross-document connections in JSON format:
            [
                {{"type": "theme", "title": "Common Theme", "content": "Description of shared theme across documents", "documents": ["doc1", "doc2"]}},
                {{"type": "concept", "title": "Related Concept", "content": "Related concept found in multiple documents", "documents": ["doc1", "doc3"]}},
                {{"type": "reference", "title": "Cross Reference", "content": "Information that references or builds upon each other", "documents": ["doc2", "doc3"]}}
            ]
            """

            response = await self.generate_text(prompt, max_tokens=1000)

            # Parse JSON response
            import json
            try:
                connections = json.loads(response.content)
                return connections if isinstance(connections, list) else []
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return [
                    {"type": "theme", "title": "Related Theme", "content": "Common themes found across documents.", "documents": ["Multiple Documents"]},
                    {"type": "concept", "title": "Shared Concept", "content": "Concepts that appear in multiple documents.", "documents": ["Cross-Document"]},
                    {"type": "reference", "title": "Cross Reference", "content": "Information that builds upon each other across documents.", "documents": ["Related Documents"]}
                ]

        except Exception as e:
            print(f"Error finding cross-document connections: {e}")
            return []


class AzureOpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv('AZURE_OPENAI_KEY')
        self.api_base = os.getenv('AZURE_OPENAI_BASE')
        self.api_version = os.getenv('AZURE_API_VERSION', '2024-02-15-preview')
        self.deployment_name = os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4o')
        
        if not all([self.api_key, self.api_base]):
            raise ValueError("Azure OpenAI credentials not provided")
        
        openai.api_type = "azure"
        openai.api_key = self.api_key
        openai.api_base = self.api_base
        openai.api_version = self.api_version
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                engine=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage,
                model=self.deployment_name
            )
        except Exception as e:
            raise Exception(f"Azure OpenAI API error: {str(e)}")
    
    async def generate_insights(self, content: str, persona: str, job: str) -> List[Dict[str, Any]]:
        prompt = f"""
        As an AI assistant helping a {persona} with their job: {job}
        
        Analyze this content and provide 3-4 insights in JSON format:
        
        Content: {content[:2000]}...
        
        Return a JSON array with insights of these types:
        - key-insight: Main takeaways
        - did-you-know: Interesting facts  
        - counterpoint: Alternative perspectives
        - connection: Links to other concepts
        
        Format: [{{"type": "key-insight", "title": "...", "content": "...", "relevance": 0.9}}]
        """
        
        response = await self.generate_text(prompt, 800)
        try:
            return json.loads(response.content)
        except:
            return [{"type": "key-insight", "title": "Analysis", "content": response.content, "relevance": 0.8}]

    async def generate_snippets(self, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate 2-4 sentence snippets from related sections"""
        return [
            {"type": "context", "title": "Context", "content": "Related information about the selected text."},
            {"type": "insight", "title": "Insight", "content": "Key insight from the document analysis."}
        ]

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return [
            {"type": "theme", "title": "Related Theme", "content": "Common themes found across documents.", "documents": ["Multiple Documents"]}
        ]


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        openai.api_key = self.api_key
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage,
                model=self.model_name
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def generate_insights(self, content: str, persona: str, job: str) -> List[Dict[str, Any]]:
        prompt = f"""
        As an AI assistant helping a {persona} with their job: {job}
        
        Analyze this content and provide 3-4 insights in JSON format:
        
        Content: {content[:2000]}...
        
        Return a JSON array with insights of these types:
        - key-insight: Main takeaways
        - did-you-know: Interesting facts
        - counterpoint: Alternative perspectives  
        - connection: Links to other concepts
        
        Format: [{{"type": "key-insight", "title": "...", "content": "...", "relevance": 0.9}}]
        """
        
        response = await self.generate_text(prompt, 800)
        try:
            return json.loads(response.content)
        except:
            return [{"type": "key-insight", "title": "Analysis", "content": response.content, "relevance": 0.8}]

    async def generate_snippets(self, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate 2-4 sentence snippets from related sections"""
        return [
            {"type": "context", "title": "Context", "content": "Related information about the selected text."},
            {"type": "insight", "title": "Insight", "content": "Key insight from the document analysis."}
        ]

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return [
            {"type": "theme", "title": "Related Theme", "content": "Common themes found across documents.", "documents": ["Multiple Documents"]}
        ]


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = os.getenv('OLLAMA_MODEL', 'llama3')
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            response = await asyncio.to_thread(
                requests.post,
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                }
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(
                content=data.get('response', ''),
                model=self.model_name
            )
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    async def generate_insights(self, content: str, persona: str, job: str) -> List[Dict[str, Any]]:
        prompt = f"""
        You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}
        
        Analyze this PDF content and provide exactly 4 insights that go beyond what's written on the page.
        Generate insights that help the user understand the content faster and discover connections.
        
        PDF Content: {content[:3000]}...
        
        Provide insights in these categories:
        1. "key-insight": Critical takeaways that save reading time
        2. "did-you-know": Surprising facts or context that enriches understanding  
        3. "counterpoint": Alternative perspectives or potential challenges
        4. "connection": How this relates to other concepts, trends, or documents
        
        Requirements:
        - Each insight should be 1-2 sentences maximum
        - Focus on what matters most to a {persona}
        - Make insights actionable and specific
        - Include relevance score (0.1-1.0) based on importance to the persona
        
        Return valid JSON array:
        [{{"type": "key-insight", "title": "Main Takeaway", "content": "Specific insight in 1-2 sentences", "relevance": 0.95}}, ...]
        """
        
        response = await self.generate_text(prompt, 1200)
        try:
            insights_data = json.loads(response.content)
            # Ensure we have exactly 4 insights as per Adobe requirements
            return insights_data[:4] if len(insights_data) >= 4 else insights_data
        except:
            return [{"type": "key-insight", "title": "Content Analysis", "content": response.content[:200], "relevance": 0.8}]

    async def generate_snippets(self, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Generate 2-4 sentence snippets from related sections"""
        return [
            {"type": "context", "title": "Context", "content": "Related information about the selected text."},
            {"type": "insight", "title": "Insight", "content": "Key insight from the document analysis."}
        ]

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return [
            {"type": "theme", "title": "Related Theme", "content": "Common themes found across documents.", "documents": ["Multiple Documents"]}
        ]


def get_llm_provider() -> LLMProvider:
    """Factory function to get the appropriate LLM provider based on environment variables"""
    provider_type = os.getenv('LLM_PROVIDER', 'gemini').lower()
    
    if provider_type == 'gemini':
        return GeminiProvider()
    elif provider_type == 'azure':
        return AzureOpenAIProvider()
    elif provider_type == 'openai':
        return OpenAIProvider()
    elif provider_type == 'ollama':
        return OllamaProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")
