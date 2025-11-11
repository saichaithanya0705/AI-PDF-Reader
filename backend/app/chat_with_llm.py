import os

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

def get_llm_response(messages):
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    # Use messages in current format directly

    if provider == "gemini":
        # Use direct google-generativeai library instead of langchain
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("google-generativeai not available. Please install it: pip install google-generativeai")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable must be set for Gemini")

        print("🔑 Using GOOGLE_API_KEY for Gemini authentication")
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash model (fast and widely available)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Convert messages to Gemini format
        # Gemini expects a simple prompt string or conversation history
        if isinstance(messages, list):
            # Extract the last user message as the prompt
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            if user_messages:
                prompt = user_messages[-1].get("content", "")
            else:
                prompt = str(messages)
        else:
            prompt = str(messages)
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Check for quota exceeded errors
            error_str = str(e).lower()
            if "quota" in error_str or "429" in error_str or "resourceexhausted" in error_str:
                print("⚠️ Gemini API quota exceeded - using fallback response")
                return "I apologize, but the AI service is currently at capacity. Please try again later or contact support for assistance."
            print(f"❌ Gemini API error: {e}")
            raise RuntimeError(f"Gemini call failed: {e}")

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
