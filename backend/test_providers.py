"""
Manual LLM provider smoke probe.

Run with:
    python backend/test_providers.py
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


async def run_gemini_probe():
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from app.llm_providers import GeminiProvider

    print("Testing GeminiProvider...")

    try:
        provider = GeminiProvider()
        print(f"Primary model: {provider.model_name}")
        print(f"Fallback model: {os.getenv('ANTHROPIC_MODEL', 'Not set')}")

        prompt = "Hello, who are you?"
        print(f"Generating text with prompt: {prompt!r}")

        response = await asyncio.wait_for(provider.generate_text(prompt), timeout=10.0)

        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")
    except asyncio.TimeoutError:
        print("Test failed: Timeout after 10s")
    except Exception as exc:
        print(f"Test failed with error: {exc}")
        return

    print("\nTesting fallback...")
    try:
        if provider.model:
            provider.model = None

        print("Generating text with fallback expected...")
        response = await asyncio.wait_for(provider.generate_text(prompt), timeout=10.0)

        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")

        if "claude" in response.model:
            print("Fallback successful.")
        else:
            print(f"Unexpected model used: {response.model}")

    except asyncio.TimeoutError:
        print("Fallback test failed: Timeout after 10s")
    except Exception as exc:
        print(f"Fallback test failed with error: {exc}")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(run_gemini_probe())
