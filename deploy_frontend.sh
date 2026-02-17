#!/bin/bash
set -e

echo "⚛️  Deploying Frontend..."

cd /var/www/pdfapp/frontend

# Install Node dependencies
echo "📦 Installing Node dependencies..."
npm install

# Build for production
echo "🔨 Building frontend..."
npm run build

echo "✅ Frontend build complete!"
echo "📁 Build output: frontend/dist/"
echo ""
echo "⚠️  Important: Make sure frontend/.env has correct VITE_API_URL"
echo "    For production: VITE_API_URL=https://your-domain.com"
