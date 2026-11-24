import logging
import os

import requests

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_CHAT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_CHAT_MODEL = "nvidia/nemotron-3.5-bolt-e4b"

# Try to import langchain components, fallback if not available
try:
    from langchain_openai import ChatOpenAI, AzureChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False
    print("⚠️ langchain-openai not available")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GOOGLE_AVAILABLE = True
except (ImportError, Exception) as e:
    LANGCHAIN_GOOGLE_AVAILABLE = False
    print(f"⚠️ langchain-google-genai not available: {e}")

# Don't import langchain_community for now to avoid installation issues
# from langchain_community.chat_models import ChatOllama
LANGCHAIN_COMMUNITY_AVAILABLE = False

# Python libraries to be installed: langchain, langchain-openai, langchain-google-genai, langchain-community

"""
LLM Chat Interface with Multi-Provider Support

This module provides a unified interface for chatting with various LLM providers
including Google Gemini, Azure OpenAI, OpenAI, and Ollama.

SETUP:
Users are expected to set appropriate environment variables for their chosen LLM provider
before calling the get_llm_response function.

Environment Variables:

LLM_PROVIDER (default: "gemini")
    - "gemini": Google Gemini (default)
    - "azure": Azure OpenAI
    - "openai": OpenAI API
    - "ollama": Local Ollama models

For Gemini (Google Generative AI):
    Authentication (in priority order):
    1. GOOGLE_API_KEY: Your Google API key (highest priority)
    2. GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON file
    3. credentials.json: Place in project root directory (automatic detection)

    GEMINI_MODEL (default: "gemini-2.5-flash"): Model name to use

For Azure OpenAI:
    AZURE_OPENAI_KEY: Your Azure OpenAI API key
    AZURE_OPENAI_BASE: Azure OpenAI endpoint URL
    AZURE_API_VERSION: API version (e.g., "2024-02-15-preview")
    AZURE_DEPLOYMENT_NAME (default: "gpt-4o"): Deployment name

For OpenAI:
    OPENAI_API_KEY: Your OpenAI API key
    OPENAI_API_BASE (default: "https://api.openai.com/v1"): API base URL
    OPENAI_MODEL (default: "gpt-4o"): Model name

For Ollama:
    OLLAMA_BASE_URL (default: "http://localhost:11434"): Ollama server URL
    OLLAMA_MODEL (default: "llama3"): Model name

Usage:
    # Set your environment variables first, then use the function
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    response = get_llm_response(messages)
"""

def _is_nvidia_fallback_enabled() -> bool:
    api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    disabled = os.getenv("DISABLE_NVIDIA_LLM_FALLBACK", "").strip().lower() in ("1", "true", "yes")
    return bool(api_key) and not disabled


def _normalize_chat_messages(messages):
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    normalized = []
    for msg in messages or []:
        if isinstance(msg, dict):
            role = str(msg.get("role") or "user")
            content = str(msg.get("content") or "")
        else:
            role = str(getattr(msg, "role", "user") or "user")
            content = str(getattr(msg, "content", msg) or "")
        normalized.append({"role": role, "content": content})
    return normalized


def _call_nvidia_chat(messages, max_tokens: int = 1600, temperature: float = 0.4) -> str:
    api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("NVIDIA_API_KEY environment variable must be set for NVIDIA chat")

    base_url = (os.getenv("NVIDIA_CHAT_BASE_URL") or DEFAULT_NVIDIA_CHAT_BASE_URL).strip().rstrip("/")
    model_name = (os.getenv("NVIDIA_CHAT_MODEL") or DEFAULT_NVIDIA_CHAT_MODEL).strip()
    normalized = _normalize_chat_messages(messages)

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": normalized,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("NVIDIA chat endpoint returned no choices")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("NVIDIA chat endpoint returned empty content")
    return content.strip()


