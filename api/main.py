"""
MonsoonDelta FastAPI application.

Routes
------
GET /api/latest        – latest 6-hour window totals for IFS and AIFS
GET /api/revision      – revision statistics for one window
GET /api/disagreement  – IFS vs AIFS difference map + point value
GET /api/health        – newest run time per model, stale flag

Principles
----------
- Never parses GRIB inside a web request.
- Reads only from the precomputed store written by ingest/run.py.
- Returns disclaimer and attribution strings in every response.
- Simple in-memory cache (5 min TTL); simple rate limit (60 req/min/IP).
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from monsoon.compute import (
    area_mean,
    disagreement as compute_disagreement,
    revision as compute_revision,
    window_totals,
)
from monsoon.explain import explain_all
from monsoon.constants import (
    ATTRIBUTION,
    DEFAULT_LAT,
    DEFAULT_LON,
    DEFAULT_NAME,
    DISCLAIMER,
    STALE_THRESHOLD_HOURS,
    WINDOW_HOURS,
    MAX_RUNS_FOR_REVISION,
)

log = logging.getLogger(__name__)

STORE_DIR = Path(os.environ.get("STORE_DIR", Path(__file__).parent.parent / "store"))
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(
    title="MonsoonDelta API",
    description="ECMWF IFS/AIFS precipitation forecast revision for Bay of Bengal.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300  # seconds


def cache_get(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None


def cache_set(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ── Simple rate limiter ───────────────────────────────────────────────────────
_request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 60  # requests per minute


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    _request_counts[ip] = [t for t in _request_counts[ip] if now - t < 60]
    if len(_request_counts[ip]) >= RATE_LIMIT:
        return False
    _request_counts[ip].append(now)
    return True


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    if request.url.path.startswith("/api/") and not check_rate_limit(ip):
        return JSONResponse(
            {"error": "Rate limit exceeded. Max 60 requests/minute."},
            status_code=429,
        )
    response = await call_next(request)
    response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL}"
    return response


# ── Store reading helpers ─────────────────────────────────────────────────────

def load_manifest() -> dict[str, Any]:
    manifest_path = STORE_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"runs": {}}
    with open(manifest_path) as f:
        return json.load(f)


def latest_run_for_model(manifest: dict, model: str) -> dict | None:
    runs = {
        k: v for k, v in manifest["runs"].items()
        if v.get("model") == model
    }
    if not runs:
        return None
    latest_key = max(runs, key=lambda k: runs[k].get("run_time_utc", ""))
    return {"key": latest_key, **runs[latest_key]}


def load_run_data(model: str, date_str: str, cycle: int) -> dict | None:
    run_dir = STORE_DIR / model / date_str / f"{cycle:02d}Z"
    if not run_dir.exists():
        return None
    try:
        return {
            "tp_mm": np.load(run_dir / "tp_mm.npy"),
            "steps": np.load(run_dir / "steps.npy"),
            "lats": np.load(run_dir / "lats.npy"),
            "lons": np.load(run_dir / "lons.npy"),
        }
    except FileNotFoundError:
        log.warning("Missing npy files in %s", run_dir)
        return None


def is_stale(run_time_utc: str) -> bool:
    try:
        rt = datetime.fromisoformat(run_time_utc.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - rt).total_seconds() / 3600
        return age_hours > STALE_THRESHOLD_HOURS
    except Exception:
        return True


def _base_response() -> dict:
    return {
        "disclaimer": DISCLAIMER,
        "attribution": ATTRIBUTION,
    }


def _mock_data_for_model(model: str, lat: float, lon: float) -> list[dict]:
    """Return synthetic data when store is empty (demo / first deploy)."""
    import random
    random.seed(hash(f"{model}{lat}{lon}") % 999)
    now = datetime.now(timezone.utc)
    windows = []
    cum = 0.0
    for step in range(6, 121, 6):
        total = round(random.uniform(0.0, 8.0), 2)
        cum += total
        valid_time = now + timedelta(hours=step)
        windows.append({
            "step_end": step,
            "step_start": step - 6,
            "total_mm": total,
            "valid_time_utc": valid_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return windows


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Return newest run time per model and stale flags."""
    manifest = load_manifest()
    result = _base_response()
    models = ["ifs", "aifs"]
    result["models"] = {}
    for m in models:
        run = latest_run_for_model(manifest, m)
        if run:
            result["models"][m] = {
                "latest_run_utc": run.get("run_time_utc"),
                "stale": is_stale(run.get("run_time_utc", "")),
            }
        else:
            result["models"][m] = {
                "latest_run_utc": None,
                "stale": True,
                "note": "No data yet. Run ingest/run.py to populate the store.",
            }
    result["status"] = "ok"
    return result


