"""
MonsoonDelta compute library.

Pure maths — no network, no file I/O, no FastAPI imports.
All functions operate on plain Python lists / numpy arrays and return
plain Python dicts or lists so they are trivially testable offline.

Hand-checked examples (from PRD Section 2) are reproduced in comments
and enforced by unit tests in tests/test_compute.py.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from monsoon.constants import (
    KNOWN_UNITS,
    NEGATIVE_CLAMP_TOLERANCE_MM,
    PRECIP_BANDS,
    REVISION_TOLERANCE_MM,
    DISAGREE_MIN_MM,
    DISAGREE_CLOSE_MM,
)

log = logging.getLogger(__name__)


# ── Unit conversion ───────────────────────────────────────────────────────────

def to_mm(values: np.ndarray | list[float], units: str) -> np.ndarray:
    """
    Convert tp values to mm.

    Known conversions
    -----------------
    - 'm'        (IFS)  : multiply by 1000
    - 'kg m**-2' (AIFS) : already mm for liquid water; factor = 1
    - 'mm'               : factor = 1

    Raises ValueError for any unknown units string.

    Hand example (PRD §2.2):
        IFS:  0.002 m → 2.0 mm;  0.005 m → 5.0 mm
        AIFS: 2.0 kg m**-2 → 2.0 mm
    """
    units = units.strip()
    if units not in KNOWN_UNITS:
        raise ValueError(
            f"Unknown tp units '{units}'. "
            f"Known: {list(KNOWN_UNITS)}. "
            "Check GRIB 'units' key and update KNOWN_UNITS in constants.py."
        )

    arr = np.asarray(values, dtype=float)

    if units == "m":
        return arr * 1000.0
    # kg m**-2, kg m-2, mm → 1:1
    return arr.copy()


# ── Accumulation → 6-hour window totals ───────────────────────────────────────

def window_totals(
    cumulative: np.ndarray | list[float],
    steps: list[int],
    window: int = 6,
) -> list[dict[str, Any]]:
    """
    Convert accumulated tp at given forecast steps to per-window totals (mm).

    Parameters
    ----------
    cumulative : array-like
        tp values in mm (after to_mm), one per step, in step order.
    steps : list[int]
        Forecast hours corresponding to each cumulative value. Must be sorted.
    window : int
        Window size in hours (default 6).

    Returns
    -------
    list of dicts with keys:
        step_end   : int   – forecast hour at end of window
        step_start : int   – forecast hour at start of window (step_end - window)
        total_mm   : float – precipitation total for this window (mm)

    Rules
    -----
    - Only steps that are multiples of *window* are considered.
    - For step s, total = tp(s) - tp(s - window). If s - window == 0, tp(0) = 0.
    - A tiny negative difference (> NEGATIVE_CLAMP_TOLERANCE_MM) is clamped to 0
      and logged. A larger negative raises ValueError (data error).

    Hand example (PRD §2.2):
        steps=[12, 18], cumulative=[2.0, 5.0] mm → window(18): 5.0 - 2.0 = 3.0 mm
        step=6, cumulative=[2.0] mm → window(6): 2.0 - 0.0 = 2.0 mm
    """
    steps = list(steps)
    arr = np.asarray(cumulative, dtype=float)
    if len(arr) != len(steps):
        raise ValueError("cumulative and steps must have the same length.")

    # Build lookup: step → cumulative mm
    step_to_cum: dict[int, float] = dict(zip(steps, arr.tolist()))

    results: list[dict[str, Any]] = []
    for s in sorted(steps):
        if s % window != 0:
            continue
        s_prev = s - window
        cum_s = step_to_cum[s]
        cum_prev = step_to_cum.get(s_prev, 0.0)  # tp(0) = 0
        diff = cum_s - cum_prev

        if diff < NEGATIVE_CLAMP_TOLERANCE_MM:
            raise ValueError(
                f"Window total at step {s} is {diff:.4f} mm, "
                f"which is below the clamping tolerance {NEGATIVE_CLAMP_TOLERANCE_MM} mm. "
                "Possible data corruption or incorrect step ordering."
            )
        if diff < 0.0:
            log.warning(
                "Tiny negative window total %.4f mm at step %d clamped to 0.0 mm "
                "(likely floating-point packing artefact).",
                diff, s,
            )
            diff = 0.0

        results.append(
            {"step_end": s, "step_start": s_prev, "total_mm": round(diff, 4)}
        )
    return results


# ── Revision ───────────────────────────────────────────────────────────────────

def revision(
    values_by_run: list[float | None],
    tolerance: float = REVISION_TOLERANCE_MM,
) -> dict[str, Any]:
    """
    Compute forecast revision statistics across multiple model runs for one
    fixed valid window.

    Parameters
    ----------
    values_by_run : list
        Window totals (mm) ordered oldest → newest. Use None for a run that
        does not cover the target window (it will be skipped, never zero-filled).
    tolerance : float
        |change| below this is "steady".

    Returns
    -------
    dict with keys:
        valid_values : list[float]  – values after dropping None
        n_runs       : int
        latest       : float
        previous     : float | None  – None if only one run
        latest_change: float | None
        direction    : str  – "up" | "down" | "steady" | "insufficient_data"
        range_mm     : float | None
        min_mm       : float | None
        max_mm       : float | None

    Hand example (PRD §2.3):
        values_by_run=[4.0, 10.0, 7.0]
        → latest_change = 7.0 - 10.0 = -3.0 mm  (down)
        → range = 10.0 - 4.0 = 6.0 mm
    """
    # Drop None (runs that do not cover the window)
    valid = [v for v in values_by_run if v is not None]

    if len(valid) == 0:
        return {
            "valid_values": [],
            "n_runs": 0,
            "latest": None,
            "previous": None,
            "latest_change": None,
            "direction": "insufficient_data",
            "range_mm": None,
            "min_mm": None,
            "max_mm": None,
        }

    latest = valid[-1]
    previous = valid[-2] if len(valid) >= 2 else None
    latest_change = round(latest - previous, 4) if previous is not None else None

    if len(valid) < 2:
        direction = "insufficient_data"
    elif abs(latest_change) < tolerance:
        direction = "steady"
    elif latest_change > 0:
        direction = "up"
    else:
        direction = "down"

    range_mm = round(max(valid) - min(valid), 4) if len(valid) >= 2 else None

    return {
        "valid_values": [round(v, 4) for v in valid],
        "n_runs": len(valid),
        "latest": round(latest, 4),
        "previous": round(previous, 4) if previous is not None else None,
        "latest_change": latest_change,
        "direction": direction,
        "range_mm": range_mm,
        "min_mm": round(min(valid), 4) if valid else None,
        "max_mm": round(max(valid), 4) if valid else None,
    }


# ── Disagreement ──────────────────────────────────────────────────────────────

def disagreement(ifs_mm: float, aifs_mm: float) -> dict[str, Any]:
    """
    Compute IFS vs AIFS disagreement for the same window.

    Returns
    -------
    dict with keys:
        ifs_mm        : float
        aifs_mm       : float
        diff_mm       : float   – IFS minus AIFS
        abs_diff_mm   : float
        wetter_model  : str     – "IFS" | "AIFS" | "equal"
        percent       : float | None  – relative diff; None if both < DISAGREE_MIN_MM
        close         : bool    – |diff| < DISAGREE_CLOSE_MM

    Hand example (PRD §2.4):
        ifs=7.0, aifs=3.0 → diff=+4.0, IFS wetter
        ifs=0.3, aifs=0.5 → diff=-0.2, percent=None (both < 1 mm)
    """
    diff = round(ifs_mm - aifs_mm, 4)
    abs_diff = round(abs(diff), 4)

    if diff > 1e-6:
        wetter = "IFS"
    elif diff < -1e-6:
        wetter = "AIFS"
    else:
        wetter = "equal"

    # Avoid misleading percentages when both values are tiny
    if ifs_mm < DISAGREE_MIN_MM and aifs_mm < DISAGREE_MIN_MM:
        percent = None
    else:
        denom = max(ifs_mm, aifs_mm)
        percent = round(100.0 * abs_diff / denom, 1) if denom > 0 else None

    return {
        "ifs_mm": round(ifs_mm, 4),
        "aifs_mm": round(aifs_mm, 4),
        "diff_mm": diff,
        "abs_diff_mm": abs_diff,
        "wetter_model": wetter,
        "percent": percent,
        "close": abs_diff < DISAGREE_CLOSE_MM,
    }


# ── Descriptive band lookup ───────────────────────────────────────────────────

def precip_band(mm: float) -> str:
    """Return the neutral descriptive band label for a 6-hour total."""
    for lo, hi, label in PRECIP_BANDS:
        if lo <= mm < hi:
            return label
    return "very heavy"


# ── Bilinear-style 4-cell area mean ──────────────────────────────────────────

def area_mean(
    data: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    target_lat: float,
    target_lon: float,
) -> float:
    """
    Return the area-weighted mean of the 4 surrounding grid cells for a point.

    Parameters
    ----------
    data : 2-D array (lat × lon), already in mm for one time step.
    lats, lons : 1-D coordinate arrays.

    Returns the bilinear-interpolated value at (target_lat, target_lon).
    Uses np.interp which clamps to boundary — appropriate for a point
    near the centre of the region box.
    """
    lat_idx = np.searchsorted(np.sort(lats), target_lat)
    lon_idx = np.searchsorted(np.sort(lons), target_lon)

    # Clamp to valid indices
    i0 = max(0, lat_idx - 1)
    i1 = min(len(lats) - 1, lat_idx)
    j0 = max(0, lon_idx - 1)
    j1 = min(len(lons) - 1, lon_idx)

    cell_values = data[
        np.ix_(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
    ].flatten()
    return float(np.mean(cell_values))
