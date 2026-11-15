FROM python:3.12-slim

LABEL maintainer="Durga Venkata Prasad Rapeti <rdvprasad36@gmail.com>"
LABEL description="MonsoonDelta — ECMWF IFS/AIFS precipitation forecast revision app"

# System dependencies (eccodes for GRIB reading)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libeccodes-dev \
    libeccodes-tools \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/     src/
COPY api/     api/
COPY ingest/  ingest/
COPY frontend/ frontend/

# Create store directory
RUN mkdir -p /data/store

ENV STORE_DIR=/data/store
ENV PYTHONPATH=/app/src:/app

EXPOSE 8000

# Start FastAPI (store is mounted as a volume in production)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
