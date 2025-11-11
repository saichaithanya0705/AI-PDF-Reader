# Quick Deployment Checklist ✅

## Before You Start
- [ ] Supabase service_role key ready
- [ ] Supabase JWT Secret ready
- [ ] Gemini API key: `AIzaSyAN49K7cFWJ8b8dhbLino3cduEJdlMx068`

---

## Backend on Render (15 minutes)

### 1. Create Service
- [ ] Go to https://render.com/
- [ ] New Web Service
- [ ] Connect GitHub: `saichaithanya0705/AI-PDF-Reader`
- [ ] Build: `pip install -r backend/requirements.txt`
- [ ] Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Environment Variables (Copy-Paste Ready)
```bash
PYTHON_VERSION=3.11
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSyAN49K7cFWJ8b8dhbLino3cduEJdlMx068
GEMINI_MODEL=gemini-2.0-flash
USE_SUPABASE=true
SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co
SUPABASE_SERVICE_KEY=<YOUR_SERVICE_KEY>
SUPABASE_JWT_SECRET=<YOUR_JWT_SECRET>
```

### 3. Deploy & Copy URL
- [ ] Click "Create Web Service"
- [ ] Wait 5-10 minutes
- [ ] Copy backend URL: `https://________.onrender.com`

---

## Frontend on Netlify (10 minutes)

### 1. Update Frontend .env
```bash
cd frontend
# Edit .env file with your Render backend URL
VITE_API_URL=https://your-backend.onrender.com
```

### 2. Commit & Push
```bash
git add frontend/.env
git commit -m "Update API URL for production"
git push origin main
```

### 3. Deploy on Netlify
- [ ] Go to https://app.netlify.com/
- [ ] Import from GitHub: `saichaithanya0705/AI-PDF-Reader`
- [ ] Base directory: `frontend`
- [ ] Build: `npm run build`
- [ ] Publish: `frontend/dist`

### 4. Environment Variables
```bash
VITE_API_URL=https://your-backend.onrender.com
VITE_SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxZXFjdHplYW5sb215bnd3d2NnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NjYwNTMsImV4cCI6MjA3ODQ0MjA1M30.UdIVDjhN9ufY1ihcU_Sel-ocXkXNV60yzp5Ujks-0v8
```

---

## Post-Deployment (5 minutes)

### 1. Update Supabase URLs
- [ ] Go to Supabase → Authentication → URL Configuration
- [ ] Add Netlify URL: `https://your-site.netlify.app`

### 2. Test Everything
- [ ] Visit your Netlify URL
- [ ] Sign up new user
- [ ] Upload a PDF
- [ ] Test chatbot
- [ ] Verify PDFs are user-specific

---

## Quick Links

- **GitHub Repo**: https://github.com/saichaithanya0705/AI-PDF-Reader
- **Supabase Dashboard**: https://supabase.com/dashboard/project/yqeqctzeanlomynwwwcg
- **Supabase API Keys**: https://supabase.com/dashboard/project/yqeqctzeanlomynwwwcg/settings/api
- **Render Dashboard**: https://dashboard.render.com/
- **Netlify Dashboard**: https://app.netlify.com/

---

## If Something Goes Wrong

### Backend not starting?
```bash
# Check Render logs
# Verify SUPABASE_SERVICE_KEY is set
# Ensure GOOGLE_API_KEY is correct
```

### Frontend can't connect?
```bash
# Check VITE_API_URL in Netlify env vars
# Verify backend is running (visit /api/health)
# Check browser console for CORS errors
```

### Authentication failing?
```bash
# Verify Supabase anon key in Netlify
# Check Netlify URL is added to Supabase allowed URLs
# Clear browser cache and try again
```

---

## Done! 🎉

Your app is live:
- Frontend: https://________.netlify.app
- Backend: https://________.onrender.com
- Database: Supabase ✅
