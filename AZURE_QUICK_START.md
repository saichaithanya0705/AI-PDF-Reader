# Azure Deployment Quick Start - AI PDF Reader

## 🚀 Deploy in 10 Minutes

### Step 1: Create Web App (2 min)
```bash
az login
az group create --name ai-pdf-reader-rg --location eastus
az appservice plan create --name ai-pdf-plan --resource-group ai-pdf-reader-rg --sku B1 --is-linux
az webapp create --name ai-pdf-reader-backend --resource-group ai-pdf-reader-rg --plan ai-pdf-plan --runtime "PYTHON:3.11"
```

### Step 2: Set Environment Variables (2 min)
```bash
# Replace placeholder values with your actual keys from .env file
az webapp config appsettings set \
  --name ai-pdf-reader-backend \
  --resource-group ai-pdf-reader-rg \
  --settings \
    PYTHON_VERSION="3.11" \
    LLM_PROVIDER="gemini" \
    TTS_PROVIDER="azure" \
    USE_SUPABASE="true" \
    GEMINI_API_KEY="your_gemini_key_from_env" \
    SUPABASE_URL="https://your-project.supabase.co" \
    SUPABASE_SERVICE_KEY="your_supabase_service_key" \
    AZURE_TTS_KEY="your_azure_speech_key" \
    AZURE_TTS_ENDPOINT="https://eastasia.api.cognitive.microsoft.com/"
```

**💡 Get your actual keys from:** `.env` file in your project root

### Step 3: Configure Startup (1 min)
```bash
az webapp config set \
  --name ai-pdf-reader-backend \
  --resource-group ai-pdf-reader-rg \
  --startup-file "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
```

### Step 4: Deploy Code (5 min)

**Via GitHub Actions** (Recommended):
1. Azure Portal → Web App → Deployment Center
2. Source: GitHub
3. Repo: `saichaithanya0705/AI-PDF-Reader`
4. Branch: `main`
5. Save → Auto-deploys on push

**Via Local Git**:
```bash
git remote add azure https://ai-pdf-reader-backend.scm.azurewebsites.net:443/ai-pdf-reader-backend.git
git push azure main
```

---

## ✅ Verify Deployment

```bash
# Check status
az webapp show --name ai-pdf-reader-backend --resource-group ai-pdf-reader-rg --query state

# Test endpoint
curl https://ai-pdf-reader-backend.azurewebsites.net/

# View logs
az webapp log tail --name ai-pdf-reader-backend --resource-group ai-pdf-reader-rg
```

**Success**: Open `https://ai-pdf-reader-backend.azurewebsites.net/docs` to see FastAPI docs

---

## 🔧 Critical Files (Already in Your Repo)

### `.deployment` (REQUIRED)
```ini
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT = true
PROJECT = backend
```
**Purpose**: Tells Azure your code is in `backend/` subfolder

### `backend/requirements.txt`
- Optimized: ~50MB (removed torch, sentence-transformers)
- Contains: fastapi, uvicorn, PyMuPDF, google-generativeai, supabase

### `backend/setup_credentials.py`
- Auto-handles Google Cloud credentials from env vars
- No manual config needed

---

## 🐛 Common Issues

| Issue | Fix |
|-------|-----|
| **Application Error** | Check startup command: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` |
| **Module not found** | Verify `.deployment` file exists with `PROJECT = backend` |
| **CORS errors** | Add `FRONTEND_URL` env var after deploying frontend |
| **Slow first request** | Enable "Always On" (requires Basic tier) |

---

## 💰 Pricing

- **Free (F1)**: $0 - Testing only
- **Basic (B1)**: $13/month - Production ready
- **Premium (P1V2)**: $96/month - Auto-scaling

**Recommendation**: Start with B1 for production

---

## 📊 Key URLs After Deployment

- **API Base**: `https://ai-pdf-reader-backend.azurewebsites.net`
- **API Docs**: `https://ai-pdf-reader-backend.azurewebsites.net/docs`
- **Health Check**: `https://ai-pdf-reader-backend.azurewebsites.net/`

---

## 🔗 Next Steps

### 1. ✅ Deploy Backend to Azure (Done!)
Your backend is deployed and configured with all environment variables.

### 2. 🔜 Deploy Frontend to Netlify

**Netlify Setup:**
1. Go to [Netlify](https://app.netlify.com/) → New site from Git
2. Connect to GitHub: `saichaithanya0705/AI-PDF-Reader`
3. Configure build:
   ```
   Base directory: frontend
   Build command: npm run build
   Publish directory: frontend/dist
   ```

**Environment Variables (Netlify Dashboard → Site settings → Environment variables):**
```
VITE_API_URL = https://ai-pdf-reader-backend.azurewebsites.net
VITE_SUPABASE_URL = your_supabase_url_from_frontend_env
VITE_SUPABASE_ANON_KEY = your_supabase_anon_key_from_frontend_env
```

**💡 Get actual values from:** `frontend/.env` file

**Important**: Replace `ai-pdf-reader-backend` with your actual Azure app name!

### 3. 🔜 Update Backend CORS (After Netlify Deploy)

Once your Netlify site is live, add this to Azure:
```bash
az webapp config appsettings set \
  --name ai-pdf-reader-backend \
  --resource-group ai-pdf-reader-rg \
  --settings FRONTEND_URL="https://your-app.netlify.app"
```

---

## 📚 Full Guide

See `AZURE_DEPLOYMENT_GUIDE.md` for detailed instructions, troubleshooting, and advanced configuration.

---

**Repository**: https://github.com/saichaithanya0705/AI-PDF-Reader  
**Support**: See AZURE_DEPLOYMENT_GUIDE.md for troubleshooting
