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
COPY scripts/ scripts/

RUN chmod +x /app/scripts/start.sh

# Create store directory
RUN mkdir -p /data/store

ENV STORE_DIR=/data/store
ENV PYTHONPATH=/app/src:/app

EXPOSE 8000

# Start via start.sh (auto-binds to $PORT and spawns background ingest worker)
CMD ["/app/scripts/start.sh"]
