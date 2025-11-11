# Deployment Guide - Render (Backend) + Netlify (Frontend)

## 🎯 Overview
This guide will help you deploy:
- **Backend**: FastAPI on Render
- **Frontend**: React/Vite on Netlify
- **Database**: Supabase (already set up)

---

## 📋 Prerequisites

### 1. Get Supabase Keys
Visit: https://supabase.com/dashboard/project/yqeqctzeanlomynwwwcg/settings/api

Copy these values:
- **service_role** key (click "Reveal")
- **JWT Secret** (scroll down to "JWT Settings")

### 2. Get Gemini API Key
You already have: `AIzaSyAN49K7cFWJ8b8dhbLino3cduEJdlMx068`

---

## 🚀 Part 1: Deploy Backend to Render

### Step 1: Create Web Service on Render

1. Go to https://render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `saichaithanya0705/AI-PDF-Reader`
4. Configure:
   - **Name**: `adobe-pdf-intelligence-backend`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or `backend` if needed)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Add Environment Variables

In Render dashboard, go to **Environment** tab and add:

```bash
# Python
PYTHON_VERSION=3.11

# LLM Configuration
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSyAN49K7cFWJ8b8dhbLino3cduEJdlMx068
GEMINI_MODEL=gemini-2.0-flash

# Supabase Configuration
USE_SUPABASE=true
SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co
SUPABASE_SERVICE_KEY=<paste_your_service_role_key>
SUPABASE_JWT_SECRET=<paste_your_jwt_secret>

# Azure OpenAI (Optional - if you want fallback)
AZURE_OPENAI_KEY=<your_azure_openai_key_if_needed>
AZURE_OPENAI_BASE=https://eastasia.api.cognitive.microsoft.com/
AZURE_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT_NAME=gpt-4o

# TTS Configuration (Optional)
TTS_PROVIDER=azure
AZURE_TTS_KEY=<your_azure_tts_key_if_needed>
AZURE_TTS_REGION=eastasia
```

### Step 3: Deploy

1. Click **"Create Web Service"**
2. Wait for deployment (5-10 minutes)
3. Once deployed, copy your backend URL (e.g., `https://adobe-pdf-intelligence-backend.onrender.com`)

---

## 🌐 Part 2: Deploy Frontend to Netlify

### Step 1: Update Frontend Environment

Before deploying, update `frontend/.env` with your Render backend URL:

```bash
VITE_API_URL=https://your-backend-url.onrender.com
VITE_SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxZXFjdHplYW5sb215bnd3d2NnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NjYwNTMsImV4cCI6MjA3ODQ0MjA1M30.UdIVDjhN9ufY1ihcU_Sel-ocXkXNV60yzp5Ujks-0v8
```

**Important**: Commit and push this change:
```bash
git add frontend/.env
git commit -m "Update frontend API URL for production"
git push origin main
```

### Step 2: Deploy to Netlify

1. Go to https://app.netlify.com/
2. Click **"Add new site"** → **"Import an existing project"**
3. Connect to GitHub and select: `saichaithanya0705/AI-PDF-Reader`
4. Configure build settings:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
   - **Branch**: `main`

### Step 3: Add Environment Variables in Netlify

Go to **Site settings** → **Environment variables** and add:

```bash
VITE_API_URL=https://your-backend-url.onrender.com
VITE_SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxZXFjdHplYW5sb215bnd3d2NnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NjYwNTMsImV4cCI6MjA3ODQ0MjA1M30.UdIVDjhN9ufY1ihcU_Sel-ocXkXNV60yzp5Ujks-0v8
```

### Step 4: Deploy

1. Click **"Deploy site"**
2. Wait for build (3-5 minutes)
3. Once deployed, you'll get a URL like: `https://your-site-name.netlify.app`

---

## 🔧 Post-Deployment Configuration

### 1. Update CORS in Backend

If you get CORS errors, update `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-site-name.netlify.app",
        "http://localhost:5173",  # For local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Configure Supabase Allowed URLs

1. Go to Supabase Dashboard → Authentication → URL Configuration
2. Add your Netlify URL to **Site URL** and **Redirect URLs**:
   - `https://your-site-name.netlify.app`
   - `https://your-site-name.netlify.app/**`

---

## ✅ Verification Checklist

After deployment, test these features:

- [ ] Frontend loads at Netlify URL
- [ ] Backend health check: `https://your-backend.onrender.com/api/health`
- [ ] User signup works
- [ ] User login works
- [ ] PDF upload works
- [ ] Chatbot responds (Gemini API)
- [ ] PDFs are isolated per user (Supabase RLS)
- [ ] Cross-document search works

---

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Backend won't start
- Check Render logs for errors
- Verify all environment variables are set
- Ensure `SUPABASE_SERVICE_KEY` and `SUPABASE_JWT_SECRET` are correct

**Problem**: Gemini API errors
- Verify `GOOGLE_API_KEY` is correct
- Check API quota: https://console.cloud.google.com/

### Frontend Issues

**Problem**: Can't connect to backend
- Verify `VITE_API_URL` points to your Render backend
- Check CORS configuration in backend
- Open browser console for detailed errors

**Problem**: Authentication not working
- Verify Supabase URL and anon key in Netlify env vars
- Check Supabase dashboard for allowed URLs

### Database Issues

**Problem**: Users can see other users' PDFs
- Verify `USE_SUPABASE=true` in Render env vars
- Check RLS policies in Supabase dashboard
- Restart Render service after changing env vars

---

## 📊 Monitoring

### Render
- View logs: Dashboard → Logs
- Monitor metrics: Dashboard → Metrics
- Set up alerts: Dashboard → Notifications

### Netlify
- View deploy logs: Site → Deploys
- Monitor functions: Site → Functions
- Analytics: Site → Analytics

### Supabase
- Database usage: Dashboard → Database
- Auth users: Dashboard → Authentication
- API logs: Dashboard → API

---

## 🔄 Continuous Deployment

Both Render and Netlify will auto-deploy when you push to `main` branch:

```bash
# Make changes
git add .
git commit -m "Your changes"
git push origin main

# Render and Netlify will automatically deploy
```

---

## 💰 Cost Estimates

### Free Tier Limits:
- **Render**: 750 hours/month (sleeps after 15 min inactivity)
- **Netlify**: 100 GB bandwidth, 300 build minutes/month
- **Supabase**: 500 MB database, 2 GB bandwidth/month

### Paid Plans (if needed):
- **Render**: $7/month (always on)
- **Netlify**: $19/month (more bandwidth)
- **Supabase**: $25/month (8 GB database)

---

## 🎉 You're Done!

Your application is now live:
- **Frontend**: https://your-site-name.netlify.app
- **Backend**: https://your-backend.onrender.com
- **Database**: Supabase (managed)

Share your app and enjoy! 🚀
