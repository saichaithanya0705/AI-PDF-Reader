#!/bin/bash
set -e

echo "🚀 Digital Ocean Droplet Setup Script"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use: sudo bash setup_droplet.sh)"
    exit 1
fi

# Install system packages
echo "📦 Installing system packages..."
apt update
apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git curl ca-certificates gnupg

# Install Node.js 20.x
echo "📦 Installing Node.js..."
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /tmp/nodesource.gpg.key
gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg /tmp/nodesource.gpg.key
chmod 0644 /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
apt update
apt install -y nodejs

# Create application user
echo "👤 Creating application user..."
if ! id "pdfapp" &>/dev/null; then
    useradd -m -s /bin/bash pdfapp
    echo "✅ User 'pdfapp' created"
else
    echo "✅ User 'pdfapp' already exists"
fi

# Create application directory
echo "📁 Setting up application directory..."
mkdir -p /var/www/pdfapp
chown -R pdfapp:pdfapp /var/www/pdfapp

echo ""
echo "✅ Droplet setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy your application files to /var/www/pdfapp"
echo "2. Switch to pdfapp user: su - pdfapp"
echo "3. Run: bash /var/www/pdfapp/deploy_backend.sh"
echo "4. Run: bash /var/www/pdfapp/deploy_frontend.sh"
echo "5. Run: sudo bash /var/www/pdfapp/setup_services.sh"
