# 🚀 AZURE WEB APP DEPLOYMENT GUIDE - BACKEND ONLY

## 📋 **QUICK OVERVIEW**

**Your Backend:**
- Framework: FastAPI + Python 3.11
- Entry Point: `backend.app.main:app`
- Port: Uses Azure's `$PORT` environment variable (default 8080)
- Start Command: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Dependencies: `backend/requirements.txt`

**Frontend:**
- Deploy separately on Netlify (you'll handle this)

---

## 🎯 **AZURE DEPLOYMENT STEPS**

### **STEP 1: Create Azure Web App**

1. **Go to Azure Portal**: https://portal.azure.com
2. **Click**: "Create a resource"
3. **Search for**: "Web App"
4. **Click**: "Create"

### **STEP 2: Configure Basic Settings**

```
Subscription:          [Your subscription]
Resource Group:        Create new: "adobe-hackathon-rg"
Name:                  adobe-hackathon-backend
                       (will be: adobe-hackathon-backend.azurewebsites.net)
Publish:               Code ✅
Runtime stack:         Python 3.11
Operating System:      Linux ✅
Region:                East US (or closest to you)
```

### **STEP 3: Choose Pricing Tier**

```
Linux Plan:            Create new: "adobe-hackathon-plan"
Sku and size:          Basic B1
                       (₹1,329.60/month)
                       OR
                       Free F1 (for testing only)
```

### **STEP 4: Review + Create**

1. Click **"Review + create"**
2. Wait for validation
3. Click **"Create"**
4. Wait 2-3 minutes for deployment

---

## ⚙️ **CONFIGURE YOUR WEB APP**

After creation, go to your Web App → **Configuration**

### **Application Settings (Environment Variables)**

Click **"New application setting"** for EACH of these:

#### **Required Variables:**
```
Name: PYTHON_VERSION
Value: 3.11

Name: GEMINI_API_KEY
Value: [your_gemini_api_key]

Name: SCM_DO_BUILD_DURING_DEPLOYMENT
Value: true

Name: WEBSITE_HTTPLOGGING_RETENTION_DAYS
Value: 7
```

#### **Google Cloud Credentials (Optional):**
```
Name: GOOGLE_APPLICATION_CREDENTIALS_JSON
Value: [your minified credentials.json - run python minify_credentials.py]
```

#### **Azure TTS Keys (Optional - if using Text-to-Speech):**
```
Name: AZURE_SPEECH_KEY
Value: [your_azure_speech_key]

Name: AZURE_SPEECH_REGION
Value: eastus
```

#### **LLM Configuration:**
```
Name: LLM_PROVIDER
Value: gemini

Name: GEMINI_MODEL
Value: gemini-1.5-flash
```

#### **CORS (For Frontend):**
```
Name: FRONTEND_URL
Value: https://your-app.netlify.app
(Add this AFTER deploying frontend)
```

**Click "Save"** at the top after adding all variables.

---

## 📦 **DEPLOYMENT METHOD 1: GitHub Actions (RECOMMENDED)**

### **Setup GitHub Deployment**

1. **In Azure Portal**:
   - Go to your Web App
   - Left menu → **"Deployment Center"**
   - Source: **GitHub**
   - Authorize GitHub access
   - Organization: `saichaithanya0705`
   - Repository: `AI-PDF-Reader`
   - Branch: `main`
   - Click **"Save"**

2. **Azure will automatically**:
   - Create `.github/workflows/azure-webapps-python.yml`
   - Set up CI/CD pipeline
   - Deploy on every push to main

3. **Verify Deployment**:
   - Go to **"Deployment Center" → "Logs"**
   - Watch build progress
   - First deploy takes 10-15 minutes

---

## 📦 **DEPLOYMENT METHOD 2: Local Git (ALTERNATIVE)**

### **Setup Local Git Deployment**

1. **In Azure Portal**:
   - Go to your Web App
   - Left menu → **"Deployment Center"**
   - Source: **"Local Git"**
   - Click **"Save"**
   - Copy the **Git Clone Uri**

2. **Get Deployment Credentials**:
   - Go to **"Deployment Center"** → **"Local Git/FTPS credentials"**
   - Note down:
     - Username: `$adobe-hackathon-backend`
     - Password: [click "Show" to reveal]

3. **Deploy from Local Machine**:

```bash
# 1. Add Azure remote
cd d:\adobe-hackathon-finale-main
git remote add azure https://<username>@adobe-hackathon-backend.scm.azurewebsites.net/adobe-hackathon-backend.git

# 2. Push to Azure
git push azure main

# 3. Enter password when prompted
```

---

## 📦 **DEPLOYMENT METHOD 3: ZIP Deploy (QUICK TEST)**

### **Manual ZIP Deployment**

```powershell
# 1. Install Azure CLI
# Download from: https://aka.ms/installazurecliwindows

# 2. Login to Azure
az login

# 3. Create deployment ZIP (from project root)
cd d:\adobe-hackathon-finale-main

# Create ZIP with only necessary files
Compress-Archive -Path backend\* -DestinationPath deploy.zip -Force

# 4. Deploy to Azure
az webapp deployment source config-zip `
  --resource-group adobe-hackathon-rg `
  --name adobe-hackathon-backend `
  --src deploy.zip

# 5. Check deployment status
az webapp log tail `
  --resource-group adobe-hackathon-rg `
  --name adobe-hackathon-backend
```

---

## 🔧 **STARTUP CONFIGURATION**

### **Set Startup Command**

1. **Go to**: Your Web App → **Configuration** → **General settings**
2. **Startup Command**:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

3. **Save** and **Restart** the web app

---

## 📂 **PROJECT STRUCTURE FOR AZURE**

Azure expects this structure:
```
your-repo/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py          ← FastAPI app here
│   ├── requirements.txt     ← Dependencies
│   └── setup_credentials.py
├── .deployment              ← Optional: custom deployment
└── startup.sh               ← Optional: custom startup
```

Your project already matches this! ✅

---

## 🔍 **CREATE .deployment FILE (OPTIONAL)**

Create in project root: `d:\adobe-hackathon-finale-main\.deployment`

```ini
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT = true
PROJECT = backend
```

This tells Azure to:
- Install from `backend/requirements.txt`
- Use backend folder as root

---

## 🔍 **CREATE startup.sh (OPTIONAL)**

Create in backend folder: `d:\adobe-hackathon-finale-main\backend\startup.sh`

```bash
#!/bin/bash

echo "🚀 Starting Adobe Hackathon Backend..."

# Setup credentials
python setup_credentials.py

# Start uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Make it executable (if using Git Bash):
```bash
chmod +x backend/startup.sh
```

---

## ✅ **VERIFY DEPLOYMENT**

### **1. Check Web App Status**
- Go to your Web App in Azure Portal
- Should show "Running" status

### **2. Test Endpoints**

```bash
# Health check
https://adobe-hackathon-backend.azurewebsites.net/health

# API Documentation
https://adobe-hackathon-backend.azurewebsites.net/docs

# Config endpoint
https://adobe-hackathon-backend.azurewebsites.net/config
```

### **3. View Logs**

**Option A: Azure Portal**
- Go to your Web App → **"Log stream"**
- Watch real-time logs

**Option B: Azure CLI**
```bash
az webapp log tail \
  --resource-group adobe-hackathon-rg \
  --name adobe-hackathon-backend
```

---

## 🐛 **TROUBLESHOOTING**

### **Issue: "Application Error"**

**Fix:** Check startup command
```bash
# Go to: Configuration → General settings → Startup Command
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### **Issue: "ModuleNotFoundError"**

**Fix:** Check logs, verify requirements.txt installed
```bash
# View logs
az webapp log tail --name adobe-hackathon-backend --resource-group adobe-hackathon-rg
```

### **Issue: Build failing**

**Fix:** Enable build during deployment
```bash
# Add to Application Settings
SCM_DO_BUILD_DURING_DEPLOYMENT = true
```

### **Issue: "Port 8080 already in use"**

**Fix:** Azure uses port 8000 by default, make sure startup command uses correct port
```bash
# Correct command
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### **Issue: CORS errors**

**Fix:** Add frontend URL to environment variables
```
FRONTEND_URL = https://your-app.netlify.app
```

---

## 📊 **EXPECTED TIMELINE**

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Web App Creation | 2-3 min | Azure provisions resources |
| First Deployment | 10-15 min | Installing dependencies, building |
| Subsequent Deploys | 3-5 min | Faster with cache |
| **Total First Time** | **15-20 min** | Complete setup |

---

## 💰 **AZURE PRICING**

### **Free Tier (F1)**
- ✅ Good for testing
- ❌ Shared resources
- ❌ No custom domain
- ❌ Limited compute
- **Cost**: FREE

### **Basic B1 (RECOMMENDED)**
- ✅ Dedicated compute
- ✅ Custom domain support
- ✅ 1.75 GB RAM
- ✅ 1 Core
- **Cost**: ~₹1,330/month (~$16/month)

### **Standard S1 (Production)**
- ✅ Auto-scaling
- ✅ Staging slots
- ✅ 3.5 GB RAM
- **Cost**: ~₹4,990/month (~$60/month)

---

## 🎯 **SUMMARY - EXACT COMMANDS**

```bash
# 1. CREATE WEB APP (Azure Portal - GUI method recommended)
#    Name: adobe-hackathon-backend
#    Runtime: Python 3.11
#    Region: East US
#    Plan: Basic B1

# 2. ADD ENVIRONMENT VARIABLES (Azure Portal → Configuration)
#    - PYTHON_VERSION = 3.11
#    - GEMINI_API_KEY = your_key
#    - SCM_DO_BUILD_DURING_DEPLOYMENT = true

# 3. SET STARTUP COMMAND (Configuration → General Settings)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 4. DEPLOY (Choose ONE method)

## Method A: GitHub (Recommended)
# Azure Portal → Deployment Center → GitHub → Connect

## Method B: Local Git
git remote add azure https://$adobe-hackathon-backend@adobe-hackathon-backend.scm.azurewebsites.net/adobe-hackathon-backend.git
git push azure main

## Method C: Azure CLI
az login
Compress-Archive -Path backend\* -DestinationPath deploy.zip -Force
az webapp deployment source config-zip --resource-group adobe-hackathon-rg --name adobe-hackathon-backend --src deploy.zip

# 5. VERIFY
# Visit: https://adobe-hackathon-backend.azurewebsites.net/docs
```

---

## 📝 **CHECKLIST**

**Before Deployment:**
- [ ] Azure account created
- [ ] Gemini API key ready
- [ ] Code pushed to GitHub (for GitHub Actions method)
- [ ] Review requirements.txt (all dependencies listed)

**During Deployment:**
- [ ] Web App created (Python 3.11, Linux, Basic B1)
- [ ] Environment variables added
- [ ] Startup command configured
- [ ] Deployment method chosen and configured

**After Deployment:**
- [ ] Test /health endpoint
- [ ] Test /docs endpoint
- [ ] Check logs for errors
- [ ] Copy backend URL for Netlify frontend
- [ ] Add FRONTEND_URL after Netlify deployment

---

## 🎉 **NEXT STEPS**

1. ✅ **Deploy Backend to Azure** (follow this guide)
2. ⏭️ **Deploy Frontend to Netlify** (you'll do this)
3. ⏭️ **Update Environment Variables**:
   - Azure: Add `FRONTEND_URL` (Netlify URL)
   - Netlify: Add `VITE_API_URL` (Azure URL)
4. ⏭️ **Test Everything**

---

## 💬 **HELPFUL AZURE CLI COMMANDS**

```bash
# View all web apps
az webapp list --output table

# Restart web app
az webapp restart --name adobe-hackathon-backend --resource-group adobe-hackathon-rg

# View logs
az webapp log tail --name adobe-hackathon-backend --resource-group adobe-hackathon-rg

# SSH into container
az webapp ssh --name adobe-hackathon-backend --resource-group adobe-hackathon-rg

# List environment variables
az webapp config appsettings list --name adobe-hackathon-backend --resource-group adobe-hackathon-rg

# Update startup command
az webapp config set --name adobe-hackathon-backend --resource-group adobe-hackathon-rg --startup-file "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
```

---

**🎯 YOUR BACKEND URL WILL BE:**
```
https://adobe-hackathon-backend.azurewebsites.net
```

Use this URL in your Netlify frontend configuration!

---

**Good luck with your deployment! 🚀**
