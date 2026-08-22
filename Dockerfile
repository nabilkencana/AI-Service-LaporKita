# ==============================================================================
# LaporKita AI Service — Production Dockerfile
# Self-contained container with preloaded YOLOv11 & XGBoost models
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_ENV=production \
    CLASSIFICATION_MODEL_PATH=models/yolov11-cls-laporkita.pt \
    XGBOOST_MODEL_PATH=models/xgboost-flood-risk.json

WORKDIR /app

# Install minimal runtime libraries (libglib / libgl for OpenCV headless, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies with CPU-optimized PyTorch
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy application source code and model weights
COPY app/ ./app/
COPY models/ ./models/

EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start ASGI application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
