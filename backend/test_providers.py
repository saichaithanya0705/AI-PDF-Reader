
import os
import asyncio
from dotenv import load_dotenv
from app.llm_providers import GeminiProvider

load_dotenv()

async def test_gemini():
    print("Testing GeminiProvider...")
    
    # Test 1: Standard Init
    try:
        provider = GeminiProvider()
        print(f"Primary model: {provider.model_name}")
        print(f"Fallback model: {os.getenv('ANTHROPIC_MODEL', 'Not set')}")
        
        prompt = "Hello, who are you?"
        print(f"Generating text with prompt: '{prompt}'")
        
        # Add timeout
        response = await asyncio.wait_for(provider.generate_text(prompt), timeout=10.0)
        
        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")
    except asyncio.TimeoutError:
        print("❌ Test failed: Timeout after 10s")
    except Exception as e:
        print(f"Test failed with error: {e}")

    # Test 2: Force Fallback
    print("\nTesting Fallback...")
    try:
        # Mess up the primary model to force failure
        if provider.model:
            provider.model = None # Simulating init failure or runtime failure logic? 
            # modifying provider.model to None triggers 'Gemini model not initialized' which triggers fallback
        
        print(f"Generating text (fallback expected)...")
        response = await asyncio.wait_for(provider.generate_text(prompt), timeout=10.0)
        
        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")
        
        if "claude" in response.model:
            print("✅ Fallback successful!")
        else:
            print(f"⚠️ Unexpected model used: {response.model}")
            
    except asyncio.TimeoutError:
         print("❌ Fallback Test failed: Timeout after 10s")
    except Exception as e:
        print(f"Fallback Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
