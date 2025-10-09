"""
Minify credentials.json for Render Environment Variable
"""
import json
from pathlib import Path

# Read credentials.json
credentials_file = Path(__file__).parent / 'credentials.json'

if not credentials_file.exists():
    print("❌ credentials.json not found!")
    print(f"   Looking for: {credentials_file}")
    exit(1)

try:
    # Load JSON
    with open(credentials_file, 'r') as f:
        credentials = json.load(f)
    
    # Minify (no spaces, single line)
    minified = json.dumps(credentials, separators=(',', ':'))
    
    print("=" * 80)
    print("✅ CREDENTIALS MINIFIED SUCCESSFULLY!")
    print("=" * 80)
    print("\n📋 Copy this value and paste it into Render:\n")
    print("─" * 80)
    print(minified)
    print("─" * 80)
    print("\n📝 Instructions:")
    print("1. Copy the line above (everything between the dashes)")
    print("2. Go to Render Dashboard → Your Service → Environment tab")
    print("3. Add new environment variable:")
    print("   Key: GOOGLE_APPLICATION_CREDENTIALS_JSON")
    print("   Value: [paste the copied line]")
    print("4. Save changes and redeploy")
    print("\n✅ Done!")
    print("=" * 80)
    
    # Also save to a file for reference
    output_file = Path(__file__).parent / 'credentials_minified.txt'
    with open(output_file, 'w') as f:
        f.write(minified)
    
    print(f"\n💾 Also saved to: {output_file}")
    
except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON in credentials.json: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
