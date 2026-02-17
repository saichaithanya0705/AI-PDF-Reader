import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8001"

def test_memory():
    print("[TEST 1] Chatbot Memory", flush=True)
    history = []
    
    # Message 1
    msg1 = "Hello, my secret code is 9988."
    payload1 = {
        "message": msg1,
        "context_type": "library",
        "conversation_history": history
    }
    print(f"User: {msg1}", flush=True)
    try:
        # Timeout is crucial to fail fast if hung
        r1 = requests.post(f"{BASE_URL}/api/chat", json=payload1, timeout=10)
        if r1.status_code != 200:
            print(f"❌ Msg 1 Failed: {r1.status_code} - {r1.text}", flush=True)
            return False
            
        resp1 = r1.json().get("response", "")
        print(f"Assistant: {resp1}", flush=True)
        
        session_id = r1.json().get("session_id")
        
        # Update History
        history.append({"role": "user", "content": msg1})
        history.append({"role": "assistant", "content": resp1})
        
        # Message 2
        msg2 = "What is the secret code I just told you?"
        payload2 = {
            "message": msg2,
            "context_type": "library",
            "conversation_history": history,
            "session_id": session_id
        }
        print(f"User: {msg2}", flush=True)
        r2 = requests.post(f"{BASE_URL}/api/chat", json=payload2, timeout=10)
        resp2 = r2.json().get("response", "")
        print(f"Assistant: {resp2}", flush=True)
        
        if "9988" in resp2:
            print("✅ TEST PASSED: Memory working.", flush=True)
            return True
        else:
            print("❌ TEST FAILED: Memory not working.", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)
        return False

if __name__ == "__main__":
    test_memory()