def get_llm_response(messages):
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "nvidia":
        return _call_nvidia_chat(messages)

    if provider == "gemini":
        # Use direct google-generativeai library instead of langchain
        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions
        except ImportError as exc:
            if _is_nvidia_fallback_enabled():
                logger.warning("google-generativeai missing; falling back to NVIDIA NIM chat")
                return _call_nvidia_chat(messages)
            raise RuntimeError("google-generativeai not available. Please install it: pip install google-generativeai") from exc

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            if _is_nvidia_fallback_enabled():
                logger.warning("GOOGLE_API_KEY not set; falling back to NVIDIA NIM chat")
                return _call_nvidia_chat(messages)
            raise ValueError("GOOGLE_API_KEY environment variable must be set for Gemini")

        # Configure the API
        genai.configure(api_key=api_key)
        
        # Prepare system instruction and chat history
        system_instruction = None
        chat_history = []
        user_message_part = ""

        if isinstance(messages, list):
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                
                if role == "system":
                    # Accumulate system instructions
                    if system_instruction is None:
                        system_instruction = content
                    else:
                        system_instruction += f"\n\n{content}"
                elif role == "user":
                    chat_history.append({"role": "user", "parts": [content]})
                    user_message_part = content # Track last user message for fallback/logging
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
        else:
            # Handle string input (simple prompt)
            user_message_part = str(messages)
            chat_history.append({"role": "user", "parts": [user_message_part]})

        # Initialize model with system instruction if present
        model_name = os.getenv("GEMINI_MODEL", 'gemini-2.5-flash')
        try:
            if system_instruction:
                model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            else:
                model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"⚠️ Error initializing Gemini model with system instruction: {e}")
            # Fallback without system instruction (should satisfy older SDKs/models)
            model = genai.GenerativeModel(model_name)
            if system_instruction:
                 # Prepend to first user message if possible, or just add as user message
                 chat_history.insert(0, {"role": "user", "parts": [f"System Instruction: {system_instruction}"]})
                 chat_history.insert(1, {"role": "model", "parts": ["Understood."]})

        try:
            response = model.generate_content(chat_history)
            return response.text
            
        except google_exceptions.ResourceExhausted as e:
            print("⚠️ Gemini API quota exceeded (ResourceExhausted)")
            if _is_nvidia_fallback_enabled():
                logger.warning("Gemini quota exceeded; falling back to NVIDIA NIM chat")
                return _call_nvidia_chat(messages)
            raise RuntimeError("AI service is currently at capacity (Quota Exceeded).") from e
        except google_exceptions.InvalidArgument as e:
            print(f"❌ Gemini API InvalidArgument: {e}")
            if _is_nvidia_fallback_enabled():
                logger.warning("Gemini request rejected; falling back to NVIDIA NIM chat")
                return _call_nvidia_chat(messages)
            raise RuntimeError(f"Gemini request rejected: {e}") from e
        except Exception as e:
            if _is_nvidia_fallback_enabled():
                logger.warning("Gemini error (%s); falling back to NVIDIA NIM chat", type(e).__name__)
                return _call_nvidia_chat(messages)
            error_str = str(e).lower()
            if "quota" in error_str or "429" in error_str or "resourceexhausted" in error_str:
                print("⚠️ Gemini API quota exceeded")
                raise RuntimeError("AI service is currently at capacity (Quota Exceeded).") from e
            print(f"❌ Gemini API error: {e}")
            raise RuntimeError(f"Gemini call failed: {e}") from e

    elif provider == "azure":
        if not LANGCHAIN_OPENAI_AVAILABLE:
            raise RuntimeError("langchain-openai not available. Please install it to use Azure OpenAI.")

        api_key = os.getenv("AZURE_OPENAI_KEY")
        api_base = os.getenv("AZURE_OPENAI_BASE")
        api_version = os.getenv("AZURE_API_VERSION")
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

        if not all([api_key, api_base, api_version]):
            raise ValueError("Missing one of AZURE_OPENAI_KEY, AZURE_OPENAI_BASE, or AZURE_API_VERSION.")

        llm = AzureChatOpenAI(
            azure_deployment=deployment_name,
            openai_api_version=api_version,
            azure_endpoint=api_base,
            api_key=api_key,
            temperature=0.7
        )

        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"Azure OpenAI call failed: {e}")

    elif provider == "openai":
        if not LANGCHAIN_OPENAI_AVAILABLE:
            raise RuntimeError("langchain-openai not available. Please install it to use OpenAI.")

        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=api_base,
            temperature=0.7
        )

        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}")

    elif provider == "ollama":
        if not LANGCHAIN_COMMUNITY_AVAILABLE:
            raise RuntimeError("langchain-community not available. Please install it to use Ollama.")

        # Ollama functionality disabled for now due to missing langchain-community
        raise RuntimeError("Ollama provider is temporarily disabled. Please use 'gemini', 'azure', or 'openai' instead.")

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]

    try:
        reply = get_llm_response(messages)
        print("LLM Response:", reply)
    except Exception as e:
        print("Error:", str(e))
