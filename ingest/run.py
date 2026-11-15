"""
MonsoonDelta ingest job.

Fetches latest IFS and AIFS tp GRIB data from ECMWF open data,
crops to the configured region box, verifies units, and saves
per-run compressed numpy files.

Run schedule: every 3 hours via cron / GitHub Actions.
Idempotent: skips runs already present in manifest.json.

NO secrets, NO API keys required.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
STORE_DIR = Path(os.environ.get("STORE_DIR", Path(__file__).parent.parent / "store"))
MANIFEST_PATH = STORE_DIR / "manifest.json"

# ── Config from environment ───────────────────────────────────────────────────
SOURCE = os.environ.get("ECMWF_SOURCE", "ecmwf")  # ecmwf | aws | google
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "14"))
REGION_LAT_MIN = float(os.environ.get("REGION_LAT_MIN", "5.0"))
REGION_LAT_MAX = float(os.environ.get("REGION_LAT_MAX", "23.0"))
REGION_LON_MIN = float(os.environ.get("REGION_LON_MIN", "78.0"))
REGION_LON_MAX = float(os.environ.get("REGION_LON_MAX", "100.0"))


# ── Manifest helpers ──────────────────────────────────────────────────────────

def load_manifest() -> dict[str, Any]:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"runs": {}}


def save_manifest(manifest: dict[str, Any]) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def run_key(model: str, date_str: str, cycle: int) -> str:
    return f"{model}/{date_str}/{cycle:02d}Z"


# ── ECMWF open-data download ──────────────────────────────────────────────────

def fetch_model(
    model: str,
    date_str: str,
    cycle: int,
    steps: list[int],
    target_dir: Path,
) -> dict[str, np.ndarray] | None:
    """
    Download tp GRIB from ECMWF open data, read with cfgrib, crop to region.

    Returns dict with keys: lats, lons, tp_mm (shape: n_steps × n_lat × n_lon),
    steps, units_original, run_time_utc

    Returns None if the file is not available (e.g. run not yet published).
    """
    try:
        from ecmwf.opendata import Client
    except ImportError:
        log.error("ecmwf-opendata not installed. Run: pip install ecmwf-opendata")
        return None

    try:
        import cfgrib
        import xarray as xr
    except ImportError:
        log.error("cfgrib/xarray not installed.")
        return None

    target_dir.mkdir(parents=True, exist_ok=True)
    grib_path = target_dir / "tp.grib2"

    client = Client(source=SOURCE)

    # Determine ECMWF API parameters by model
    if model == "ifs":
        params = dict(
            model="ifs",
            resol="0p25",
            stream="oper",
            type="fc",
            param="tp",
            step=steps,
            time=cycle,
            date=date_str,
        )
    elif model == "aifs":
        params = dict(
            model="aifs-single",
            resol="0p25",
            stream="oper",
            type="fc",
            param="tp",
            step=steps,
            time=cycle,
            date=date_str,
        )
    else:
        raise ValueError(f"Unknown model: {model!r}")

    log.info("Fetching %s run %s %02dZ steps %s ...", model, date_str, cycle, steps)
    try:
        client.retrieve(**params, target=str(grib_path))
    except Exception as exc:
        log.warning("Could not fetch %s %s %02dZ: %s", model, date_str, cycle, exc)
        return None

    # Read GRIB with cfgrib
    try:
        ds_list = cfgrib.open_datasets(str(grib_path))
    except Exception as exc:
        log.error("Failed to read GRIB %s: %s", grib_path, exc)
        return None

    if not ds_list:
        log.error("No datasets found in %s", grib_path)
        return None

    ds = ds_list[0]
    if "tp" not in ds:
        log.error("'tp' variable not found in GRIB. Variables: %s", list(ds))
        return None

    tp_var = ds["tp"]

    # ── Units verification ─────────────────────────────────────────────────────
    from monsoon.constants import KNOWN_UNITS
    units = str(tp_var.attrs.get("units", "UNKNOWN")).strip()
    if units not in KNOWN_UNITS:
        raise ValueError(
            f"[INGEST] Unknown tp units '{units}' in {grib_path}. "
            f"Known: {list(KNOWN_UNITS)}. "
            "Update KNOWN_UNITS in constants.py after verifying."
        )

    from monsoon.compute import to_mm

    # ── Region crop ────────────────────────────────────────────────────────────
    lats = tp_var.latitude.values
    lons = tp_var.longitude.values
    lat_mask = (lats >= REGION_LAT_MIN) & (lats <= REGION_LAT_MAX)
    lon_mask = (lons >= REGION_LON_MIN) & (lons <= REGION_LON_MAX)

    tp_region = tp_var.values[..., lat_mask, :]
    tp_region = tp_region[..., lon_mask]
    lats_region = lats[lat_mask]
    lons_region = lons[lon_mask]

    # Convert to mm
    original_shape = tp_region.shape
    tp_mm = to_mm(tp_region.reshape(-1), units).reshape(original_shape)

    return {
        "lats": lats_region,
        "lons": lons_region,
        "tp_mm": tp_mm,  # shape (n_steps, n_lat, n_lon)
        "steps": np.array(steps, dtype=int),
        "units_original": units,
        "run_time_utc": f"{date_str}T{cycle:02d}:00:00Z",
    }


# ── Save run to store ─────────────────────────────────────────────────────────

def save_run(model: str, date_str: str, cycle: int, data: dict) -> Path:
    run_dir = STORE_DIR / model / date_str / f"{cycle:02d}Z"
    run_dir.mkdir(parents=True, exist_ok=True)
    for key, val in data.items():
        if isinstance(val, np.ndarray):
            np.save(run_dir / f"{key}.npy", val)
        else:
            with open(run_dir / "meta.json", "w") as f:
                # Collect all string metadata
                meta = {k: v for k, v in data.items() if not isinstance(v, np.ndarray)}
                json.dump(meta, f, indent=2)
                break
    log.info("Saved run %s/%s/%02dZ to %s", model, date_str, cycle, run_dir)
    return run_dir


# ── Retention cleanup ─────────────────────────────────────────────────────────

def purge_old_runs(manifest: dict[str, Any]) -> dict[str, Any]:
    """Remove runs older than RETENTION_DAYS from store and manifest."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    to_delete = []
    for key in list(manifest["runs"].keys()):
        run_time_str = manifest["runs"][key].get("run_time_utc", "")
        try:
            run_time = datetime.fromisoformat(run_time_str.replace("Z", "+00:00"))
            if run_time < cutoff:
                to_delete.append(key)
        except ValueError:
            pass

    for key in to_delete:
        del manifest["runs"][key]
        # Remove from disk
        model, date_str, cycle_str = key.split("/")
        run_dir = STORE_DIR / model / date_str / cycle_str
        if run_dir.exists():
            import shutil
            shutil.rmtree(run_dir)
            log.info("Purged old run: %s", key)

    return manifest


