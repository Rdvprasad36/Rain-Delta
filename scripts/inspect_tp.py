"""
Phase 1 — Data inspection script.

Usage:
    pip install ecmwf-opendata cfgrib xarray numpy
    python scripts/inspect_tp.py

Downloads ONE IFS tp file and ONE AIFS tp file from the latest available run.
Prints key metadata for each. Saves files to tests/raw/ (gitignored).
Does NOT parse any secrets or write credentials.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ecmwf.opendata import Client
except ImportError:
    print("ERROR: ecmwf-opendata not installed. Run: pip install ecmwf-opendata")
    sys.exit(1)

try:
    import cfgrib
    import numpy as np
except ImportError:
    print("ERROR: cfgrib/numpy not installed. Run: pip install cfgrib numpy")
    sys.exit(1)


RAW_DIR = Path(__file__).parent.parent / "tests" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
DATE_STR = NOW.strftime("%Y%m%d")

MODELS = [
    {
        "label": "IFS",
        "params": dict(
            model="ifs",
            resol="0p25",
            stream="oper",
            type="fc",
            param="tp",
            step=24,     # one step, multiple of 6
            time=0,      # 00Z run
            date=DATE_STR,
        ),
        "outfile": RAW_DIR / "ifs_tp.grib2",
    },
    {
        "label": "AIFS",
        "params": dict(
            model="aifs-single",
            resol="0p25",
            stream="oper",
            type="fc",
            param="tp",
            step=24,
            time=0,
            date=DATE_STR,
        ),
        "outfile": RAW_DIR / "aifs_tp.grib2",
    },
]


def inspect_file(label: str, path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"Model: {label}  |  File: {path.name}")
    print(f"{'='*60}")

    ds_list = cfgrib.open_datasets(str(path))
    if not ds_list:
        print("  ERROR: No datasets found in GRIB file.")
        return

    for ds in ds_list:
        for var_name in ds:
            var = ds[var_name]
            attrs = var.attrs
            print(f"  Variable      : {var_name}")
            print(f"  shortName     : {attrs.get('GRIB_shortName', 'UNVERIFIED')}")
            print(f"  paramId       : {attrs.get('GRIB_paramId', 'UNVERIFIED')}")
            print(f"  units         : {attrs.get('units', 'UNVERIFIED')}")  # KEY CHECK
            print(f"  stepType      : {attrs.get('GRIB_stepType', 'UNVERIFIED')}")
            print(f"  typeOfStat    : {attrs.get('GRIB_typeOfStatisticalProcessing', 'N/A')}")
            print(f"  dataDate      : {attrs.get('GRIB_dataDate', 'UNVERIFIED')}")
            print(f"  dataTime      : {attrs.get('GRIB_dataTime', 'UNVERIFIED')}")
            print(f"  step          : {attrs.get('GRIB_stepRange', 'UNVERIFIED')}")
            print(f"  Grid shape    : {var.values.shape}")
            print(f"  Grid dtype    : {var.values.dtype}")
            vals = var.values.flatten()
            vals = vals[~np.isnan(vals)]
            if len(vals) > 0:
                print(f"  Min value     : {vals.min():.6g}")
                print(f"  Max value     : {vals.max():.6g}")
            print(f"  Lat range     : {float(ds.latitude.min()):.2f} – {float(ds.latitude.max()):.2f}")
            print(f"  Lon range     : {float(ds.longitude.min()):.2f} – {float(ds.longitude.max()):.2f}")
            print()


def main() -> None:
    client = Client(source="ecmwf")

    for model in MODELS:
        print(f"\nFetching {model['label']} tp (step=24, 00Z, {DATE_STR}) …")
        try:
            client.retrieve(**model["params"], target=str(model["outfile"]))
            print(f"  Saved to: {model['outfile']}")
            inspect_file(model["label"], model["outfile"])
        except Exception as exc:
            print(f"  FAILED: {exc}")
            print("  → Record this failure in DECISIONS.md open questions.")

    print("\nDone. Record answers in DECISIONS.md.")


if __name__ == "__main__":
    main()
