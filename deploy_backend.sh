#!/bin/bash
set -e

echo "🐍 Deploying Backend..."

# Ensure we're in the right directory
cd /var/www/pdfapp

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Create temp directory for pip to avoid /tmp space issues
mkdir -p /var/www/pdfapp/tmp
export TMPDIR=/var/www/pdfapp/tmp

# Install backend dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create necessary directories
mkdir -p backend/data
mkdir -p uploads

# Set permissions
chmod 755 backend/data
chmod 755 uploads

echo "✅ Backend deployment complete!"
echo ""
echo "⚠️  Important: Make sure to create/update .env file with production credentials"
echo "    Example: cp .env.example .env (then edit with your API keys)"
