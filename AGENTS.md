# AGENTS.md — MonsoonDelta Project Rules

Project: **MonsoonDelta** — ECMWF IFS/AIFS precipitation revision app  
Region: Bay of Bengal, default location Visakhapatnam (~17.7°N, 83.2°E)

---

## Rules (every agent must follow)

1. **Never invent** numbers, sources, file paths or API fields. If unverified, write `UNVERIFIED` and ask.
2. **Never read, print or write secrets.** No API keys are needed. Do not add any.
3. **Small steps.** State plan and assumptions first. Wait for decision on any real choice.
4. **Commit often** with clear messages (imperative, one change each). Tests before code.
5. **Tests run offline** on `tests/data` fixtures. Never download in tests.
6. **Units:** always read the GRIB `units` key; convert to mm; unknown units raise an error.
7. **tp is accumulated** from forecast start; window total = `tp(s) - tp(s-6)`.
8. **UI and copy never say** warning/alert/danger; every page shows the disclaimer and ECMWF attribution.
9. **Keep dependencies minimal.** Python 3.12+, pytest, FastAPI, xarray, cfgrib/eccodes.
10. **Update DECISIONS.md** after every decision (what, why, date).

## Stack
- Python 3.12+
- ecmwf-opendata (download client)
- cfgrib / eccodes (GRIB reading)
- xarray + numpy (compute)
- FastAPI + uvicorn (API)
- pytest (tests)
- Static HTML/JS + Three.js + Leaflet (frontend)

## Directory layout
```
Rain-Delta/
├── AGENTS.md
├── DECISIONS.md
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── src/monsoon/
│   ├── __init__.py
│   ├── compute.py        # pure maths, no I/O
│   ├── explain.py        # template engine
│   └── constants.py      # region box, bands, tolerances
├── ingest/
│   ├── __init__.py
│   └── run.py            # scheduled ingest job
├── api/
│   ├── __init__.py
│   └── main.py           # FastAPI app
├── frontend/
│   ├── index.html
│   ├── methods.html
│   ├── css/style.css
│   └── js/app.js
├── scripts/
│   └── inspect_tp.py     # Phase 1 data inspection
├── store/                # runtime data (gitignored)
└── tests/
    ├── data/             # offline fixtures (small NetCDF/numpy)
    ├── test_compute.py
    ├── test_explain.py
    └── test_api.py
```
