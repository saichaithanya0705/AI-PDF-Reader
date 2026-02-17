# Port Configuration Guide

## Local Development

### Backend
- **Port**: `8080`
- **URL**: `http://localhost:8080`
- **Start command**: `python run_app.py`
- **Configuration**: `.env.local`

### Frontend
- **Port**: `5173` (Vite default)
- **URL**: `http://localhost:5173`
- **API Target**: `http://localhost:8080`
- **Start command**: `cd frontend && npm run dev`
- **Configuration**: `frontend/.env.local`

### Environment Files
```bash
# Backend
.env.local              # Use this for local development

# Frontend
frontend/.env.local     # Use this for local development
```

---

## Production Deployment (Digital Ocean)

### Nginx (Reverse Proxy)
- **HTTP Port**: `80` (redirects to HTTPS)
- **HTTPS Port**: `443`
- **Public URL**: `https://64-227-179-63.sslip.io`
- **SSL Certificate**: Let's Encrypt (auto-renewed)

### Backend (Internal)
- **Port**: `8080` (only accessible via Nginx proxy)
- **Service**: `pdfapp-backend.service` (systemd)
- **User**: `pdfapp`
- **Working Directory**: `/var/www/pdfapp`
- **Configuration**: `/var/www/pdfapp/.env`

### Frontend (Static Files)
- **Served by**: Nginx
- **Location**: `/var/www/pdfapp/frontend/dist`
- **API Target**: `https://64-227-179-63.sslip.io` (proxied to backend:8080)
- **Build Configuration**: `frontend/.env.production`

### Port Flow
```
User Browser → https://64-227-179-63.sslip.io (Port 443)
             ↓
          Nginx (Port 443)
             ↓
          [Frontend Static Files] (for / paths)
             OR
          [Proxy to Backend] (for /api, /config, /upload paths)
             ↓
          Backend (localhost:8080)
             ↓
          [Supabase Database]
```

### Environment Files
```bash
# Backend (on server)
/var/www/pdfapp/.env    # Copy from .env.production

# Frontend (on server)
/var/www/pdfapp/frontend/.env    # Copy from frontend/.env.production
```

---

## Quick Deployment Commands

### Deploy to Production
```bash
# 1. Upload environment files
scp -i C:\Users\SAI\.ssh\id_ed25519 .env.production root@64.227.179.63:/var/www/pdfapp/.env
scp -i C:\Users\SAI\.ssh\id_ed25519 frontend/.env.production root@64.227.179.63:/var/www/pdfapp/frontend/.env

# 2. Upload code (if changed)
scp -i C:\Users\SAI\.ssh\id_ed25519 -r backend frontend root@64.227.179.63:/var/www/pdfapp/

# 3. SSH and rebuild
ssh -i C:\Users\SAI\.ssh\id_ed25519 root@64.227.179.63
su - pdfapp
cd /var/www/pdfapp
bash deploy_backend.sh
bash deploy_frontend.sh
exit
systemctl restart pdfapp-backend
```

### Switch to Local Development
```bash
# Copy local env files
cp .env.local .env
cp frontend/.env.local frontend/.env

# Start services
python run_app.py          # Terminal 1 (backend on :8080)
cd frontend && npm run dev  # Terminal 2 (frontend on :5173)
```

---

## Troubleshooting

### Frontend can't connect to backend
- **Local**: Check `VITE_API_URL` in `frontend/.env.local` → should be `http://localhost:8080`
- **Production**: Check `VITE_API_URL` in `frontend/.env.production` → should be `https://64-227-179-63.sslip.io`
- **Fix**: Update env file and rebuild frontend: `npm run build`

### CORS errors
- **Local**: Check `FRONTEND_URL` in `.env.local` → should be `http://localhost:5173`
- **Production**: Check `FRONTEND_URL` in `/var/www/pdfapp/.env` → should be `https://64-227-179-63.sslip.io`
- **Fix**: Update env file and restart backend

### Port already in use
```bash
# Find process on port 8080
netstat -ano | findstr :8080    # Windows
lsof -i :8080                   # Linux/Mac

# Kill the process
taskkill /PID <pid> /F          # Windows
kill -9 <pid>                   # Linux/Mac
```
