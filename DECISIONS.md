# DECISIONS.md — MonsoonDelta

> Record every significant design decision here with date and rationale.

| Date | Decision | Why | Alternatives rejected | Status |
|---|---|---|---|---|
| 2026-11-15 | Use tp, 6-hour windows | Common step grid for IFS (3h) and AIFS (6h) | 3-hourly (AIFS lacks it) | accepted |
| 2026-11-15 | Region box 5–23°N, 78–100°E | Covers Bay of Bengal + coastal Andhra Pradesh | Smaller box (misses offshore systems) | accepted |
| 2026-11-15 | Default point: 4-cell bilinear mean around 17.7°N 83.2°E | More robust than nearest-cell; avoids single-cell noise | Radius average (more complex) | accepted |
| 2026-11-15 | Revision tolerance 0.5 mm | Below typical model uncertainty at 0.25° | 0.1 mm (too tight), 1.0 mm (too loose) | proposed |
| 2026-11-15 | Descriptive bands: <1, 1–5, 5–15, 15–30, ≥30 mm per 6 h | Own neutral scale; not IMD official | IMD categories (not independently verified here) | accepted |
| 2026-11-15 | Store own 14-day history | ECMWF retention ~2–4 days is too short for 6-run revision | Cloud mirror (unknown retention) | accepted |
| 2026-11-15 | Frontend: static HTML/JS + Three.js + Leaflet | No build step; fast initial load; meets 3 s mobile target | React (adds bundle complexity for MVP) | accepted |
| 2026-11-15 | Hosting: Railway.app free tier (Docker) | Free, persistent disk, supports cron, easy deploy | Render, Fly.io, Heroku | proposed |
| 2026-11-15 | No ECMWF API key needed | Data is CC BY 4.0 open; ecmwf-opendata uses public URLs | Paid ECMWF MARS (not needed for open data) | accepted |

## Open questions (from Section 0 of PRD)

- [ ] Real IFS tp units from a downloaded file (documented as metres; unconfirmed)
- [ ] Real AIFS tp units (documented as kg m⁻²; unconfirmed)
- [ ] IFS 06/18 UTC step range (0–144 h or 0–90 h?)
- [ ] Exact AIFS file path pattern on data.ecmwf.int
- [ ] Whether a service agreement is needed for public deployment
- [ ] ECMWF retention window (12 runs vs 2–4 days vs 4 days)
