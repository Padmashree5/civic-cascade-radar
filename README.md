# Civic Cascade Radar — Bengaluru

A full-stack smart-city analytics dashboard for exploring urban datasets on an interactive map. The project includes citizen reporting, infrastructure layers, risk-analysis endpoints, and Civic Cascade Radar, a transparent heuristic that ranks potential waterlogging hotspots for demonstration and exploration.

## Civic Cascade Radar

Civic Cascade Radar integrates a ranked hotspot panel, rainfall what-if scenarios, score breakdowns and source notes, backend radar API handling, and map navigation to selected hotspots. It is a demonstration heuristic, not a validated flood forecast or emergency-warning system. Check the source and verification status before describing any feature as production-ready.

Before publishing or redistributing this repository, verify the licenses and attribution requirements for any third-party code and datasets included in the project.


---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript |
| Map | Leaflet.js, leaflet-heat, leaflet.markercluster |
| Styling | Tailwind CSS v4, shadcn/ui |
| Backend | FastAPI (Python 3.11+), Uvicorn |
| Database | SQLite (via `database.py` + SQLAlchemy models) |
| Auth | JWT (HS256, 8h tokens, `python-jose`) |
| Cache | In-process TTL cache (2–15 min per source type) |
| AI / LLM | Groq API — `llama-3.3-70b-versatile` |
| Weather | Open-Meteo (free, no key required) |
| Routing | OSRM (public API) + Dijkstra fallback |
| Air Quality | AQICN API (live AQI stations) |
| Geo | GeoPandas, Shapely |

---

## Project Structure

```
civic_cascade_radar/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, router mounts (52 routes)
│   │   ├── database.py                # SQLite engine, session factory
│   │   ├── models/
│   │   │   ├── report.py              # Pydantic request/response models
│   │   │   ├── grid.py                # GridPoint (lat, lng, intensity, label, color…)
│   │   │   └── db_models.py           # SQLAlchemy ORM — CitizenReport table
│   │   ├── routes/
│   │   │   ├── heatmap.py             # GET /heatmap/{layer_id}
│   │   │   ├── aqi.py                 # GET /aqi/stations (live AQICN)
│   │   │   ├── reports.py             # CRUD + upvote + photo upload + WebSocket
│   │   │   ├── traffic.py             # OSRM routing + Dijkstra fallback
│   │   │   ├── analytics.py           # Pothole/crime/flood risk, anomalies, ward summary
│   │   │   ├── auth.py                # POST /auth/login, GET /auth/verify (JWT)
│   │   │   ├── layers.py              # BMTC, noise, metro, schools, streetlights,
│   │   │   │                          #   trees, water-quality, construction, rainfall
│   │   │   ├── weather.py             # Open-Meteo live weather stations + rainfall
│   │   │   ├── emergency.py           # Simulation + OSM facilities
│   │   │   ├── insights.py            # Groq LLM insights + chat
│   │   │   ├── datasets.py            # Dataset browser
│   │   │   └── kml.py                 # KML export
│   │   └── services/
│   │       ├── heatmap_engine.py      # All CSV loaders + layer dispatcher
│   │       ├── analytics_service.py   # Risk scoring models
│   │       ├── cache_service.py       # TTL in-memory cache
│   │       ├── weather_service.py     # Open-Meteo wrapper
│   │       ├── groq_service.py        # Groq LLM integration
│   │       ├── coverage_engine.py     # Emergency facility proximity
│   │       ├── routing_service.py     # Dijkstra pathfinding
│   │       └── osm_service.py         # Live OSM facilities
│
├── datasets/                          # Real + synthetic Bengaluru datasets
│   ├── bengaluru_crime_data.csv
│   ├── bengaluru_potholes.csv         # ~789 real records
│   ├── garbage_dump_banglore.csv
│   ├── btp_2025_station_wise.csv      # BTP road crash stations
│   ├── stp.csv.csv
│   ├── street_dogs_banglore.csv
│   ├── tax_collection_with_coords.csv
│   ├── population_with_latlon.csv
│   ├── bescom_with_latlon.csv
│   ├── weather_stations_with_coords.csv
│   ├── bmtc_bus_stops.csv             # 205 stops (seed=2025)
│   ├── metro_stations.csv             # 20 stations across 3 lines
│   ├── noise_stations.csv             # 67 noise monitors
│   ├── school_locations.csv           # 110 schools/colleges
│   ├── street_lights.csv              # 483 lights (working/dim/faulty)
│   ├── tree_canopy.csv                # 246 canopy zones
│   ├── bwssb_water_zones.csv          # 16 water quality zones
│   ├── construction_permits.csv       # 151 active permits
│   └── generate_new_datasets.py       # Reproducible seed=2025 generator
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Main dashboard — sidebar, layers, AI chat, export
│   │   │   ├── layout.tsx             # HTML shell, ThemeProvider, global fonts
│   │   │   └── globals.css            # Tailwind v4 + dark/light CSS variables
│   │   └── components/
│   │       ├── MapView.tsx            # All map rendering (heatmaps, dots, circles,
│   │       │                          #   metro lines, simulation overlay)
│   │       ├── AlertPanel.tsx         # WebSocket live feed with anomaly severity
│   │       ├── LegendPanel.tsx        # Color scales for all active layers
│   │       ├── ThemeProvider.tsx      # Dark/light theme persistence (localStorage)
│   │       ├── InsightCard.tsx        # Weakness card (severity + recommendation)
│   │       ├── GroqInsightButton.tsx  # Trigger Groq LLM analysis
│   │       ├── ReportModal.tsx        # Click-to-report modal
│   │       └── DatasetSelector.tsx    # Raw dataset browser
│   └── package.json
│
├── smartcity.db                       # SQLite — citizen reports (gitignored)
└── README.md
```

