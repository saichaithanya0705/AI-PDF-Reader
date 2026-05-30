"""
Enhanced LLM Provider for Adobe Hackathon - Integrates provided chat_with_llm.py
Supports multiple LLM providers: Gemini, Azure OpenAI, OpenAI, Ollama
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import requests
from pydantic import BaseModel

try:
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:  # pragma: no cover - optional provider dependency
    init_chat_model = None
    HumanMessage = None
    SystemMessage = None

try:
    from openai import AsyncAzureOpenAI, AsyncOpenAI
except ImportError:  # pragma: no cover - only relevant for unsupported SDKs
    AsyncAzureOpenAI = None
    AsyncOpenAI = None

# Lazy imports for optional providers
genai = None
vertexai = None
GenerativeModel = None
anthropic = None


class LLMResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str


def _usage_to_dict(usage: Any) -> Optional[Dict[str, Any]]:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if hasattr(usage, "dict"):
        return usage.dict()
    return {
        key: getattr(usage, key)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if hasattr(usage, key)
    } or None


def _chat_completion_content(response: Any) -> str:
    choice = response.choices[0]
    message = choice.message
    if isinstance(message, dict):
        return message.get("content") or ""
    return getattr(message, "content", None) or ""


def _parse_json_list(content: str) -> List[Dict[str, Any]]:
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    try:
        payload = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


async def _generate_snippets_with_model(provider, selected_text: str, related_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
    sections_content = [
        f"Section: {section.get('content', '')[:500]}"
        for section in related_sections[:5]
    ]
    prompt = f"""
You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}

Based on the selected text and related sections, generate 2-4 concise, informative snippets.
Each snippet must be grounded in the supplied selected text or related sections.

Selected Text: {selected_text}

Related Sections:
{chr(10).join(sections_content)}

Return ONLY valid JSON:
[
  {{"type": "context", "title": "Context Title", "content": "2-4 sentence grounded explanation"}},
  {{"type": "insight", "title": "Key Insight", "content": "2-4 sentence grounded insight"}}
]
"""
    response = await provider.generate_text(prompt, max_tokens=800)
    return _parse_json_list(response.content)


async def _find_connections_with_model(provider, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
    section_lines = []
    current_doc = None
    for section in all_sections[:10]:
        doc_name = section.get('document_name', 'Unknown')
        if doc_name != current_doc:
            section_lines.append(f"Document: {doc_name}")
            current_doc = doc_name
        section_lines.append(f"Section: {section.get('content', '')[:300]}")

    prompt = f"""
You are an AI assistant for Adobe's PDF Intelligence System helping a {persona} with: {job}

Find cross-document connections for the selected text using only the supplied sections.

Selected Text: {selected_text}

Available Sections:
{chr(10).join(section_lines)}

Return ONLY valid JSON:
[
  {{"type": "theme", "title": "Common Theme", "content": "Grounded description", "documents": ["doc1", "doc2"]}}
]
"""
    response = await provider.generate_text(prompt, max_tokens=1000)
    return _parse_json_list(response.content)


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

    @abstractmethod
    async def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a chat response from a list of messages (role, content)"""
        pass

    
    # Removed separate AnthropicProvider class as it's now handled by LangChain fallback logic above