# ── Main entry point ──────────────────────────────────────────────────────────

def ingest_latest() -> None:
    """
    Main ingest function. Called by the scheduler every 3 hours.
    1. Load manifest
    2. Determine the latest available run per model
    3. Skip if already in manifest
    4. Download, verify, crop, save
    5. Update manifest
    6. Purge old runs
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log.info("=== MonsoonDelta ingest started ===")

    manifest = load_manifest()
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y%m%d")

    # IFS cycles: 00, 06, 12, 18 UTC; steps multiples of 6 up to 240 h
    # AIFS cycles: 00, 12 UTC; steps 6-hourly up to 360 h
    models = {
        "ifs": {
            "cycles": [0, 6, 12, 18],
            "steps": list(range(6, 145, 6)),  # 0–144 h (conservative; check DECISIONS.md)
        },
        "aifs": {
            "cycles": [0, 12],
            "steps": list(range(6, 361, 6)),
        },
    }

    for model, cfg in models.items():
        for cycle in reversed(cfg["cycles"]):  # newest first
            key = run_key(model, date_str, cycle)
            if key in manifest["runs"]:
                log.info("Already stored: %s — skipping.", key)
                continue

            if today.hour < cycle:
                log.info("Run %s not yet published (current hour %d UTC).", key, today.hour)
                continue

            data = fetch_model(model, date_str, cycle, cfg["steps"], STORE_DIR / "raw")
            if data is None:
                continue

            save_run(model, date_str, cycle, data)
            manifest["runs"][key] = {
                "model": model,
                "date": date_str,
                "cycle": cycle,
                "run_time_utc": data["run_time_utc"],
                "n_steps": int(len(data["steps"])),
                "units_original": data["units_original"],
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
            save_manifest(manifest)
            log.info("Ingested: %s", key)
            break  # Only latest cycle per model per run

    manifest = purge_old_runs(manifest)
    save_manifest(manifest)
    log.info("=== MonsoonDelta ingest complete ===")


if __name__ == "__main__":
    ingest_latest()
