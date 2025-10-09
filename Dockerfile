# Lightweight Dockerfile for Adobe Hackathon
FROM python:3.11-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy pre-built frontend (build locally first)
COPY frontend/dist ./frontend/dist

# Copy backend and install dependencies
COPY backend/ ./backend/
COPY backend/app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p data/docs

# Expose port
EXPOSE 8080

# Environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Start command
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
