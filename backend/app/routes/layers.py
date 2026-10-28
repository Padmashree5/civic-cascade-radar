"""
layers.py - New data layer endpoints: BMTC buses, noise, metro, schools,
street lights, tree canopy, BWSSB water quality, construction permits.
Each returns [{lat, lng, intensity, label, ...}] for heatmap or dot rendering.
"""
import csv
import random
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/layers", tags=["layers"])

DATASETS_DIR = Path(__file__).parent.parent.parent.parent / "datasets"


def _load_csv(filename: str, lat_col="lat", lng_col="lng") -> list[dict]:
    path = DATASETS_DIR / filename
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                rows.append({**row, "lat": float(row[lat_col]), "lng": float(row[lng_col])})
            except (ValueError, KeyError):
                continue
    return rows


# ── BMTC Bus Stops / Routes ──────────────────────────────────────────────────

@router.get("/bmtc")
def get_bmtc_layer():
    rows = _load_csv("bmtc_bus_stops.csv")
    result = []
    for r in rows:
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": float(r.get("frequency", 0.5)),
            "label": (
                f'<b>🚌 {r.get("stop_name","Bus Stop")}</b><br/>'
                f'Route: {r.get("route","—")}<br/>'
                f'Frequency: {r.get("frequency_label","Medium")}'
            ),
            "type": "bmtc",
        })
    return result


# ── Noise Pollution Stations ─────────────────────────────────────────────────

@router.get("/noise")
def get_noise_layer():
    rows = _load_csv("noise_stations.csv")
    result = []
    for r in rows:
        db_val = float(r.get("db_level", 65))
        intensity = round(min(1.0, max(0.0, (db_val - 45) / 50.0)), 3)
        if db_val >= 85:
            cat = "Critical"
        elif db_val >= 75:
            cat = "Very High"
        elif db_val >= 65:
            cat = "High"
        elif db_val >= 55:
            cat = "Moderate"
        else:
            cat = "Normal"
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": intensity,
            "db_level": db_val,
            "label": (
                f'<b>🔊 {r.get("name","Noise Station")}</b><br/>'
                f'Level: <b>{db_val} dB</b> — {cat}<br/>'
                f'Zone: {r.get("zone","—")}'
            ),
        })
    return result


# ── Metro Stations ────────────────────────────────────────────────────────────

@router.get("/metro")
def get_metro_layer():
    rows = _load_csv("metro_stations.csv")
    result = []
    for r in rows:
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": float(r.get("ridership_index", 0.7)),
            "label": (
                f'<b>🚇 {r.get("name","Metro Station")}</b><br/>'
                f'Line: {r.get("line","—")}<br/>'
                f'Daily Ridership: ~{r.get("daily_ridership","—")}'
            ),
            "line_color": r.get("line_color", "#9c27b0"),
            "line": r.get("line", ""),
        })
    return result


# ── Schools & Colleges ────────────────────────────────────────────────────────

@router.get("/schools")
def get_schools_layer():
    rows = _load_csv("school_locations.csv")
    result = []
    for r in rows:
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": float(r.get("intensity", 0.6)),
            "label": (
                f'<b>🏫 {r.get("name","School")}</b><br/>'
                f'Type: {r.get("type","—")}<br/>'
                f'Students: ~{r.get("students","—")}'
            ),
            "school_type": r.get("type", "school"),
        })
    return result


# ── Street Lights ─────────────────────────────────────────────────────────────

@router.get("/streetlights")
def get_streetlights_layer():
    rows = _load_csv("street_lights.csv")
    result = []
    for r in rows:
        status = r.get("status", "working")
        intensity = 1.0 if status == "faulty" else (0.5 if status == "dim" else 0.2)
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": intensity,
            "status": status,
            "label": (
                f'<b>💡 Street Light</b><br/>'
                f'Status: <b>{status.upper()}</b><br/>'
                f'Zone: {r.get("zone","—")}'
            ),
        })
    return result


# ── Tree Canopy / Green Cover ─────────────────────────────────────────────────

@router.get("/trees")
def get_trees_layer():
    rows = _load_csv("tree_canopy.csv")
    result = []
    for r in rows:
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": float(r.get("canopy_density", 0.5)),
            "label": (
                f'<b>🌳 Green Cover</b><br/>'
                f'Canopy Density: {float(r.get("canopy_density",0.5))*100:.0f}%<br/>'
                f'Ward: {r.get("ward","—")}'
            ),
        })
    return result


# ── BWSSB Water Quality Zones ─────────────────────────────────────────────────

@router.get("/water-quality")
def get_water_quality_layer():
    rows = _load_csv("bwssb_water_zones.csv")
    result = []
    for r in rows:
        score = float(r.get("quality_score", 0.7))
        intensity = round(1.0 - score, 3)  # low quality = high intensity (alert)
        if score >= 0.85:
            status = "Excellent"
        elif score >= 0.70:
            status = "Good"
        elif score >= 0.50:
            status = "Fair"
        else:
            status = "Poor"
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": intensity,
            "quality_score": score,
            "label": (
                f'<b>💧 {r.get("zone_name","Water Zone")}</b><br/>'
                f'Quality: <b>{status}</b> ({score*100:.0f}/100)<br/>'
                f'pH: {r.get("ph","—")} | TDS: {r.get("tds","—")} ppm'
            ),
        })
    return result


# ── BBMP Construction Permits ─────────────────────────────────────────────────

@router.get("/construction")
def get_construction_layer():
    rows = _load_csv("construction_permits.csv")
    result = []
    for r in rows:
        result.append({
            "lat": r["lat"],
            "lng": r["lng"],
            "intensity": float(r.get("intensity", 0.6)),
            "label": (
                f'<b>🏗️ Construction Permit</b><br/>'
                f'Type: {r.get("type","—")}<br/>'
                f'Status: {r.get("status","Active")}<br/>'
                f'Ward: {r.get("ward","—")}'
            ),
        })
    return result


# ── KSNDMC Rainfall (live via weather service) ────────────────────────────────

@router.get("/rainfall")
async def get_rainfall_layer():
    from ..services.weather_service import get_rainfall_heatmap
    return await get_rainfall_heatmap()
