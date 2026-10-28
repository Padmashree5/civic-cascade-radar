# Bengaluru Smart City Dashboard — Data Sources

## Overview

The dashboard overlays multiple urban data layers on an interactive OpenStreetMap base.
Each layer draws from a distinct source, ranging from real government datasets to
curated CSV data and synthetic generation.

---

## Layer-by-Layer Data Sources

### Traffic
**File:** `bengaluru_traffic_data.csv` (project root)
**Type:** Curated real-world measurements

46 records covering 23 key areas of Bengaluru (morning/evening readings per area).

| Field | Description |
|---|---|
| `area_name` | Neighbourhood name (e.g. Silk Board, Whitefield) |
| `latitude / longitude` | GPS coordinates of the area centre |
| `traffic_volume` | Vehicle count observed in the measurement window |
| `avg_speed_kmph` | Average vehicle speed (km/h) |
| `congestion_level` | Low / Medium / High classification |
| `time_of_day` | Morning / Afternoon / Evening |

**Intensity mapping:** `traffic_volume / 1000` (Silk Board evening peaks at 1.0)

**Hotspots:** Silk Board, Bellandur, Whitefield, KR Puram, Marathahalli — all consistently High congestion.

---

### Potholes
**File:** `backend/app/data/bengaluru_potholes.csv`
**Type:** Real dataset — 788 records

Sourced from BBMP (Bruhat Bengaluru Mahanagara Palike) open data.
Fields: `lat`, `long`, `category` (0–3 → Low / Medium / High / Critical), `created_at`.

---

### Crime — Synthetic
**Generated in:** `backend/app/services/data_service.py → generate_crime_data()`
**Type:** Synthetic (zone-based random scatter, seed=42)

Points are scattered around 10 known high-density zones (Majestic, Whitefield, Marathahalli, etc.)
using a fixed random seed so the pattern is reproducible across restarts.

---

### Crime — NCRB 2023
**File:** `backend/app/data/ncrb_crime_2023.py`
**Type:** Real — National Crime Records Bureau official data

Contains Karnataka district-level IPC totals and Bangalore zone-level crime indices.
Intensity is normalised against Bangalore Urban's maximum IPC total.

---

### Drainage Issues
**Generated in:** `backend/app/services/data_service.py → generate_drainage_data()`
**Type:** Synthetic (zone-based random scatter, seed=99)

Covers 8 known flood-prone / low-drainage zones (Majestic, Indiranagar, Electronic City, etc.).
States: Blocked, Overflowing, Broken Cover, Partial Block.

---

### Flood Risk
**Endpoint:** `GET /flood/risk?rainfall=<mm>`
**Type:** Model-derived (elevation + drainage scoring)

Risk zones (HIGH / MEDIUM / LOW) are computed dynamically by the backend flood-risk engine
using elevation data and drainage scores. Rainfall input (mm) shifts zone thresholds.

---

### Emergency Facilities
**Endpoint:** `GET /emergency/facilities-osm`
**Type:** Real — OpenStreetMap (OSM) live query

Police stations, hospitals, fire stations, clinics, and ambulance stations pulled directly
from the OSM Overpass API for Bangalore. Data is live and reflects current OSM edits.

**Also:** `bengaluru_emergency_services.csv` in project root provides a static fallback
with pre-verified facility locations.

---

### Litter / Sanitation
**Generated in:** `backend/app/services/heatmap_engine.py → _BASE_LITTER`
**Type:** Synthetic (jittered from 10 known sanitation-problem zones, seed=202)

---

## Summary Table

| Layer | Source Type | Record Count | File / Origin |
|---|---|---|---|
| Traffic | Curated CSV | 46 | `bengaluru_traffic_data.csv` |
| Potholes | Real (BBMP) | 788 | `bengaluru_potholes.csv` |
| Crime (Synthetic) | Synthetic | ~239 | `data_service.py` |
| Crime (NCRB 2023) | Real (Govt) | 30+ zones | `ncrb_crime_2023.py` |
| Drainage | Synthetic | ~159 | `data_service.py` |
| Flood Risk | Model-derived | Dynamic | `/flood/risk` endpoint |
| Litter | Synthetic | ~70 | `heatmap_engine.py` |
| Emergency Facilities | Real (OSM) | Live | OSM Overpass API |
