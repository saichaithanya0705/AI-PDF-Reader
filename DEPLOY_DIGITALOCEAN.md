# 🚀 Digital Ocean Deployment Guide

## Quick Start

### 1. Prerequisites
- Digital Ocean Droplet (Ubuntu 22.04 LTS, 2 CPU, 4GB RAM recommended)
- Domain name pointed to droplet's IP address
- SSH access to the droplet

### 2. Upload Files to Droplet

From your local machine:

```bash
# Option 1: Using SCP
scp -r d:\adobe-hackathon-finale-main/* root@<droplet-ip>:/var/www/pdfapp/

# Option 2: Using Git (recommended)
# First, push your code to GitHub/GitLab
# Then on droplet:
cd /var/www/pdfapp
git clone <your-repo-url> .
```

### 3. Run Deployment Scripts

SSH into your droplet:

```bash
ssh root@<droplet-ip>
```

Then run these commands in order:

```bash
# Step 1: Setup the droplet (installs Node, Python, Nginx, etc.)
cd /var/www/pdfapp
chmod +x *.sh
sudo bash setup_droplet.sh

# Step 2: Configure environment variables
cp .env.production .env
nano .env  # Fill in your API keys and credentials

# Step 3: Deploy backend
su - pdfapp
cd /var/www/pdfapp
bash deploy_backend.sh

# Step 4: Deploy frontend
# Update frontend/.env with production URL
echo "VITE_API_URL=https://your-domain.com" > frontend/.env
echo "VITE_SUPABASE_URL=https://yqeqctzeanlomynwwwcg.supabase.co" >> frontend/.env
echo "VITE_SUPABASE_ANON_KEY=<your-anon-key>" >> frontend/.env

bash deploy_frontend.sh

# Step 5: Setup services (systemd and nginx)
exit  # Exit back to root
sudo bash setup_services.sh
```

### 4. Configure SSL (HTTPS)

```bash
# Update nginx.conf with your actual domain
sudo nano /etc/nginx/sites-available/pdfapp
# Change "server_name _;" to "server_name your-domain.com;"

# Reload nginx
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 5. Verify Deployment

```bash
# Check backend service
sudo systemctl status pdfapp-backend

# Check nginx
sudo systemctl status nginx

# Test backend
curl http://localhost:8080/api/library/statistics

# Test public access
curl https://your-domain.com/api/library/statistics
```

## 📁 Deployment Files

| File | Purpose |
|------|---------|
| `setup_droplet.sh` | Initial server setup (Python, Node, Nginx) |
| `deploy_backend.sh` | Install Python dependencies and setup backend |
| `deploy_frontend.sh` | Build React frontend |
| `setup_services.sh` | Configure systemd and nginx |
| `pdfapp-backend.service` | Systemd service definition |
| `nginx.conf` | Nginx reverse proxy configuration |
| `requirements.txt` | Python dependencies list |
| `.env.production` | Environment variables template |

## 🔧 Port Configuration

- **Backend Internal**: Port 8080 (managed by systemd)
- **Nginx HTTP**: Port 80 → redirects to 443
- **Nginx HTTPS**: Port 443 → proxies to backend:8080
- **Frontend**: Built as static files, served by Nginx

## 🔐 Environment Variables Required

### Backend (.env)
```
LLM_PROVIDER=gemini
GOOGLE_API_KEY=<your-key>
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_KEY=<your-service-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>
AZURE_TTS_KEY=<your-azure-key>
FRONTEND_URL=https://your-domain.com
```

### Frontend (frontend/.env)
```
VITE_API_URL=https://your-domain.com
VITE_SUPABASE_URL=<your-supabase-url>
VITE_SUPABASE_ANON_KEY=<your-anon-key>
```

## 📊 Monitoring

```bash
# View backend logs
sudo journalctl -u pdfapp-backend -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check service status
sudo systemctl status pdfapp-backend
sudo systemctl status nginx
```

## 🔄 Updates

To update the application:

```bash
cd /var/www/pdfapp
git pull

# Update backend
su - pdfapp
bash deploy_backend.sh

# Update frontend
bash deploy_frontend.sh
exit

# Restart services
sudo systemctl restart pdfapp-backend
sudo systemctl reload nginx
```

## 🐛 Troubleshooting

### Backend won't start
```bash
sudo journalctl -u pdfapp-backend -n 100 --no-pager
# Check for missing environment variables or Python errors
```

### Upload fails
```bash
# Check nginx config
sudo nginx -t

# Verify upload size limit in nginx.conf:
# client_max_body_size 100M;

# Check backend /uploads directory permissions
ls -la /var/www/pdfapp/uploads
```

### Port 8080 already in use
```bash
# Find what's using the port
sudo lsof -i :8080

# Kill the process if needed
sudo kill -9 <PID>

# Restart backend service
sudo systemctl restart pdfapp-backend
```

## 📚 Additional Resources

- [Detailed Deployment Plan](./digital_ocean_deployment.md) - In artifacts folder
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Systemd Service Guide](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Let's Encrypt](https://letsencrypt.org/)

## ✅ Post-Deployment Checklist

- [ ] Backend service running: `sudo systemctl status pdfapp-backend`
- [ ] Nginx running: `sudo systemctl status nginx`
- [ ] SSL certificate installed: `https://your-domain.com` loads
- [ ] File upload works: Test uploading a PDF
- [ ] Chat works: Test asking questions about PDFs
- [ ] WebSocket connected: Check browser console for WS connection
- [ ] Firewall configured: Only ports 22, 80, 443 open

## 🎉 Success!

Your application should now be live at `https://your-domain.com`!

For support, check the logs or refer to the detailed deployment plan in the artifacts folder.
