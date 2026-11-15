"""
MonsoonDelta — constants used across compute, ingest, and API layers.

No I/O here. Imported by compute.py, ingest/run.py, api/main.py.
"""

# ── Region bounding box ──────────────────────────────────────────────────────
# Bay of Bengal region covering coastal Andhra Pradesh and offshore systems.
REGION_BOX = {
    "lat_min": 5.0,
    "lat_max": 23.0,
    "lon_min": 78.0,
    "lon_max": 100.0,
}

# ── Default point: Visakhapatnam ─────────────────────────────────────────────
# Coordinates from public geographic databases; verify before hard-coding in production.
DEFAULT_LAT = 17.7
DEFAULT_LON = 83.2
DEFAULT_NAME = "Visakhapatnam"

# ── Window size ──────────────────────────────────────────────────────────────
WINDOW_HOURS = 6  # common grid for IFS (3 h steps) and AIFS (6 h steps)

# ── Revision ─────────────────────────────────────────────────────────────────
REVISION_TOLERANCE_MM = 0.5   # |change| below this → "steady"
MAX_RUNS_FOR_REVISION = 6     # last N runs shown in revision chart
NEGATIVE_CLAMP_TOLERANCE_MM = -0.05  # tiny negative (packing artefact) is clamped

# ── Descriptive bands (6-hour totals, mm) — neutral, not IMD official ────────
PRECIP_BANDS = [
    (0,   1,   "negligible"),
    (1,   5,   "light"),
    (5,   15,  "moderate"),
    (15,  30,  "heavy"),
    (30,  float("inf"), "very heavy"),
]

# ── Disagreement threshold ────────────────────────────────────────────────────
DISAGREE_MIN_MM = 1.0   # below this for BOTH values, don't report percent
DISAGREE_CLOSE_MM = 2.0 # |D| below this → models "broadly agree"

# ── Stale data threshold (hours) ─────────────────────────────────────────────
STALE_THRESHOLD_HOURS = 9  # if newest run is older than this, raise stale flag

# ── Known tp units from GRIB ─────────────────────────────────────────────────
# IFS: metres; AIFS: kg m-2 (== mm for water). Both end up as mm.
KNOWN_UNITS = {
    "m": "metres",
    "kg m**-2": "kg_per_m2",
    "kg m-2": "kg_per_m2",   # alternate spelling seen in some GRIB files
    "mm": "mm",               # some derived/remapped files
}

# ── Attribution strings (CC BY 4.0, required on every page) ──────────────────
DISCLAIMER = (
    "This is automated model output from ECMWF IFS and AIFS. "
    "It is not an official forecast or warning. "
    "For official warnings, follow your national meteorological service "
    "(IMD in India) and local authorities."
)

ATTRIBUTION = (
    "This service is based on data and products of the European Centre for "
    "Medium-Range Weather Forecasts (ECMWF). \u00a9 2026 ECMWF. "
    "Source: www.ecmwf.int. "
    "Licence: CC BY 4.0 \u2014 https://creativecommons.org/licenses/by/4.0/. "
    "ECMWF does not accept any liability for any error or omission in the data, "
    "their availability, or for any loss or damage arising from their use. "
    "Values shown are derived (6-hour totals, differences between runs), "
    "so the material has been modified."
)

# ── Banned words (tested in CI) ───────────────────────────────────────────────
BANNED_WORDS = [
    "warning", "alert", "danger", "evacuate", "will flood",
    "safe", "dangerous", "emergency",
]
