import sys
import os

print(f"Python executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")

try:
    import google.generativeai as genai
    print(f"SUCCESS: google-generativeai imported. Version: {genai.__version__}")
except ImportError as e:
    print(f"FAILURE: Could not import google.generativeai. Error: {e}")
except Exception as e:
    print(f"FAILURE: Unexpected error. Error: {e}")