@app.get("/api/latest")
def latest_forecast(
    lat: float = Query(DEFAULT_LAT, description="Latitude (°N)"),
    lon: float = Query(DEFAULT_LON, description="Longitude (°E)"),
):
    """Latest 6-hour window totals for IFS and AIFS at a point."""
    cache_key = f"latest:{lat:.2f}:{lon:.2f}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    manifest = load_manifest()
    result = _base_response()
    result["location"] = {"lat": lat, "lon": lon}
    result["windows"] = {}
    result["stale"] = False
    result["demo_mode"] = False

    for model in ["ifs", "aifs"]:
        run_meta = latest_run_for_model(manifest, model)
        if run_meta is None:
            # Demo mode: generate synthetic data
            result["demo_mode"] = True
            result["windows"][model] = {
                "run_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z"),
                "stale": True,
                "data": _mock_data_for_model(model, lat, lon),
                "note": "Demo data — run ingest/run.py for real ECMWF data.",
            }
            continue

        run_data = load_run_data(
            model, run_meta["date"], run_meta["cycle"]
        )
        if run_data is None:
            result["windows"][model] = {"error": "Data files missing."}
            continue

        # Compute area mean for each step, then window totals
        point_values = []
        for i, step in enumerate(run_data["steps"]):
            val = area_mean(
                run_data["tp_mm"][i],
                run_data["lats"],
                run_data["lons"],
                lat, lon,
            )
            point_values.append(val)

        windows = window_totals(point_values, run_data["steps"].tolist(), WINDOW_HOURS)

        # Add valid times
        run_dt = datetime.fromisoformat(run_meta["run_time_utc"].replace("Z", "+00:00"))
        for w in windows:
            w["valid_time_utc"] = (run_dt + timedelta(hours=w["step_end"])).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        stale = is_stale(run_meta["run_time_utc"])
        if stale:
            result["stale"] = True

        result["windows"][model] = {
            "run_time_utc": run_meta["run_time_utc"],
            "stale": stale,
            "data": windows,
        }

    cache_set(cache_key, result)
    return result


@app.get("/api/revision")
def forecast_revision(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    step_end: int = Query(24, description="Forecast step (hours) for the target window end"),
    n_runs: int = Query(MAX_RUNS_FOR_REVISION, description="Number of recent runs to include"),
    model: str = Query("ifs", description="Model: ifs or aifs"),
):
    """Revision statistics across last N runs for one fixed window."""
    cache_key = f"revision:{model}:{lat:.2f}:{lon:.2f}:{step_end}:{n_runs}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    manifest = load_manifest()
    result = _base_response()
    result["model"] = model
    result["step_end"] = step_end
    result["location"] = {"lat": lat, "lon": lon}

    # Sort all runs for this model, newest first
    all_runs = sorted(
        [
            (k, v) for k, v in manifest["runs"].items()
            if v.get("model") == model
        ],
        key=lambda kv: kv[1].get("run_time_utc", ""),
        reverse=True,
    )[:n_runs]
    all_runs.reverse()  # oldest→newest for revision()

    if len(all_runs) < 1:
        # Demo mode
        result["demo_mode"] = True
        demo_values = [4.0, None, 10.0, 7.0]
        rev = compute_revision(demo_values)
        result["revision"] = rev
        result["run_times"] = ["demo"]
        expl = explain_all(
            latest_ifs_mm=rev["latest"] or 0.0,
            latest_aifs_mm=rev["latest"] or 0.0,
            direction=rev["direction"],
            latest_change=rev["latest_change"],
            range_mm=rev["range_mm"],
            n_runs=rev["n_runs"],
            diff_mm=0.0,
            wetter_model="equal",
            close=True,
        )
        result["explanation"] = expl
        return result

    values_by_run = []
    run_times = []
    for key, meta in all_runs:
        rd = load_run_data(model, meta["date"], meta["cycle"])
        if rd is None:
            values_by_run.append(None)
            run_times.append(meta.get("run_time_utc"))
            continue

        steps = rd["steps"].tolist()
        if step_end not in steps:
            values_by_run.append(None)  # run doesn't cover this window
            run_times.append(meta.get("run_time_utc"))
            continue

        point_vals = [
            area_mean(rd["tp_mm"][i], rd["lats"], rd["lons"], lat, lon)
            for i, s in enumerate(steps)
        ]
        wts = window_totals(point_vals, steps, WINDOW_HOURS)
        wt_map = {w["step_end"]: w["total_mm"] for w in wts}
        values_by_run.append(wt_map.get(step_end))
        run_times.append(meta.get("run_time_utc"))

    rev = compute_revision(values_by_run)
    result["revision"] = rev
    result["run_times"] = run_times

    cache_set(cache_key, result)
    return result


@app.get("/api/disagreement")
def model_disagreement(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    step_end: int = Query(24, description="Forecast step (hours) for the target window"),
):
    """IFS minus AIFS disagreement for the same window, as a point value."""
    cache_key = f"disagree:{lat:.2f}:{lon:.2f}:{step_end}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    manifest = load_manifest()
    result = _base_response()
    result["step_end"] = step_end
    result["location"] = {"lat": lat, "lon": lon}

    values = {}
    for model in ["ifs", "aifs"]:
        run_meta = latest_run_for_model(manifest, model)
        if run_meta is None:
            import random
            random.seed(hash(f"{model}{step_end}") % 1234)
            values[model] = round(random.uniform(0.5, 10.0), 2)
            result["demo_mode"] = True
            continue

        rd = load_run_data(model, run_meta["date"], run_meta["cycle"])
        if rd is None:
            raise HTTPException(500, f"Data missing for {model}")

        steps = rd["steps"].tolist()
        point_vals = [
            area_mean(rd["tp_mm"][i], rd["lats"], rd["lons"], lat, lon)
            for i, _ in enumerate(steps)
        ]
        wts = window_totals(point_vals, steps, WINDOW_HOURS)
        wt_map = {w["step_end"]: w["total_mm"] for w in wts}
        values[model] = wt_map.get(step_end)

    if values.get("ifs") is None or values.get("aifs") is None:
        raise HTTPException(422, "Window not covered by one or both models for this step.")

    dis = compute_disagreement(values["ifs"], values["aifs"])
    result["disagreement"] = dis

    expl = explain_all(
        latest_ifs_mm=values["ifs"],
        latest_aifs_mm=values["aifs"],
        direction="steady",
        latest_change=0.0,
        range_mm=0.0,
        n_runs=1,
        diff_mm=dis["diff_mm"],
        wetter_model=dis["wetter_model"],
        close=dis["close"],
    )
    result["explanation"] = expl

    cache_set(cache_key, result)
    return result


# ── Serve static frontend ────────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
