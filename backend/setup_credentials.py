"""
Render Credentials Setup Script
Handles Google Cloud credentials from environment variable on Render
"""
import os
import json
import tempfile
from pathlib import Path


def setup_google_credentials():
    """
    Setup Google Application Credentials for Render deployment
    
    This script checks for credentials in the following order:
    1. GOOGLE_APPLICATION_CREDENTIALS_JSON (env var with full JSON)
    2. GOOGLE_APPLICATION_CREDENTIALS (path to credentials file)
    3. credentials.json in project root
    """
    
    # Option 1: JSON content in environment variable (Recommended for Render)
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    
    if credentials_json:
        print("🔐 Found GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable")
        try:
            # Parse to validate JSON
            credentials_dict = json.loads(credentials_json)
            
            # Create temporary file (Render has ephemeral filesystem)
            temp_dir = Path(tempfile.gettempdir())
            credentials_path = temp_dir / 'google_credentials.json'
            
            # Write credentials to temp file
            with open(credentials_path, 'w') as f:
                json.dump(credentials_dict, f)
            
            # Set environment variable to point to temp file
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            
            print(f"✅ Google credentials written to: {credentials_path}")
            print(f"✅ GOOGLE_APPLICATION_CREDENTIALS set to: {credentials_path}")
            
            return str(credentials_path)
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
            return None
    
    # Option 2: Path to credentials file
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path and Path(credentials_path).exists():
        print(f"✅ Using existing credentials from: {credentials_path}")
        return credentials_path
    
    # Option 3: Check project root for credentials.json
    project_root = Path(__file__).parent.parent.parent
    local_credentials = project_root / 'credentials.json'
    
    if local_credentials.exists():
        print(f"✅ Using credentials.json from project root: {local_credentials}")
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(local_credentials)
        return str(local_credentials)
    
    # No credentials found
    print("⚠️  No Google Cloud credentials found!")
    print("    To fix this on Render:")
    print("    1. Add environment variable: GOOGLE_APPLICATION_CREDENTIALS_JSON")
    print("    2. Set value to your entire credentials.json content")
    print("    3. Redeploy your service")
    
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("Google Cloud Credentials Setup for Render")
    print("=" * 60)
    
    credentials_path = setup_google_credentials()
    
    if credentials_path:
        print("\n✅ SUCCESS: Google credentials are configured!")
        print(f"   Path: {credentials_path}")
    else:
        print("\n❌ FAILED: Could not setup Google credentials")
        print("   Some features may not work without credentials")
    
    print("=" * 60)
