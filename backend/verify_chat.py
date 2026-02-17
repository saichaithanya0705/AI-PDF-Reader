import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8080"
# Get Supabase URL and Key from .env if needed, but chat API might be public or rely on mocked user
# The backend uses get_optional_user which defaults to 'anonymous' if no token.

def verify_chat():
    print("💬 Verifying Chat API...")
    
    url = f"{API_URL}/api/chat"
    
    payload = {
        "message": "What does my library contain",
        "context_type": "library",
        "conversation_history": []
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Chat Request Successful!")
                print(f"🤖 Response: {data.get('response')[:200]}...")
                return True
            else:
                print(f"❌ Chat Success False: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    verify_chat()
