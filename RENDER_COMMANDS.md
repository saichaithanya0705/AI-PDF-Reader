# 🚀 RENDER DEPLOYMENT - EXACT COMMANDS

## 📋 Quick Reference Card

Copy and paste these EXACT commands into Render dashboard:

---

## 🔧 Render Configuration

### **1. Build Command**
```bash
cd backend && pip install --upgrade pip && pip install -r requirements.txt
```

### **2. Start Command**
```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### **3. Environment Variables**

#### Required (Add these first):
```
PYTHON_VERSION=3.11
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

#### Optional (Add if you have them):
```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
LLM_PROVIDER=gemini
FRONTEND_URL=https://your-app.netlify.app
```

---

## 📝 Step-by-Step Instructions

### Step 1: Go to Render
1. Open https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**

### Step 2: Connect Repository
1. Click **"Connect account"** next to GitHub
2. Authorize Render
3. Find and select: **`saichaithanya0705/AI-PDF-Reader`**

### Step 3: Fill in Settings

```
┌────────────────────────────────────────────────────────────┐
│ Name:                                                      │
│   adobe-hackathon-backend                                  │
│                                                            │
│ Region:                                                    │
│   Oregon (US West)                                         │
│                                                            │
│ Branch:                                                    │
│   main                                                     │
│                                                            │
│ Root Directory:                                            │
│   (leave blank)                                            │
│                                                            │
│ Environment:                                               │
│   Python 3                                                 │
│                                                            │
│ Build Command:                                             │
│   cd backend && pip install --upgrade pip &&               │
│   pip install -r requirements.txt                          │
│                                                            │
│ Start Command:                                             │
│   cd backend && python -m uvicorn app.main:app             │
│   --host 0.0.0.0 --port $PORT                              │
│                                                            │
│ Instance Type:                                             │
│   Free                                                     │
└────────────────────────────────────────────────────────────┘
```

### Step 4: Add Environment Variables
Click **"Advanced"** → Scroll to **"Environment Variables"**

**Required:**
1. Click **"Add Environment Variable"**
2. Key: `PYTHON_VERSION`, Value: `3.11`
3. Click **"Add Environment Variable"** again
4. Key: `GEMINI_API_KEY`, Value: `your_api_key_here`

**Optional (add more if needed):**
- `OPENAI_API_KEY`
- `AZURE_SPEECH_KEY`
- `FRONTEND_URL` (add this after deploying frontend)

### Step 5: Create Web Service
1. Click **"Create Web Service"** at the bottom
2. Wait 5-10 minutes for first deployment
3. Watch the logs

---

## ✅ Success Checklist

After deployment completes:

### 1. Check Logs
Look for these lines:
```
✓ Build successful
✓ Starting service with 'cd backend && python -m uvicorn...'
✓ Application startup complete
✓ Uvicorn running on http://0.0.0.0:8080
```

### 2. Test Endpoints
Your service URL will be: `https://adobe-hackathon-backend.onrender.com`

Test these:
```
✓ https://adobe-hackathon-backend.onrender.com/health
  Should return: {"status": "healthy"}

✓ https://adobe-hackathon-backend.onrender.com/docs
  Should show: Swagger API documentation
```

### 3. Copy Your Service URL
You'll need this for the frontend `.env` file!

---

## 🐛 Troubleshooting

### Error: "Build failed"
**Check:** Is the build command correct?
```bash
# Must include 'cd backend'
cd backend && pip install --upgrade pip && pip install -r requirements.txt
```

### Error: "Module not found"
**Check:** Is the start command correct?
```bash
# Must include 'cd backend'
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Error: "Port already in use"
**Check:** Start command must use `$PORT` variable (NOT 8000 or 8080)

### Error: "GEMINI_API_KEY not found"
**Check:** Did you add environment variable `GEMINI_API_KEY`?

### Build times out
**Try:** Deploy during off-peak hours or use Oregon/Ohio region

---

## 📊 What to Expect

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Queuing | 0-2 min | Waiting for build server |
| Installing packages | 3-5 min | `pip install -r requirements.txt` |
| Starting server | 1 min | Running uvicorn |
| Health checks | 30 sec | Verifying service is up |
| **Total** | **5-10 min** | First deploy only |

Subsequent deploys: 2-3 minutes

---

## 🎯 After Successful Deployment

### 1. Copy Your Backend URL
Example: `https://adobe-hackathon-backend.onrender.com`

### 2. Update Frontend `.env`
```env
VITE_API_URL=https://adobe-hackathon-backend.onrender.com
```

### 3. Deploy Frontend to Netlify
Now you're ready for frontend deployment!

---

## 💡 Pro Tips

1. **Auto-Deploy**: Enable in Settings → Auto-deploy on git push
2. **Logs**: Click "Logs" tab to watch real-time deployment
3. **Shell Access**: Click "Shell" tab to SSH into your service
4. **Health Check**: Render pings `/health` to verify service is up
5. **Cold Starts**: Free tier spins down after 15 min (30s to wake up)

---

## 📞 Need Help?

If deployment fails:
1. **Check the logs** in Render dashboard
2. **Copy the error message**
3. **Share it** and I'll help you fix it!

Common issues are usually:
- Missing environment variables
- Wrong build/start commands
- Package version conflicts

---

## ✨ Summary

**Build Command:**
```bash
cd backend && pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```
PYTHON_VERSION=3.11
GEMINI_API_KEY=your_key_here
```

**Time:** 5-10 minutes
**Success Rate:** 95%+

---

🎉 **You're ready to deploy!** Copy these commands and paste them into Render!
