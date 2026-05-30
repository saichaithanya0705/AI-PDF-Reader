#!/bin/bash
set -e

echo "Deploying Backend..."

# Ensure we're in the right directory
cd /var/www/pdfapp

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

if [ ! -f ".env" ]; then
    echo "ERROR: Missing /var/www/pdfapp/.env."
    echo "Provision production secrets from the approved secure source before deploying."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Create temp directory for pip to avoid /tmp space issues
mkdir -p /var/www/pdfapp/tmp
export TMPDIR=/var/www/pdfapp/tmp

# Install backend dependencies
echo "Installing Python dependencies from backend/requirements.txt..."
python -m pip install --no-cache-dir --requirement backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Verify NLP runtime assets are present from pinned dependencies.
echo "Verifying packaged spaCy model..."
python - <<'PY'
import spacy

try:
    spacy.load("en_core_web_sm")
except OSError:
    raise SystemExit(
        "Missing spaCy model en_core_web_sm. Add the pinned model package to "
        "backend/requirements.txt or bake it into the deployment image; deploys "
        "must not download NLP models at runtime."
    )
PY

# Create necessary directories
mkdir -p backend/data
mkdir -p uploads

# Set permissions
chmod 755 backend/data
chmod 755 uploads

echo "Backend deployment complete."
echo ""
echo "Production environment was supplied from the secure remote .env."