class GeminiProvider(LLMProvider):
    def __init__(self):
        # Initialize primary model (Gemini) via LangChain with explicit API key
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.api_key = os.getenv('GOOGLE_API_KEY')

        try:
            if self.api_key:
                # Use ChatGoogleGenerativeAI directly with API key
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.model = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.7
                )
                print(f"✅ Gemini initialized via LangChain: {self.model_name}")
            else:
                print("⚠️ GOOGLE_API_KEY not set, Gemini will not be available")
                self.model = None
        except Exception as e:
            print(f"⚠️ Gemini initialization failed: {e}")
            self.model = None

        # Initialize fallback provider (Anthropic) via LangChain
        self.fallback_model = None
        if os.getenv('ANTHROPIC_API_KEY') and init_chat_model is not None:
            try:
                fallback_name = os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
                self.fallback_model = init_chat_model(fallback_name, model_provider="anthropic")
                print(f"✅ Fallback provider (Anthropic) initialized: {fallback_name}")
            except Exception as e:
                print(f"⚠️ Failed to initialize fallback provider: {e}")
        elif os.getenv('ANTHROPIC_API_KEY'):
            print("⚠️ LangChain is not installed, Anthropic fallback will not be available")

        # Keep raw imports for PDF-specific multimodal features if needed
        # (Legacy support for generate_insights_from_pdf)
        global genai
        try:
            import google.generativeai as genai
            self.raw_genai = genai
            # Use GOOGLE_API_KEY directly instead of credentials file
            if self.api_key:
                genai.configure(api_key=self.api_key)
        except:
            self.raw_genai = None

    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            # Try primary model
            if self.model:
                response = await self.model.ainvoke(prompt)
                return LLMResponse(
                    content=str(response.content),
                    model=self.model_name
                )
            else:
                raise Exception("Gemini model not initialized")
        except Exception as e:
            # Try fallback
            if self.fallback_model:
                print(f"❌ Gemini error: {e}. 🔄 Trying fallback to Anthropic...")
                response = await self.fallback_model.ainvoke(prompt)
                return LLMResponse(
                    content=str(response.content),
                    model=os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku')
                )
            
            print(f"❌ LLM API error: {e}")
            raise Exception(f"All LLM providers failed: {str(e)}")

    async def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response handling either list of dicts or LangChain messages"""
        try:
            # Convert dict messages to LangChain messages if needed
            langchain_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    if HumanMessage is None or SystemMessage is None:
                        langchain_messages.append(msg)
                        continue
                    if msg.get("role") == "user":
                        langchain_messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "system":
                        langchain_messages.append(SystemMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        # LangChain doesn't have a simple "AssistantMessage" alias in core but AIMessage exists
                        try:
                            from langchain_core.messages import AIMessage
                            langchain_messages.append(AIMessage(content=msg.get("content", "")))
                        except ImportError:
                            langchain_messages.append(msg)
                else:
                    # Assume it's already a LangChain message/object
                    langchain_messages.append(msg)

            # Try primary model
            if self.model:
                response = await self.model.ainvoke(langchain_messages)
                return str(response.content)
            else:
                raise Exception("Gemini model not initialized")
                
        except Exception as e:
            # Try fallback
            if self.fallback_model:
                print(f"❌ Gemini chat error: {e}. 🔄 Trying fallback to Anthropic...")
                # Fallback needs string or messages. Anthropic via LangChain supports messages.
                try:
                    response = await self.fallback_model.ainvoke(langchain_messages)
                    return str(response.content)
                except Exception as fallback_error:
                    print(f"❌ Fallback failed: {fallback_error}")
                    raise fallback_error
            
            print(f"❌ LLM API error: {e}")
            raise Exception(f"All LLM providers failed: {str(e)}")

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
        
        try:
            response = await self.generate_text(prompt, 1200)
            try:
                insights_data = json.loads(response.content)
                # Ensure we have exactly 4 insights as per Adobe requirements
                return insights_data[:4] if len(insights_data) >= 4 else insights_data
            except:
                return [{"type": "key-insight", "title": "Analysis", "content": response.content, "relevance": 0.8}]
        except Exception as e:
            print(f"❌ Gemini insight generation failed after configured fallbacks: {e}")
            raise e

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
                return []

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
                return []

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

        if AsyncAzureOpenAI is None:
            raise ValueError("OpenAI Python SDK 1.x with AsyncAzureOpenAI is required")

        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.api_base,
            api_version=self.api_version,
        )
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return LLMResponse(
                content=_chat_completion_content(response),
                usage=_usage_to_dict(getattr(response, "usage", None)),
                model=self.deployment_name
            )
        except Exception as e:
            raise Exception(f"Azure OpenAI API error: {str(e)}")

    async def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
            )
            return _chat_completion_content(response)
        except Exception as e:
            raise Exception(f"Azure OpenAI chat API error: {str(e)}")
    
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
        return await _generate_snippets_with_model(self, selected_text, related_sections, persona, job)

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return await _find_connections_with_model(self, selected_text, all_sections, persona, job)


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        if AsyncOpenAI is None:
            raise ValueError("OpenAI Python SDK 1.x with AsyncOpenAI is required")

        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return LLMResponse(
                content=_chat_completion_content(response),
                usage=_usage_to_dict(getattr(response, "usage", None)),
                model=self.model_name
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )
            return _chat_completion_content(response)
        except Exception as e:
            raise Exception(f"OpenAI chat API error: {str(e)}")
    
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
        return await _generate_snippets_with_model(self, selected_text, related_sections, persona, job)

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return await _find_connections_with_model(self, selected_text, all_sections, persona, job)


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

    async def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        prompt = "\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in messages
        )
        response = await self.generate_text(prompt, max_tokens=1000)
        return response.content
    
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
        return await _generate_snippets_with_model(self, selected_text, related_sections, persona, job)

    async def find_cross_document_connections(self, selected_text: str, all_sections: List[Dict], persona: str, job: str) -> List[Dict[str, Any]]:
        """Find semantically related sections across documents"""
        return await _find_connections_with_model(self, selected_text, all_sections, persona, job)


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
