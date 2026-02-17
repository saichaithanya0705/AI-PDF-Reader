import requests
import os
import time
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# User credentials
email = "ysaichaaithu2005@gmail.com"
password = "Sai@752005"

user_id = None

try:
    print("Fetching a valid user ID via Admin API...")
    # Use admin API to list users (requires service role key)
    users_response = supabase.auth.admin.list_users()
    if isinstance(users_response, list) and len(users_response) > 0:
        user_id = users_response[0].id
        print(f"✅ Found valid User ID: {user_id}")
    elif hasattr(users_response, 'users') and users_response.users:
        user_id = users_response.users[0].id
        print(f"✅ Found valid User ID: {user_id}")
    else:
        print("❌ No users found in Supabase auth.users")
        exit(1)
except Exception as e:
    print(f"❌ Failed to fetch users: {e}")
    exit(1)

# Create a dummy PDF
pdf_content = b"%PDF-1.4\n%Test PDF Content"
with open("test.pdf", "wb") as f:
    f.write(pdf_content)

url = f"http://localhost:8000/upload/active_file?client_id={user_id}"
files = {'file': ('test.pdf', open('test.pdf', 'rb'), 'application/pdf')}

print(f"Sending request to {url}...")

try:
    # Retry logic in case server is still starting
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.post(url, files=files)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200 or response.status_code == 202:
                print("✅ Upload successful!")
                break
            else:
                print("❌ Upload failed!")
                break
        except requests.exceptions.ConnectionError:
            print(f"Connection failed, retrying ({i+1}/{max_retries})...")
            time.sleep(2)
    else:
        print("❌ Could not connect to server after retries.")

except Exception as e:
    print(f"Error: {e}")
finally:
    files['file'][1].close()
    if os.path.exists("test.pdf"):
        os.remove("test.pdf")
