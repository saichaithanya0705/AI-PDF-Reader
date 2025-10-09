# 🔐 How to Add credentials.json to Render

## 📋 Quick Answer

**Don't upload the file!** Use environment variables instead (more secure).

---

## ✅ **RECOMMENDED METHOD: Environment Variable**

### **Step 1: Prepare Your Credentials**

1. **Open** `credentials.json` (you have it selected)
2. **Copy the ENTIRE content** - from `{` to `}` including everything
3. **Minify it** (remove all line breaks) - make it one single line

**Original (multi-line):**
```json
{
  "type": "service_account",
  "project_id": "adobe-hackathon-468510",
  ...
}
```

**Minified (single line):**
```json
{"type":"service_account","project_id":"adobe-hackathon-468510",...}
```

### **Step 2: Add to Render**

1. Go to your Render service dashboard
2. Click **"Environment"** tab (left sidebar)
3. Click **"Add Environment Variable"**
4. Fill in:
   ```
   Key: GOOGLE_APPLICATION_CREDENTIALS_JSON
   Value: [paste the minified JSON here]
   ```
5. Click **"Save Changes"**
6. Service will automatically redeploy

### **Step 3: Verify**

After deployment:
1. Check logs for: `✅ Google credentials are configured!`
2. Test your service endpoints

---

## 🔧 **I've Already Set This Up For You!**

I added a `setup_credentials.py` script that:
- ✅ Reads `GOOGLE_APPLICATION_CREDENTIALS_JSON` from environment
- ✅ Creates a temporary file on Render
- ✅ Sets `GOOGLE_APPLICATION_CREDENTIALS` automatically
- ✅ Called automatically when your app starts

---

## 📝 **Complete Environment Variables for Render**

Add all these to your Render service:

### **Required:**
```
PYTHON_VERSION=3.11
GEMINI_API_KEY=your_gemini_api_key
```

### **For Google Cloud TTS (if using):**
```
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"adobe-hackathon-468510",...}
```

**OR use API key instead:**
```
GOOGLE_API_KEY=your_google_api_key
```

### **Optional:**
```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
LLM_PROVIDER=gemini
```

---

## 🎯 **Which One to Use?**

Your code supports **3 options** (in priority order):

### **Option 1: GEMINI_API_KEY (Simplest)** ⭐ **RECOMMENDED**
```
Key: GEMINI_API_KEY
Value: AIza...your_key_here
```
- ✅ Easiest to setup
- ✅ No credentials.json needed
- ✅ Good for Gemini models

### **Option 2: GOOGLE_APPLICATION_CREDENTIALS_JSON (Service Account)**
```
Key: GOOGLE_APPLICATION_CREDENTIALS_JSON
Value: {"type":"service_account",...entire JSON...}
```
- ✅ More features (TTS, Vertex AI)
- ✅ Better for production
- ⚠️ Longer to setup

### **Option 3: Both (Full Features)**
```
GEMINI_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS_JSON={...json...}
```
- ✅ All features enabled
- ✅ Fallback options

---

## 🚀 **Quick Deploy Checklist**

Before deploying to Render:

### **Minimal Setup (Just Chat):**
```
✓ PYTHON_VERSION=3.11
✓ GEMINI_API_KEY=your_key
```

### **Full Setup (All Features):**
```
✓ PYTHON_VERSION=3.11
✓ GEMINI_API_KEY=your_key
✓ GOOGLE_APPLICATION_CREDENTIALS_JSON={...json...}
✓ AZURE_SPEECH_KEY=your_key (if using Azure TTS)
```

---

## 📖 **How to Minify JSON**

### **Method 1: Manual**
Copy JSON → Remove all line breaks → Remove extra spaces

### **Method 2: Online Tool**
1. Go to: https://www.jsonformatter.org/jsonminifier
2. Paste your JSON
3. Click "Minify"
4. Copy result

### **Method 3: Python Script**
```python
import json

with open('credentials.json', 'r') as f:
    data = json.load(f)

minified = json.dumps(data, separators=(',', ':'))
print(minified)
```

### **Method 4: Command Line**
```bash
# PowerShell
$json = Get-Content credentials.json | ConvertFrom-Json
$json | ConvertTo-Json -Compress
```

---

## ⚠️ **Security Notes**

### **DO:**
✅ Use environment variables on Render
✅ Add credentials.json to .gitignore (already done)
✅ Never commit credentials.json to GitHub
✅ Use different credentials for dev/prod

### **DON'T:**
❌ Upload credentials.json to GitHub
❌ Share credentials in public places
❌ Hardcode credentials in code
❌ Use same credentials everywhere

---

## 🐛 **Troubleshooting**

### **Error: "Could not authenticate"**
**Cause:** Credentials not found
**Fix:** 
1. Check environment variable name: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
2. Verify JSON is valid (use jsonlint.com)
3. Make sure it's minified (no line breaks)

### **Error: "Invalid JSON"**
**Cause:** JSON has syntax errors
**Fix:**
1. Re-copy from original file
2. Use JSON validator before minifying
3. Don't escape quotes manually

### **Error: "File not found"**
**Cause:** Using file path instead of JSON content
**Fix:** 
- Use `GOOGLE_APPLICATION_CREDENTIALS_JSON` (with JSON content)
- NOT `GOOGLE_APPLICATION_CREDENTIALS` (file path doesn't work on Render)

---

## 🎯 **What I Changed in Your Code**

### **Added:**
1. **`backend/setup_credentials.py`** - Handles credentials on Render
2. **Updated `backend/app/main.py`** - Calls setup script on startup

### **How It Works:**
```
1. App starts
2. setup_credentials.py runs
3. Checks for GOOGLE_APPLICATION_CREDENTIALS_JSON env var
4. Creates temp file with credentials
5. Sets GOOGLE_APPLICATION_CREDENTIALS to temp file path
6. Your existing code uses it automatically
```

---

## ✨ **Summary**

**For Render Deployment:**

1. **Minify** your `credentials.json` to one line
2. **Add environment variable** in Render:
   ```
   GOOGLE_APPLICATION_CREDENTIALS_JSON={minified json}
   ```
3. **Deploy** - credentials will be automatically set up
4. **Done!** ✅

**OR Simpler:**

1. Just use `GEMINI_API_KEY` if you don't need Google Cloud TTS
2. Your app will work fine with just Gemini API key

---

## 📝 **Next Steps**

1. ✅ Code changes pushed to GitHub (setup_credentials.py added)
2. ⏭️ Minify your credentials.json
3. ⏭️ Add to Render as environment variable
4. ⏭️ Deploy!

---

🎉 **You're all set!** The code automatically handles credentials now.
