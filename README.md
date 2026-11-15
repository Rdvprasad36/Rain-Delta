# MonsoonDelta 🌧️

**Bay of Bengal Precipitation Forecast Revision Platform**  
*Prepared for Durga Venkata Prasad Rapeti — QUEST Lab pre-doctoral Project 1*

[![MonsoonDelta CI](https://github.com/Rdvprasad36/Rain-Delta/actions/workflows/ci.yml/badge.svg)](https://github.com/Rdvprasad36/Rain-Delta/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-green.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)

> ⚠️ **Mandatory Public Notice**:  
> *This is automated model output from ECMWF IFS and AIFS. It is not an official forecast or advisory. For official warnings and guidance, follow the India Meteorological Department (IMD) and local disaster management authorities.*

---

## 1. Overview & Core Features

MonsoonDelta tracks, revisions, and compares numerical weather prediction precipitation forecasts across cycles for the **Bay of Bengal** region (default focus: **Visakhapatnam ~17.7°N, 83.2°E**):

1. **Latest Forecast**: Synchronized 6-hour precipitation totals ($mm$) across the next 5 days for ECMWF's operational **IFS** (Integrated Forecasting System) and **AIFS** (AI-based Integrated Forecasting System).
2. **Forecast Revision Engine**: For any fixed 6-hour valid window, computes run-to-run drift across the last $N$ model cycles (latest change, full range, and direction trend: `up`, `down`, or `steady`).
3. **Model Disagreement**: Quantifies spatial and point-level delta ($D = \text{IFS} - \text{AIFS}$), pinpointing which model is wetter without deceptive relative percentages on trace amounts ($<1.0\,mm$).
4. **Deterministic Plain-Language Generator**: Rule-based template synthesizer that converts metrics into clear natural language, verified by CI against alarmist or unauthorized warning phrases.
5. **Interactive 3D Glassmorphic Interface**: High-performance UI featuring a real-time **Three.js** 3D globe and dynamic rainfall particle field, **Chart.js** forecast bar and revision trend lines, and a **Leaflet** divergence map.

---

## 2. System Architecture

### 2.1 Complete System Flow

```
                      ┌────────────────────────────────────────┐
                      │    ECMWF Open Data (data.ecmwf.int)    │
                      │  Public HTTPS • CC BY 4.0 • Zero Keys  │
                      └──────────────────┬─────────────────────┘
                                         │
                   Scheduled Ingest Job (Every 3 Hours)
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │                ingest/run.py                   │
                 │  1. Check remote cycle against manifest.json   │
                 │  2. Download GRIB (IFS: 0p25, AIFS: 0p25)      │
                 │  3. GRIB Inspection: verify units key          │
                 │  4. Spatial Crop: 5–23°N, 78–100°E (Bay of B.) │
                 │  5. 14-Day Rolling History Retention Purge    │
                 └───────────────────────┬────────────────────────┘
                                         │
                              Writes compressed arrays
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │       Persistent Store (/data/store)           │
                 │  ├── manifest.json                             │
                 │  └── store/{model}/{YYYYMMDD}/{cycle}Z/        │
                 │      ├── tp_mm.npy  (n_steps × n_lat × n_lon)  │
                 │      ├── steps.npy, lats.npy, lons.npy         │
                 │      └── meta.json                             │
                 └───────────────────────┬────────────────────────┘
                                         │
                          Reads on-demand (FastAPI)
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │                 FastAPI Service                │
                 │  • /api/latest        • /api/health            │
                 │  • /api/revision      • /api/disagreement      │
                 │  ───────────────────────────────────────────── │
                 │  • In-Memory TTL Cache (5 min)                 │
                 │  • Rate Limiter (60 req/min/IP)                │
                 │  • Fallback Demo Synthesizer (instant preview) │
                 │  • Never parses GRIB inside HTTP requests      │
                 └───────────────────────┬────────────────────────┘
                                         │
                               JSON + Static Assets
                                         ▼
                 ┌────────────────────────────────────────────────┐
                 │          Animated 3D Web UI (frontend/)        │
                 │  • Three.js Interactive Rotating 3D Globe      │
                 │  • Three.js Atmospheric Rain Particle Canvas   │
                 │  • Chart.js Interactive Bar & Line Visualizers │
                 │  • Leaflet Model Divergence Geo-Map            │
                 │  • Permanent Disclaimer & Attribution in DOM   │
                 └────────────────────────────────────────────────┘
```

### 2.2 Functional Layer Boundaries

| Layer | Module | Responsibility | Invariant / Isolation Rule |
|---|---|---|---|
| **Compute** | `src/monsoon/compute.py` | Unit conversions, accumulation math, revision stats, spatial interpolation | **Pure math**: No filesystem or network I/O. Runs 100% offline. |
| **Explain** | `src/monsoon/explain.py` | Deterministic template-based sentences | **Banned-word enforcement**: Rejects terms like `warning`, `alert`, `evacuate`. |
| **Constants** | `src/monsoon/constants.py` | Geobox bounds, tolerances, attribution | Single source of truth for calculations and legal texts. |
| **Ingest** | `ingest/run.py` | Downloads GRIBs, crops Bay of Bengal box, updates manifest | Scheduled asynchronously; never invoked during an API request. |
| **API** | `api/main.py` | FastAPI REST endpoints with caching and rate limits | Reads precomputed `.npy` store only. |
| **Frontend** | `frontend/` | Static HTML5, Three.js, Chart.js, Leaflet | Zero build step. Mobile-first responsive design down to 360px. |

---

## 3. Mathematical Foundations & Hand Examples

All mathematical routines are derived from the project specification and verified against hand calculations in unit tests (`tests/test_compute.py`).

### 3.1 Unit Normalization
* **IFS**: Parameter `tp` (paramId `228`) is reported in **metres** ($m$).  
  $$\text{depth}\,(mm) = \text{value}\,(m) \times 1000$$
* **AIFS**: Parameter `tp` (paramId `228228`) is reported in **$\text{kg m}^{-2}$**.  
  $$\text{depth}\,(mm) = \text{value}\,(\text{kg m}^{-2}) \times 1.0 \quad (\text{for liquid water at } 1000\,\text{kg/m}^3)$$
* **Guard rule**: Any unexpected unit string triggers an immediate `ValueError`.

### 3.2 6-Hour Window Accumulation
Total precipitation is cumulative from forecast inception ($t=0$):
$$W(s) = tp(s) - tp(s - 6) \quad \text{with} \quad tp(0) = 0$$

*Hand-Checked Example*:
- IFS: $tp(12h) = 0.002\,m$, $tp(18h) = 0.005\,m$ $\implies W(18h) = 5.0 - 2.0 = \mathbf{3.0\,mm}$
- AIFS: $tp(12h) = 2.0\,\text{kg/m}^2$, $tp(18h) = 5.0\,\text{kg/m}^2$ $\implies W(18h) = 5.0 - 2.0 = \mathbf{3.0\,mm}$

### 3.3 Forecast Revision
For valid time window $V$, across runs $r_1, r_2, \dots, r_k$:
- $\text{Latest Change} = A_{\text{latest}} - A_{\text{previous}}$
- $\text{Range} = \max(A_r) - \min(A_r)$
- $\text{Direction} = \begin{cases} \text{steady} & \text{if } |\text{Latest Change}| < 0.5\,mm \\ \text{up} & \text{if } \text{Latest Change} \ge +0.5\,mm \\ \text{down} & \text{if } \text{Latest Change} \le -0.5\,mm \end{cases}$

*Hand-Checked Example*:  
Runs $00Z \to 06Z \to 12Z$ yield $4.0\,mm, 10.0\,mm, 7.0\,mm$:
$$\text{Latest Change} = 7.0 - 10.0 = \mathbf{-3.0\,mm\,(down)}, \quad \text{Range} = 10.0 - 4.0 = \mathbf{6.0\,mm}$$

### 3.4 Disagreement
$$D = \text{IFS} - \text{AIFS}$$
Relative percentage difference is withheld when both $\text{IFS} < 1.0\,mm$ and $\text{AIFS} < 1.0\,mm$ to prevent misleading ratios on trace amounts.

---

## 4. Complete Deployment Guidelines

MonsoonDelta is designed for high reliability, minimal resource footprint, and zero operational cost. Below are step-by-step instructions for popular hosting environments.

### 4.1 Deployment Architecture Summary

| Component | Port / Command | Resource Target |
|---|---|---|
| **Web Service** | `uvicorn api.main:app --host 0.0.0.0 --port 8000` | 0.5 CPU, 512 MB RAM |
| **Ingest Worker** | `python -m ingest.run` (Runs every 3h) | 1.0 CPU, 1024 MB RAM (transient) |
| **Storage** | `/data/store` (Persistent Volume or Directory) | ~200–500 MB (14-day history) |

---

### Option A: Cloud Deployment on Render.com (Recommended Free/Low Cost)

Render provides direct GitHub repository integration.

1. **Fork or Push** the repository to your GitHub account: `https://github.com/Rdvprasad36/Rain-Delta`.
2. **Create Web Service**:
   - Go to [dashboard.render.com](https://dashboard.render.com) $\to$ **New** $\to$ **Web Service**.
   - Connect repository `Rdvprasad36/Rain-Delta`.
   - **Environment**: `Docker` (Render auto-detects `Dockerfile`).
   - **Plan**: Free or Starter.
3. **Attach Persistent Disk**:
   - In your Web Service settings, navigate to **Disks** $\to$ **Add Disk**.
   - Name: `monsoon-store`
   - Mount Path: `/data/store`
   - Size: `1 GB`
4. **Environment Variables**:
   Add the following in **Environment**:
   ```ini
   STORE_DIR=/data/store
   ECMWF_SOURCE=ecmwf
   RETENTION_DAYS=14
   REGION_LAT_MIN=5.0
   REGION_LAT_MAX=23.0
   REGION_LON_MIN=78.0
   REGION_LON_MAX=100.0
   ```
5. **Set up Scheduled Ingest**:
   - Go to **New** $\to$ **Cron Job**.
   - Connect the same repository.
   - Command: `python -m ingest.run`
   - Schedule: `0 */3 * * *` (every 3 hours).
   - Mount the same disk or run ingest within the container loop.

---

### Option B: Deployment on Railway.app

1. Go to [railway.app](https://railway.app) $\to$ **New Project** $\to$ **Deploy from GitHub repo**.
2. Select `Rdvprasad36/Rain-Delta`.
3. In **Settings** $\to$ **Volumes**:
   - Click **Add Volume** with mount path `/data/store`.
4. In **Variables**, set:
   ```ini
   PORT=8000
   STORE_DIR=/data/store
   ECMWF_SOURCE=ecmwf
   RETENTION_DAYS=14
   ```
5. Railway automatically builds the `Dockerfile` and attaches the healthcheck at `/api/health`.

---

### Option C: Production Docker Compose (VPS / EC2 / Droplet)

Deploy directly on any Linux server with Docker and Docker Compose installed:

```bash
# 1. SSH into your host
ssh user@your-server-ip

# 2. Clone repository
git clone https://github.com/Rdvprasad36/Rain-Delta.git /opt/rain-delta
cd /opt/rain-delta

# 3. Create persistent directory
sudo mkdir -p /var/monsoon/store
sudo chown -R 1000:1000 /var/monsoon/store

# 4. Start the stack (API + Ingest background loop)
docker compose up -d --build

# 5. Verify containers are healthy
docker compose ps
curl -s http://localhost:8000/api/health | jq .
```

To configure Nginx reverse-proxy with SSL:
```nginx
server {
    server_name monsoon.yourdomain.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### Option D: Fly.io Deployment

```bash
# 1. Install flyctl & authenticate
fly auth login

# 2. Create the application configuration
fly launch --no-deploy

# 3. Create persistent storage volume
fly volumes create monsoon_data --size 1 --region sin

# 4. In fly.toml, mount volume:
# [mounts]
#   source = "monsoon_data"
#   destination = "/data/store"

# 5. Deploy
fly deploy
```

---

## 5. Configuration Reference

All settings are configured through standard environment variables with sensible defaults:

| Variable | Default | Purpose |
|---|---|---|
| `STORE_DIR` | `<repo>/store` | Path to directory storing `manifest.json` and `.npy` cycle files. |
| `ECMWF_SOURCE` | `ecmwf` | Open data distribution source: `ecmwf`, `aws`, or `google`. |
| `RETENTION_DAYS` | `14` | Rolling window of cycles retained locally before pruning. |
| `REGION_LAT_MIN` | `5.0` | Southern latitude boundary (°N). |
| `REGION_LAT_MAX` | `23.0` | Northern latitude boundary (°N). |
| `REGION_LON_MIN` | `78.0` | Western longitude boundary (°E). |
| `REGION_LON_MAX` | `100.0` | Eastern longitude boundary (°E). |

---

## 6. Local Development & Testing

### 6.1 Running the Full Test Suite

The test suite runs **100% offline** using verified fixtures. No network access or credentials are required:

```bash
# Run all 66 test assertions
python -m pytest tests/test_compute.py tests/test_explain.py tests/test_api.py -v
```

### 6.2 Running the Application Locally

```bash
# 1. Install Python packages
pip install -r requirements.txt
pip install -e .

# 2. Inspect ECMWF GRIB parameters (Phase 1 diagnostic)
python scripts/inspect_tp.py

# 3. Start local development server (serves 3D UI + API with instant demo fallback)
uvicorn api.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 7. Operational Health & Monitoring

The healthcheck endpoint `/api/health` reports status, latest ingested cycle timestamps, and staleness detection:

```json
{
  "disclaimer": "This is automated model output from ECMWF IFS and AIFS...",
  "attribution": "This service is based on data and products of ECMWF...",
  "status": "ok",
  "models": {
    "ifs": {
      "latest_run_utc": "2026-11-15T06:00:00Z",
      "stale": false
    },
    "aifs": {
      "latest_run_utc": "2026-11-15T00:00:00Z",
      "stale": false
    }
  }
}
```

- When the latest cycle is $>9$ hours old, `"stale": true` is flagged, activating the top-level stale warning banner on the UI.
- Use any external uptime monitor (e.g., UptimeRobot, BetterUptime) pointed at `/api/health` with a 200 OK check.

---

## 8. Attribution & Licensing

### 8.1 ECMWF Data Attribution (CC BY 4.0)
> *This service is based on data and products of the European Centre for Medium-Range Weather Forecasts (ECMWF). © 2026 ECMWF. Source: [www.ecmwf.int](https://www.ecmwf.int). Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ECMWF does not accept any liability for any error or omission in the data, their availability, or for any loss or damage arising from their use. Values shown are derived (6-hour totals, differences between runs), so the material has been modified.*

### 8.2 Application Source Code License
The application source code is distributed under the **MIT License**:

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

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
