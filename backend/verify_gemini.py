import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key found: {bool(api_key)}")

genai.configure(api_key=api_key)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")

print("\nTesting generation with gemini-1.5-flash...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error with gemini-1.5-flash: {e}")

print("\nTesting generation with models/gemini-1.5-flash...")
try:
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    response = model.generate_content("Hello")
    print(f"Response (with prefix): {response.text}")
except Exception as e:
    print(f"Error with models/gemini-1.5-flash: {e}")
