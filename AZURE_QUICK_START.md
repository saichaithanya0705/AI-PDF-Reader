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
az webapp config appsettings set \
  --name ai-pdf-reader-backend \
  --resource-group ai-pdf-reader-rg \
  --settings \
    PYTHON_VERSION="3.11" \
    GEMINI_API_KEY="your_gemini_key_here"
```

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

1. ✅ Deploy backend to Azure (this guide)
2. 🔜 Deploy frontend to Netlify:
   - Build: `npm run build`
   - Env: `VITE_API_URL = https://ai-pdf-reader-backend.azurewebsites.net`
3. 🔜 Update backend CORS:
   - Add env var: `FRONTEND_URL = https://your-app.netlify.app`

---

## 📚 Full Guide

See `AZURE_DEPLOYMENT_GUIDE.md` for detailed instructions, troubleshooting, and advanced configuration.

---

**Repository**: https://github.com/saichaithanya0705/AI-PDF-Reader  
**Support**: See AZURE_DEPLOYMENT_GUIDE.md for troubleshooting
