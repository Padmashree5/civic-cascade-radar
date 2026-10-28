# Architecture & Data Pipeline

How the Smart City Intelligence Dashboard is built and how data flows through it.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Browser (Next.js)                           │
│                                                                     │
│  ┌──────────────┐   ┌─────────────────────────────────────────┐   │
│  │  Left Sidebar │   │            Map Viewport (Leaflet)        │   │
│  │              │   │                                           │   │
│  │  21 layer    │   │  Heatmaps  Dots  Circles  Metro lines    │   │
│  │  toggles     │   │  Simulation overlay   GeoJSON/KML        │   │
│  │  Intensity   │   │                                           │   │
│  │  sliders     │   └─────────────────────────────────────────┘   │
│  │  Simulation  │                                                   │
│  │  controls    │   ┌─────────────────────────────────────────┐   │
│  └──────────────┘   │           Right Panel                    │   │
│                      │  Insights │ AI Chat │ Analytics         │   │
│  ┌──────────────┐   │                                           │   │
│  │ AlertPanel   │   │  LegendPanel   Export (PNG/PDF)          │   │
│  │ (WebSocket)  │   └─────────────────────────────────────────┘   │
│  └──────────────┘                                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                       │
│                                                                     │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ heatmap.py │  │layers.py │  │analytics │  │  reports.py    │  │
│  │            │  │          │  │  .py     │  │  (WebSocket)   │  │
│  │ CSV → pts  │  │ CSV → pts│  │ scoring  │  │  SQLite CRUD   │  │
│  └─────┬──────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│        │              │             │                  │           │
│        └──────────────┴─────────────┴──────────────────┘          │
│                              │                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Services Layer                           │   │
│  │  heatmap_engine  analytics_service  cache_service          │   │
│  │  weather_service  groq_service  routing_service            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ SQLite   │  │  /datasets│  │  Groq    │  │  External APIs   │  │
│  │smartcity │  │  CSVs     │  │  LLM     │  │  AQICN / OSRM   │  │
│  │  .db     │  │           │  │          │  │  Open-Meteo      │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline

### Layer data flow (heatmap / dot layers)

```
CSV file on disk
      │
      ▼
heatmap_engine.py  ──────────────────────────────────────────────────┐
  load_csv_layer()                                                     │
  • pandas read_csv                                                    │
  • map columns → lat / lng / intensity / label                       │
  • return List[GridPoint]                                             │
      │                                                                │
      ▼                                                                │
cache_service.py                                                       │
  TTLCache.get(layer_id)                                               │
  • HIT  → return cached points (TTL: 5–15 min)                       │
  • MISS → call heatmap_engine, store result                           │
      │                                                                │
      ▼                                                                │
GET /heatmap/{layer_id}                                                │
    or                                                                 │
GET /layers/{layer_id}                                                 │
      │                                                                │
      ▼                                                                │
JSON response  [ { lat, lng, intensity, label?, color? }, … ]         │
      │                                                                │
      ▼                                                                │
page.tsx — fetchHeatLayer()                                            │
  setLayerData(prev => ({ ...prev, [layerId]: points }))              │
      │                                                                │
      ▼                                                                │
MapView.tsx — useEffect([activeLayers, layerData])                    │
  • heatmap layers  → L.heatLayer(points, gradient)                   │
  • dot layers      → L.markerClusterGroup + L.divIcon per point      │
  • metro           → line-colored L.marker                           │
  • tax/AQI/pop     → L.circle with scaled radius + color             │
      │                                                                │
      ▼                                                                │
Leaflet renders tiles + overlays in the browser                       │
```

### Live AQI flow

```
AQICN API  (external)
      │  GET https://api.waqi.info/map/bounds/…
      ▼
aqi.py — /aqi/stations
  • fetch bounding box for Bengaluru
  • map AQI value → color category (Good/Moderate/…/Hazardous)
  • return GridPoint list with color + label
      │
      ▼
MapView — AQI useEffect
  → L.circle per station, radius=1200m, color from AQI category
```

### Citizen report flow

```
User clicks map
      │
      ▼
ReportModal (page.tsx)
  POST /reports/  or  POST /reports/with-photo
      │
      ▼
reports.py
  • validate Pydantic model
  • INSERT into CitizenReport (SQLite)
  • broadcast {type: "new_report"} to all WebSocket clients
      │
      ├──▶ WebSocket /ws/reports ──▶ AlertPanel.tsx
      │         (live feed)
      │
      └──▶ heatmap route now reads from SQLite
           (citizen reports feed the heatmap layer)
```

### Analytics / risk scoring flow

