# Smart City Intelligence System Tasks

## 1. Project Setup
- [x] Initialize Next.js frontend (`frontend`) with App Router, TypeScript, TailwindCSS.
- [x] Integrate shadcn/ui components in Next.js.
- [x] Set up Python virtual environment and initialize FastAPI project (`backend`).
- [x] Skip Docker/PostGIS — using in-memory SQLite-compatible approach for MVP.

## 2. Backend Implementation (FastAPI)
- [x] Set up in-memory data models (`report.py`, `grid.py`).
- [x] Build Services:
  - [x] `osm_service.py` (static city infrastructure data, GeoJSON facilities)
  - [x] `routing_service.py` (custom Dijkstra's algorithm for traffic/ETA)
  - [x] `risk_engine.py` (Flood simulation using elevation + drainage data)
  - [x] `coverage_engine.py` (Emergency response distances, UNDER-SERVED detection)
  - [x] `heatmap_engine.py` (Crime/Litter heatmap generation with citizen point merging)
- [x] Build API Routes:
  - [x] `/flood/risk` (flood simulation with rainfall param)
  - [x] `/traffic/route` (Dijkstra ETA + path coordinates)
  - [x] `/emergency/nearest`, `/coverage`, `/under-served`, `/facilities`
  - [x] `/reports` (CRUD citizen reports, in-memory store)
  - [x] `/heatmap/{layer_id}` (crime, litter, traffic, pothole, drainage)
  - [x] `/insights/` (dynamic city weakness report + citizen report data)

## 3. Frontend Implementation (Next.js)
- [x] Set up main layout and dark smart-city theme.
- [x] Map Integration:
  - [x] `CesiumViewer.tsx` — 3D Cesium map with flood + heatmap layers.
- [x] Sidebar & Control Panel:
  - [x] Toggle group for all layers (Flood, Traffic, Crime, Litter, Emergency, Pothole, Drainage).
  - [x] Rainfall slider (0–200mm) tied to flood risk engine.
- [x] Citizen Reporting:
  - [x] `ReportModal.tsx` — map-click triggered, category picker, API submit.
- [x] Insights Panel:
  - [x] `InsightCard.tsx` with severity badges.
  - [x] Fetch top 5 weaknesses from backend.
- [x] Emergency Panel:
  - [x] Coordinate input → coverage check against all facility types.

## 4. Integration & Verification
- [ ] Start backend: `uvicorn app.main:app --port 8000 --reload`
- [ ] Start frontend: `npm run dev`
- [ ] Test flood simulation logic.
- [ ] Test reporting flow to ensure points appear as litter/issue hotspots.
- [ ] Verify heatmap rendering in Cesium.
- [ ] Final end-to-end review and styling polish.
