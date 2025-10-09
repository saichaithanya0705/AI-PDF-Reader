# 🚀 Step-by-Step Render Deployment Guide

## Prerequisites
✅ GitHub repository: https://github.com/saichaithanya0705/AI-PDF-Reader
✅ Optimized requirements.txt (just pushed)
✅ Render account (free): https://render.com

---

## 📋 Deployment Steps

### Step 1: Create Render Account
1. Go to https://render.com
2. Click "Get Started for Free"
3. Sign up with GitHub (recommended)

### Step 2: Create New Web Service
1. Click "New +" → "Web Service"
2. Click "Connect Account" next to GitHub
3. Authorize Render to access your repositories
4. Find and select `AI-PDF-Reader` repository

### Step 3: Configure Service
Fill in these EXACT settings:

```
┌─────────────────────────────────────────────────────┐
│ Name: adobe-hackathon-backend                       │
│ Region: Oregon (US West)                            │
│ Branch: main                                        │
│ Root Directory: (leave blank)                       │
│ Runtime: Python 3                                   │
│ Build Command: cd backend && pip install --upgrade  │
│                pip && pip install -r requirements.txt│
│ Start Command: cd backend && python -m uvicorn      │
│                app.main:app --host 0.0.0.0 --port   │
│                $PORT                                 │
│ Instance Type: Free                                 │
└─────────────────────────────────────────────────────┘
```

### Step 4: Add Environment Variables
**Click "Advanced" → Scroll to "Environment Variables"**

**Required Variables:**
```
PYTHON_VERSION = 3.11
GEMINI_API_KEY = your_gemini_api_key_here
```

**Optional Variables (add if you have them):**
```
OPENAI_API_KEY = your_openai_key
ANTHROPIC_API_KEY = your_anthropic_key
AZURE_SPEECH_KEY = your_azure_key
AZURE_SPEECH_REGION = eastus
LLM_PROVIDER = gemini
```

### Step 5: Deploy
1. Click "Create Web Service"
2. Wait 5-10 minutes for first deployment
3. Watch the logs for any errors

### Step 6: Verify Deployment
Once deployed, you'll see:
```
==> Your service is live 🎉
```

**Test your endpoints:**
1. Copy your service URL (e.g., `https://adobe-hackathon-backend.onrender.com`)
2. Visit: `https://your-service.onrender.com/health`
3. Should return: `{"status": "healthy"}`
4. Visit: `https://your-service.onrender.com/docs` for API documentation

---

## 🔧 Configuration After Deployment

### Update Frontend .env
Once backend is deployed, update your frontend `.env`:

```env
# Replace with your actual Render URL
VITE_API_URL=https://adobe-hackathon-backend.onrender.com

# Get these from Supabase dashboard
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

---

## 📊 Expected Timeline

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Queueing | 0-2 min | Waiting for build server |
| Build | 3-5 min | Installing dependencies |
| Deploy | 1-2 min | Starting server |
| **Total** | **5-10 min** | First deploy only |

**Subsequent deploys**: 2-3 minutes

---

## ✅ Success Indicators

### In Render Logs:
```
✓ Build successful
✓ Starting service
✓ Application startup complete
✓ Uvicorn running on http://0.0.0.0:8080
```

### In Browser:
- `/health` returns `{"status": "healthy"}`
- `/docs` shows Swagger UI
- No 502/503 errors

---

## 🐛 Troubleshooting

### Build Error: "Could not find a version"
**Problem**: Package version not available
**Fix**: Older langchain versions may not exist
```bash
# Try these versions instead:
langchain==0.1.20
langchain-openai==0.1.8
langchain-google-genai==1.0.6
```

### Build Error: "Out of memory"
**Problem**: Still too many packages
**Fix**: Remove more packages or upgrade to paid tier

### Runtime Error: "Port already in use"
**Problem**: Wrong start command
**Fix**: Make sure start command uses `$PORT` variable:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Error: "Module not found"
**Problem**: Import path wrong
**Fix**: Make sure start command includes `cd backend`

### Service starts but returns 502
**Problem**: Health check failing
**Fix**: Add `/health` endpoint to your FastAPI app:
```python
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## 💡 Pro Tips

1. **Auto-Deploy**: Enable in Render settings to auto-deploy on git push
2. **Logs**: Use "Logs" tab to debug issues in real-time
3. **Metrics**: Check "Metrics" tab for memory/CPU usage
4. **Shell**: Use "Shell" tab to SSH into your service
5. **Cold Starts**: First request after 15 min takes 30-60 seconds (free tier limitation)

---

## 🎯 Next Steps After Backend Deploy

1. ✅ **Test all endpoints** using `/docs`
2. ✅ **Copy your Render URL** 
3. ✅ **Update frontend `.env`** with backend URL
4. ✅ **Deploy frontend to Netlify**
5. ✅ **Update backend CORS** to allow frontend URL

---

## 📞 Support

### Render Issues:
- Docs: https://render.com/docs
- Community: https://community.render.com
- Status: https://status.render.com

### Common Questions:

**Q: Why is my service slow on first request?**
A: Free tier services spin down after 15 min. Upgrade to $7/month to keep always-on.

**Q: Can I use a custom domain?**
A: Yes! Add custom domain in Render settings (requires paid plan for HTTPS).

**Q: How do I see logs?**
A: Click "Logs" tab in Render dashboard for real-time logs.

**Q: Database not persisting?**
A: SQLite doesn't persist on free tier. Use Render PostgreSQL or external database.

---

🎉 **You're all set!** Follow these steps and you'll have a deployed backend in 10 minutes!
