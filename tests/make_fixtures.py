"""
Create offline test fixtures for MonsoonDelta.

Run once: python tests/make_fixtures.py
Writes small numpy files to tests/data/ so tests never download anything.
"""

import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT, exist_ok=True)

# ── IFS fixture ───────────────────────────────────────────────────────────────
# 3 steps: 6, 12, 18 h; 4 lat points (5–6.25°N), 4 lon points (78–79.25°E)
# Accumulated tp in METRES (IFS units)
ifs_steps = np.array([6, 12, 18], dtype=int)
# shape (3, 4, 4)
ifs_tp_m = np.array([
    [[0.001, 0.001, 0.0012, 0.0010],
     [0.0011, 0.0010, 0.0013, 0.0011],
     [0.0010, 0.0010, 0.0010, 0.0010],
     [0.0010, 0.0010, 0.0010, 0.0010]],
    # step 12 → includes PRD hand example: some cells at 0.002 m
    [[0.002, 0.002, 0.0022, 0.0020],
     [0.0021, 0.0020, 0.0023, 0.0021],
     [0.0020, 0.0020, 0.0020, 0.0020],
     [0.0020, 0.0020, 0.0020, 0.0020]],
    # step 18 → PRD hand example: 0.005 m
    [[0.005, 0.005, 0.0052, 0.0050],
     [0.0051, 0.0050, 0.0053, 0.0051],
     [0.0050, 0.0050, 0.0050, 0.0050],
     [0.0050, 0.0050, 0.0050, 0.0050]],
], dtype=float)
ifs_lats = np.array([5.0, 5.25, 5.5, 5.75])
ifs_lons = np.array([78.0, 78.25, 78.5, 78.75])

np.save(os.path.join(OUT, "ifs_tp_steps.npy"), ifs_steps)
np.save(os.path.join(OUT, "ifs_tp_m.npy"), ifs_tp_m)
np.save(os.path.join(OUT, "ifs_lats.npy"), ifs_lats)
np.save(os.path.join(OUT, "ifs_lons.npy"), ifs_lons)

# ── AIFS fixture ──────────────────────────────────────────────────────────────
# 3 steps: 6, 12, 18 h; same 4×4 grid
# Accumulated tp in kg m**-2 (== mm for liquid water)
aifs_steps = np.array([6, 12, 18], dtype=int)
aifs_tp_kgm2 = np.array([
    [[1.0, 1.0, 1.1, 1.0],
     [1.1, 1.0, 1.2, 1.1],
     [1.0, 1.0, 1.0, 1.0],
     [1.0, 1.0, 1.0, 1.0]],
    # step 12: PRD hand example point-value 2.0 kg m**-2
    [[2.0, 2.0, 2.1, 2.0],
     [2.1, 2.0, 2.2, 2.1],
     [2.0, 2.0, 2.0, 2.0],
     [2.0, 2.0, 2.0, 2.0]],
    # step 18: PRD hand example 5.0 kg m**-2
    [[5.0, 5.0, 5.1, 5.0],
     [5.1, 5.0, 5.2, 5.1],
     [5.0, 5.0, 5.0, 5.0],
     [5.0, 5.0, 5.0, 5.0]],
], dtype=float)

np.save(os.path.join(OUT, "aifs_tp_steps.npy"), aifs_steps)
np.save(os.path.join(OUT, "aifs_tp_kgm2.npy"), aifs_tp_kgm2)
np.save(os.path.join(OUT, "aifs_lats.npy"), ifs_lats)
np.save(os.path.join(OUT, "aifs_lons.npy"), ifs_lons)

print("Fixtures written to", OUT)
