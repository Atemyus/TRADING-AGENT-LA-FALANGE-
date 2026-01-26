# Prometheus Trading Platform - Backend Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

# Set work directory
WORKDIR /app

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libfontconfig1 \
    libfreetype6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for smaller image)
RUN playwright install chromium && \
    playwright install-deps chromium || true

# Copy application code
COPY . .

# Create non-root user and set permissions for Playwright
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/.playwright || true
USER appuser

# Expose port (Railway uses $PORT)
EXPOSE 8000

# Health check disabled for Railway (uses its own)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application with dynamic PORT from Railway
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
