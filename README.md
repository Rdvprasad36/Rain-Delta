# MonsoonDelta

**Bay of Bengal Precipitation Forecast Revision** — compares ECMWF IFS and AIFS model runs, shows how the forecast has changed across recent runs, and highlights where the two models disagree.

> ⚠️ **This is automated model output. It is not an official forecast or advisory.**
> For official guidance follow [IMD](https://mausam.imd.gov.in) and local authorities.

---

## What it shows

| Feature | Description |
|---|---|
| Latest forecast | 6-hour precipitation totals (mm) for the next 5 days, IFS and AIFS |
| Forecast revision | How the value for one window changed across the last 6 model runs |
| Model disagreement | IFS minus AIFS for the same window, as a number and a map marker |
| Plain language | Template-generated explanation (no free-form AI text) |

## Data source

ECMWF open data — `data.ecmwf.int`, no API key required.
Licence: **CC BY 4.0**. Attribution required (see footer of every page).

```
This service is based on data and products of the European Centre for
Medium-Range Weather Forecasts (ECMWF). © 2026 ECMWF.
Source: www.ecmwf.int. Licence: CC BY 4.0.
ECMWF does not accept any liability for any error or omission in the data.
Values shown are derived (6-hour totals, run differences) — material modified.
```

---

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/Rdvprasad36/Rain-Delta.git
cd Rain-Delta

# 2. Install
pip install -r requirements.txt
pip install -e .      # installs monsoon package in editable mode

# 3. Run tests (offline — no download needed)
pytest tests/test_compute.py tests/test_explain.py tests/test_api.py -v

# 4. Start API (demo mode — no real data needed)
uvicorn api.main:app --reload --port 8000
# Open http://localhost:8000
```

## Run with real ECMWF data

```bash
# Install GRIB dependencies
pip install ecmwf-opendata cfgrib xarray

# Phase 1: inspect a real GRIB file (run on your machine)
python scripts/inspect_tp.py

# Ingest latest run
python -m ingest.run

# API serves real data automatically
uvicorn api.main:app --port 8000
```

## Docker

```bash
docker-compose up --build
# API: http://localhost:8000
# Ingest runs every 3 h in the ingest service
```

---

## Architecture

```
ECMWF open data (HTTPS, public)
        │
        ▼
  ingest/run.py         ← scheduled every 3 h
  - reads GRIB units, converts to mm
  - crops to region 5–23°N, 78–100°E
  - saves store/{model}/{date}/{cycle}Z/
        │
        ▼
  store/ (14-day retention)
        │
        ▼
  api/main.py (FastAPI)
  - /api/latest, /api/revision, /api/disagreement, /api/health
  - 5-min cache; 60 req/min rate limit; never parses GRIB in request
        │
        ▼
  frontend/ (static HTML + Three.js + Chart.js + Leaflet)
  - Disclaimer + attribution on every page
```

## Maths (hand-verified examples)

### 6-hour window total
```
tp is cumulative from forecast start.
W(s) = tp(s) − tp(s − 6h)   [mm]

IFS  example: tp(12h)=0.002 m, tp(18h)=0.005 m → W(18h)=3.0 mm ✓
AIFS example: tp(12h)=2.0 kg/m², tp(18h)=5.0 kg/m² → W(18h)=3.0 mm ✓
```

### Revision
```
Runs 00Z→06Z→12Z: 4.0, 10.0, 7.0 mm for the same window.
Latest change = 7.0 − 10.0 = −3.0 mm  (down)  ✓
Range         = 10.0 − 4.0 = 6.0 mm             ✓
```

### Disagreement
```
IFS=7.0 mm, AIFS=3.0 mm → diff=+4.0 mm (IFS wetter)  ✓
```

## Tests

```bash
pytest -v                      # all tests
pytest tests/test_compute.py   # unit tests (PRD hand examples)
pytest tests/test_explain.py   # banned-word enforcement
pytest tests/test_api.py       # API schema + disclaimer
```

All tests run offline on fixture data. Never download in tests.

## Known limits

- 0.25° grid (~28 km). No local terrain or urban effects.
- ECMWF retains open data ~2–4 days. MonsoonDelta stores 14 days internally.
- AIFS is experimental; uncertainty properties differ from IFS.
- No ensemble probabilities.

## Deployment (Railway / Render / Fly.io)

1. Push to GitHub (this repo).
2. Connect repo to your host.
3. Set environment variables:
   - `STORE_DIR=/data/store`
   - `ECMWF_SOURCE=ecmwf`
   - `RETENTION_DAYS=14`
4. Mount persistent disk at `/data/store`.
5. Set ingest cron: `python -m ingest.run` every 3 hours.
6. Health check: `GET /api/health`.

See [DECISIONS.md](DECISIONS.md) for all design choices.

## Licence

Application code: **MIT** (see below).
ECMWF data: **CC BY 4.0** — attribution required on every page (already included).

```
MIT License
Copyright (c) 2026 Durga Venkata Prasad Rapeti
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```
