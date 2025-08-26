FROM python:3.13.7-alpine

WORKDIR /app

# Install system dependencies for Alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Add entrypoint script and make it executable
RUN chmod +x /app/entrypoint.sh

# Create non-root user (Alpine style)
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/', timeout=10)"

# Use entrypoint script for dynamic worker configuration
ENTRYPOINT ["/app/entrypoint.sh"]