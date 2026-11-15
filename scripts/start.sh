#!/bin/sh
set -e

# Run background ingest worker loop if enabled
if [ "${ENABLE_INGEST_WORKER:-true}" = "true" ]; then
  echo "[MonsoonDelta] Spawning background ingest worker (every 3 hours)..."
  (
    while true; do
      echo "[MonsoonDelta Ingest] Checking ECMWF open data at $(date -u)..."
      python -m ingest.run || echo "[MonsoonDelta Ingest] Cycle check finished."
      sleep 10800
    done
  ) &
fi

PORT_TO_USE="${PORT:-8000}"
echo "[MonsoonDelta] Starting FastAPI server on port ${PORT_TO_USE}..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT_TO_USE}" --workers 1
