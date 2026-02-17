#!/bin/bash
set -e

echo "⚙️  Setting up systemd and nginx services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use: sudo bash setup_services.sh)"
    exit 1
fi

# Copy systemd service file
echo "📋 Installing systemd service..."
cp /var/www/pdfapp/pdfapp-backend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable pdfapp-backend
systemctl start pdfapp-backend

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet pdfapp-backend; then
    echo "✅ Backend service is running"
else
    echo "❌ Backend service failed to start. Check logs with: sudo journalctl -u pdfapp-backend -n 50"
    exit 1
fi

# Setup Nginx
echo "📋 Configuring Nginx..."
cp /var/www/pdfapp/nginx.conf /etc/nginx/sites-available/pdfapp

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/pdfapp /etc/nginx/sites-enabled/

# Test nginx configuration
if nginx -t; then
    echo "✅ Nginx configuration is valid"
    systemctl restart nginx
    echo "✅ Nginx restarted"
else
    echo "❌ Nginx configuration is invalid"
    exit 1
fi

echo ""
echo "✅ All services configured and running!"
echo ""
echo "📊 Service Status:"
systemctl status pdfapp-backend --no-pager -l | head -10
echo ""
systemctl status nginx --no-pager -l | head -10
echo ""
echo "🌐 Your application should now be accessible!"
echo ""
echo "⚠️  Next steps:"
echo "1. Update nginx.conf with your actual domain name"
echo "2. Run: sudo certbot --nginx -d your-domain.com (for SSL)"
echo "3. Test: curl http://localhost/api/library/statistics"