---

## Map Layers (21 total)

### Infrastructure
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| Traffic | Heatmap (amber) | `bengaluru_traffic_data.csv` | `/heatmap/traffic` |
| Potholes | Orange dots | `bengaluru_potholes.csv` | `/heatmap/pothole` |
| Road Crashes | Red dots | `btp_2025_station_wise.csv` | `/heatmap/crashes` |
| Street Lights | Dots (green/amber/red by status) | `street_lights.csv` | `/layers/streetlights` |
| Construction | Orange dots | `construction_permits.csv` | `/layers/construction` |

### Environment
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| Air Quality (AQI) | Color-coded circles | Live — AQICN API | `/aqi/stations` |
| Noise Pollution | Heatmap (red) | `noise_stations.csv` | `/layers/noise` |
| Rainfall (Live) | Heatmap (blue) | Open-Meteo / `bwssb_water_zones.csv` | `/layers/rainfall` |
| Tree Canopy | Heatmap (green) | `tree_canopy.csv` | `/layers/trees` |
| Drainage Issues | Blue dots | Synthetic (zone-based) | `/heatmap/drainage` |

### Safety
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| Crime | Red dots | `bengaluru_crime_data.csv` | `/heatmap/crime` |
| Crime (NCRB 2023) | Heatmap (red) | `ncrb_crime_2023.py` | `/heatmap/crime_ncrb` |
| Garbage Dumps | Green dots | `garbage_dump_banglore.csv` | `/heatmap/garbage_dump` |
| Street Dogs | Heatmap (orange) | `street_dogs_banglore.csv` | `/heatmap/street_dogs` |

### Utilities
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| BESCOM Substations | Orange dots | `bescom_with_latlon.csv` | `/heatmap/bescom` |
| STP Plants | Teal factory icons | `stp.csv.csv` | `/heatmap/stp` |
| Water Quality | Color-coded dots | `bwssb_water_zones.csv` | `/layers/water-quality` |

### Transport
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| BMTC Bus Stops | Bus icons | `bmtc_bus_stops.csv` | `/layers/bmtc` |
| Metro Stations | Line-colored markers | `metro_stations.csv` | `/layers/metro` |

### Demographics
| Layer | Visual | Data Source | Endpoint |
|---|---|---|---|
| Population Density | Blue-indigo circles | `population_with_latlon.csv` | `/heatmap/population` |
| Schools & Colleges | Purple dots | `school_locations.csv` | `/layers/schools` |
| Tax Collection | Amber ward circles | `tax_collection_with_coords.csv` | `/heatmap/tax_collection` |
| Weather Stations | Cyan dots | `weather_stations_with_coords.csv` | `/heatmap/weather_station` |

---

## Features

### Real-time & Live Data
- **WebSocket live feed** (`/ws/reports`) — pushes new citizen reports and periodic anomaly alerts to `AlertPanel`
- **Open-Meteo weather** — live rainfall and station data, no API key required
- **AQICN AQI** — live air quality circles for Bengaluru bounding box