```
GET /analytics/pothole-risk
          │
          ▼
analytics_service.py
  • load pothole CSV + citizen reports from SQLite
  • group by ward
  • score = (report_count × 0.4) + (severity_avg × 0.4) + (road_age × 0.2)
  • rank wards, return top-N with score + risk_label
          │
          ▼
page.tsx — Analytics tab
  • bar chart per ward with score fill
  • color: red (CRITICAL) → orange (HIGH) → yellow (MEDIUM) → green (LOW)
```

### AI chat flow

```
User types message in Ask tab
          │
          ▼
page.tsx — buildContext()
  • collect activeLayers[]
  • count points per layer from layerData
  • serialize as: "Active layers: traffic (120 pts), crime (89 pts)…"
          │
          ▼
POST /insights/chat
  { message, context }
          │
          ▼
groq_service.py
  • prepend system prompt (city analyst persona)
  • inject layer context into user message
  • call Groq API — llama-3.3-70b-versatile
  • stream response
          │
          ▼
page.tsx — append assistant message to history[]
```

### Routing flow

```
User selects two points
          │
          ▼
GET /traffic/route?from_lat=…&to_lat=…
          │
          ▼
routing_service.py
  ┌─── try OSRM public API
  │      GET http://router.project-osrm.org/route/v1/driving/…
  │      parse steps, distance, duration
  │
  └─── fallback: Dijkstra on road graph
         build graph from bengaluru_traffic_data.csv
         find shortest path by weight
          │
          ▼
return { route: [[lat,lng],…], distance_km, eta_minutes }
          │
          ▼
MapView — draw L.polyline on map
```

### WebSocket anomaly feed

```
Background task in reports.py (runs every 60 s)
          │
          ▼
  • query SQLite for reports in last 24h
  • cluster by lat/lng grid cell
  • if cluster_count > threshold → generate anomaly alert
  • broadcast {type: "anomaly", severity, zone, message}
          │
          ▼
AlertPanel.tsx
  • useEffect → new WebSocket("ws://localhost:8000/ws/reports")
  • onmessage → append to alerts[]
  • severity color: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green
```

---

## Authentication Flow

```
POST /auth/login  { secret: "ADMIN_SECRET" }
          │
          ▼
auth.py — compare against ADMIN_SECRET env var
  • match → create JWT (HS256, exp=8h, sub="admin")
  • return { token }
          │
          ▼
Client stores token in localStorage
  • sends as Authorization: Bearer <token> on protected routes
          │
          ▼
GET /auth/verify  → 200 OK or 401
```

---

## Frontend State Architecture

```
page.tsx (root state)
  │
  ├── activeLayers: string[]          which layers are toggled on
  ├── layerData: Record<id, pts[]>    fetched points per layer
  ├── layerIntensity: Record<id, n>   0.0–1.0 per layer
  ├── simulationMode / Result         emergency sim state
  ├── geoJsonLayer                    uploaded KML/GeoJSON
  ├── mapCenter: [lat, lng]           Nominatim jump-to result
  │
  └── MapView (props-only, no internal state for layers)
        │
        ├── useEffect[activeLayers, layerData, layerIntensity]
        │     add / remove heatmap layers
        ├── useEffect[activeLayers, layerData, layerIntensity]
        │     add / remove dot/cluster layers
        ├── useEffect[activeLayers, layerData, layerIntensity]
        │     metro / tax / AQI / population circles
        ├── useEffect[simulationResult]
        │     draw incident marker + responder polylines
        └── useEffect[geoJsonLayer]
              draw uploaded GeoJSON
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| `leaflet-heat` loaded via `<script>` tag (not npm) | Turbopack/ESM can't import UMD bundles; browser script tag puts it on `window.L` |
| `leaflet/dist/leaflet.css` imported in `MapView.tsx` | Without it, Leaflet tiles have no positioning context and render in random chunks |
| `absolute inset-0` on Leaflet container div | `h-full` fails when parent height is flexbox-computed; absolute fill is reliable |
| `ResizeObserver` + `invalidateSize()` on map init | Ensures tiles re-render when sidebar opens/closes |
| `random.Random(seed)` per call in synthetic generators | Module-level `random.seed()` breaks between requests; per-call seeded RNG keeps data deterministic |
| SQLite instead of PostgreSQL | Zero-config, file-based, sufficient for ~10k reports; easy to swap later |
| TTL cache per layer type | CSV files don't change at runtime; caching avoids re-reading disk on every API call |
| OSRM public API with Dijkstra fallback | OSRM gives real road routing; fallback prevents hard failure if OSRM is unreachable |
