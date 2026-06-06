# ──────────────────────────────────────────────────────────────────
# Stage 1 — dependency builder
# Uses a full Python image so pip can compile any C-extension wheels.
# ──────────────────────────────────────────────────────────────────
FROM python:slim-trixie AS builder
WORKDIR /build
# Install build tools needed for any compiled dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into an isolated prefix so we can copy only the libs
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ──────────────────────────────────────────────────────────────────
# Stage 2 — lean runtime image
# ──────────────────────────────────────────────────────────────────
FROM python:slim-trixie AS runtime
LABEL Product="FuelTrackAPI"
LABEL Version="0.0.1"
LABEL Maintainer="TkM"
LABEL Description="Fuel Track API"

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app
# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY ./service/main.py .

# Switch to non-root user
USER appuser

# ── Environment variable defaults (override at runtime via -e or .env) ──
ENV PORT=8000 \
    AWS_REGION=us-east-1 \
    DYNAMODB_TABLE=FuelEntries \
    ALLOWED_ORIGIN=* \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE ${PORT}

# ── Health check (Docker will mark the container unhealthy if this fails) ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
        "import urllib.request, sys; \
         r = urllib.request.urlopen('http://localhost:${PORT}/health', timeout=4); \
         sys.exit(0 if r.status == 200 else 1)"

# ── Start Uvicorn with production-grade settings ──
CMD ["sh", "-c", \
     "uvicorn main:app \
        --host 0.0.0.0 \
        --port ${PORT} \
        --workers 2 \
        --log-level info \
        --access-log \
        --proxy-headers \
        --forwarded-allow-ips='*'"]