### AI & Analytics
- **Groq LLM chat** — context-aware (sends active layer IDs + point counts with each message)
- **Predictive analytics** — pothole-risk, crime-hotspot, and flood-risk ward scoring (`/analytics/*`)
- **Anomaly detection** — automatic alert generation from report patterns

### Emergency Simulation
Click **Crime** or **Rain** in the sidebar, then click the map to simulate an incident:
- Nearest police / fire / hospital with ETA
- Response lines color-coded by responder type
- Under-served zones flagged in red

### Other
- **JWT auth** — admin login at `/auth/login`, 8h tokens
- **Citizen reports** — click map to file a report; supports photo upload (5 MB limit) and upvoting
- **Nominatim geocoder** — search any Bengaluru location and jump to it
- **PNG / PDF export** — captures the current map viewport
- **KML/KMZ upload** — drag-and-drop any GeoJSON/KML layer onto the map
- **Per-layer intensity sliders** — fine-tune heatmap opacity/dot size
- **Dark / light theme** — persisted in `localStorage`

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:3000`

---

## Environment Variables

Create `backend/.env`:

```env
GROQ_API_KEY=...        # groq.com — free tier, llama-3.3-70b-versatile
AQICN_TOKEN=...         # aqicn.org/api — free token for live AQI
ADMIN_SECRET=...        # any string — used to sign JWT tokens
```

Open-Meteo needs no key.

---

## Full API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/heatmap/{layer_id}` | Intensity points for any layer |
| GET | `/aqi/stations` | Live AQI stations (AQICN) |
| GET | `/layers/bmtc` | BMTC bus stop points |
| GET | `/layers/metro` | Metro station points with line colors |
| GET | `/layers/noise` | Noise monitor heatmap points |
| GET | `/layers/schools` | School/college locations |
| GET | `/layers/streetlights` | Street light status points |
| GET | `/layers/trees` | Tree canopy heatmap points |
| GET | `/layers/water-quality` | BWSSB water quality points |
| GET | `/layers/construction` | Active construction permit points |
| GET | `/layers/rainfall` | Live/synthetic rainfall heatmap |
| GET | `/weather/stations` | Open-Meteo weather station data |
| GET | `/weather/rainfall` | Live rainfall readings |
| GET | `/analytics/pothole-risk` | Ward-level pothole risk scores |
| GET | `/analytics/crime-hotspot` | Ward-level crime hotspot scores |
| GET | `/analytics/flood-risk` | Ward-level flood risk scores |
| GET | `/analytics/anomalies` | Auto-detected anomalies from reports |
| GET | `/analytics/ward-summary` | Full ward summary table |
| POST | `/auth/login` | Get JWT token (`{ secret: "..." }`) |
| GET | `/auth/verify` | Verify JWT token |
| GET | `/insights/` | Ranked infrastructure weakness report |
| GET | `/insights/ai` | Groq LLM city analysis |
| POST | `/insights/chat` | Conversational city assistant |
| GET | `/reports/` | List citizen reports (from SQLite) |
| POST | `/reports/` | Submit citizen report |
| POST | `/reports/with-photo` | Submit report with photo (multipart, 5 MB) |
| POST | `/reports/{id}/upvote` | Upvote a report (IP-hash dedup) |
| WS | `/ws/reports` | WebSocket — live report + anomaly feed |
| GET | `/emergency/simulate` | Emergency response simulation |
| GET | `/emergency/facilities-osm` | Live OSM emergency facilities |
| GET | `/traffic/route` | OSRM route + ETA (Dijkstra fallback) |
| GET | `/datasets/` | List available raw datasets |
| GET | `/datasets/{id}` | Raw dataset points |
| GET | `/kml/{layer_id}` | Export layer as GeoJSON/KML |


## Civic Cascade Radar (added)

The right-hand panel now includes a **Cascade** tab. It ranks potential waterlogging hotspots from the bundled flood-prone-location KML and combines a rainfall signal, nearby garbage-dump density, existing hand-coded zone priors, and recent citizen reports. Each result includes its score breakdown and source notes.

- `GET /cascade/radar?top_n=10` — use the nearest weather station's precipitation.
- `GET /cascade/radar?rainfall=80&top_n=10` — run an explicit 80 mm what-if scenario.

**Important:** this is a transparent demo heuristic, not a validated flood prediction. Some weather values may be synthetic fallback data, and the dataset provenance has not been independently verified. Groundwater potential is context only, not a measured drainage or infiltration value.

For one-click setup on Windows, see [`README-WINDOWS.md`](README-WINDOWS.md) and run `run_windows.bat`.
