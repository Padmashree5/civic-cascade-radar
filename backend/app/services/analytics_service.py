"""
analytics_service.py - ML-lite analytics: pothole risk, crime hotspots,
flood risk scoring, anomaly detection, emergency dispatch optimization.
Uses pure Python + basic statistics — no heavy ML dependencies.
"""
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ── Bengaluru ward centroids for scoring ────────────────────────────────────

WARDS = [
    {"id": 1,  "name": "Majestic",         "lat": 12.9716, "lng": 77.5946},
    {"id": 2,  "name": "Whitefield",       "lat": 12.9352, "lng": 77.6244},
    {"id": 3,  "name": "Marathahalli",     "lat": 12.9780, "lng": 77.6408},
    {"id": 4,  "name": "Bommanahalli",     "lat": 12.8340, "lng": 77.6602},
    {"id": 5,  "name": "Hebbal",           "lat": 13.0067, "lng": 77.5963},
    {"id": 6,  "name": "Jayanagar",        "lat": 12.9007, "lng": 77.5996},
    {"id": 7,  "name": "Rajajinagar",      "lat": 12.9600, "lng": 77.5700},
    {"id": 8,  "name": "BTM Layout",       "lat": 12.8440, "lng": 77.6100},
    {"id": 9,  "name": "HAL",              "lat": 12.9280, "lng": 77.6276},
    {"id": 10, "name": "Yelahanka",        "lat": 13.0360, "lng": 77.5970},
    {"id": 11, "name": "Indiranagar",      "lat": 12.9580, "lng": 77.6060},
    {"id": 12, "name": "Basavanagudi",     "lat": 12.9200, "lng": 77.5800},
    {"id": 13, "name": "Koramangala",      "lat": 12.9350, "lng": 77.6270},
    {"id": 14, "name": "Electronic City",  "lat": 12.8455, "lng": 77.6603},
    {"id": 15, "name": "JP Nagar",         "lat": 12.9076, "lng": 77.5838},
    {"id": 16, "name": "Banashankari",     "lat": 12.9091, "lng": 77.5466},
    {"id": 17, "name": "HSR Layout",       "lat": 12.9075, "lng": 77.6473},
    {"id": 18, "name": "Yelahanka New",    "lat": 13.1007, "lng": 77.5960},
]

# Road quality index per ward (0=bad, 1=good) - from domain knowledge
_ROAD_QUALITY = {
    "Majestic": 0.35, "Whitefield": 0.55, "Marathahalli": 0.48,
    "Bommanahalli": 0.30, "Hebbal": 0.60, "Jayanagar": 0.70,
    "Rajajinagar": 0.50, "BTM Layout": 0.42, "HAL": 0.65,
    "Yelahanka": 0.58, "Indiranagar": 0.72, "Basavanagudi": 0.68,
    "Koramangala": 0.75, "Electronic City": 0.40, "JP Nagar": 0.62,
    "Banashankari": 0.55, "HSR Layout": 0.70, "Yelahanka New": 0.45,
}

# Average annual rainfall mm (higher → more potholes)
_RAINFALL_INDEX = {
    "Majestic": 0.80, "Whitefield": 0.65, "Marathahalli": 0.70,
    "Bommanahalli": 0.75, "Hebbal": 0.60, "Jayanagar": 0.55,
    "Rajajinagar": 0.60, "BTM Layout": 0.72, "HAL": 0.55,
    "Yelahanka": 0.50, "Indiranagar": 0.60, "Basavanagudi": 0.58,
    "Koramangala": 0.62, "Electronic City": 0.78, "JP Nagar": 0.55,
    "Banashankari": 0.60, "HSR Layout": 0.65, "Yelahanka New": 0.52,
}

# Traffic volume index per ward
_TRAFFIC_INDEX = {
    "Majestic": 0.95, "Whitefield": 0.88, "Marathahalli": 0.90,
    "Bommanahalli": 0.70, "Hebbal": 0.75, "Jayanagar": 0.65,
    "Rajajinagar": 0.72, "BTM Layout": 0.80, "HAL": 0.68,
    "Yelahanka": 0.55, "Indiranagar": 0.75, "Basavanagudi": 0.60,
    "Koramangala": 0.85, "Electronic City": 0.82, "JP Nagar": 0.65,
    "Banashankari": 0.62, "HSR Layout": 0.78, "Yelahanka New": 0.50,
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ── Pothole Risk Prediction ──────────────────────────────────────────────────

def compute_pothole_risk(live_rainfall_mm: float = 0.0) -> list[dict]:
    """
    Score each ward's pothole risk using:
    - road quality (inverse: bad road → high risk)
    - rainfall (both historical index + current live mm)
    - traffic volume
    Returns list of {ward, lat, lng, risk_score (0-1), risk_level, factors}
    """
    results = []
    for ward in WARDS:
        name = ward["name"]
        road_inv = 1.0 - _ROAD_QUALITY.get(name, 0.5)
        rain = _RAINFALL_INDEX.get(name, 0.6) * 0.6 + min(1.0, live_rainfall_mm / 20.0) * 0.4
        traffic = _TRAFFIC_INDEX.get(name, 0.6)

        # Weighted combination
        raw = 0.35 * road_inv + 0.40 * rain + 0.25 * traffic
        score = round(_sigmoid((raw - 0.5) * 8) , 3)

        if score >= 0.80:
            level = "CRITICAL"
        elif score >= 0.65:
            level = "HIGH"
        elif score >= 0.45:
            level = "MEDIUM"
        else:
            level = "LOW"

        results.append({
            "ward": name,
            "lat": ward["lat"],
            "lng": ward["lng"],
            "risk_score": score,
            "risk_level": level,
            "factors": {
                "road_quality": round(1.0 - road_inv, 2),
                "rainfall_index": round(rain, 2),
                "traffic_volume": round(traffic, 2),
            },
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


# ── Crime Hotspot Prediction ─────────────────────────────────────────────────

_CRIME_BASE = {
    "Majestic": 0.90, "BTM Layout": 0.78, "Marathahalli": 0.72,
    "Bommanahalli": 0.68, "Whitefield": 0.65, "Hebbal": 0.55,
    "Rajajinagar": 0.62, "HAL": 0.50, "Yelahanka": 0.48,
    "Indiranagar": 0.58, "Basavanagudi": 0.45, "Koramangala": 0.60,
    "Electronic City": 0.52, "Jayanagar": 0.42, "JP Nagar": 0.40,
    "Banashankari": 0.38, "HSR Layout": 0.55, "Yelahanka New": 0.35,
}

_CRIME_TIME_MULTIPLIER = {
    "morning": 0.60, "afternoon": 0.75, "evening": 1.20, "night": 1.40,
}


def _time_of_day(hour: int) -> str:
    if 6 <= hour < 12: return "morning"
    if 12 <= hour < 17: return "afternoon"
    if 17 <= hour < 21: return "evening"
    return "night"


def compute_crime_hotspots(hour: int | None = None) -> list[dict]:
    """
    Predict crime risk per ward with time-of-day multiplier.
    hour=None uses current UTC+5:30 hour.
    """
    if hour is None:
        ist_hour = (datetime.utcnow().hour + 5) % 24  # approximate IST
        hour = ist_hour

    tod = _time_of_day(hour)
    multiplier = _CRIME_TIME_MULTIPLIER[tod]

    results = []
    for ward in WARDS:
        name = ward["name"]
        base = _CRIME_BASE.get(name, 0.50)
        score = round(min(1.0, base * multiplier), 3)

        if score >= 0.85:
            label = "HOTSPOT"
        elif score >= 0.65:
            label = "HIGH RISK"
        elif score >= 0.45:
            label = "MODERATE"
        else:
            label = "LOW RISK"

        results.append({
            "ward": name,
            "lat": ward["lat"],
            "lng": ward["lng"],
            "risk_score": score,
            "risk_label": label,
            "time_of_day": tod,
            "peak_hours": "18:00–23:00" if base > 0.65 else "20:00–01:00",
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


# ── Flood Risk Scoring ────────────────────────────────────────────────────────

_FLOOD_BASE = {
    "Majestic": 0.72, "BTM Layout": 0.80, "Indiranagar": 0.65,
    "Marathahalli": 0.78, "Bommanahalli": 0.70, "Whitefield": 0.55,
    "Hebbal": 0.60, "Rajajinagar": 0.58, "HAL": 0.50,
    "Yelahanka": 0.45, "Basavanagudi": 0.62, "Koramangala": 0.68,
    "Electronic City": 0.75, "Jayanagar": 0.55, "JP Nagar": 0.50,
    "Banashankari": 0.58, "HSR Layout": 0.72, "Yelahanka New": 0.42,
}

_DRAINAGE_QUALITY = {
    "Majestic": 0.30, "BTM Layout": 0.35, "Indiranagar": 0.60,
    "Marathahalli": 0.40, "Bommanahalli": 0.35, "Whitefield": 0.58,
    "Hebbal": 0.62, "Rajajinagar": 0.50, "HAL": 0.65,
    "Yelahanka": 0.70, "Basavanagudi": 0.55, "Koramangala": 0.65,
    "Electronic City": 0.38, "Jayanagar": 0.68, "JP Nagar": 0.62,
    "Banashankari": 0.60, "HSR Layout": 0.55, "Yelahanka New": 0.72,
}


def compute_flood_risk(live_rainfall_mm: float = 0.0) -> list[dict]:
    """
    Combine terrain susceptibility, drainage quality, and live rainfall
    to produce per-ward flood risk scores.
    """
    results = []
    rain_factor = min(1.0, live_rainfall_mm / 25.0)  # 25mm = saturating rain

    for ward in WARDS:
        name = ward["name"]
        terrain = _FLOOD_BASE.get(name, 0.55)
        drain_inv = 1.0 - _DRAINAGE_QUALITY.get(name, 0.55)

        score = round(
            _sigmoid((0.40 * terrain + 0.35 * drain_inv + 0.25 * rain_factor - 0.5) * 7),
            3
        )

        if score >= 0.80:
            alert = "EVACUATE"
        elif score >= 0.65:
            alert = "HIGH ALERT"
        elif score >= 0.45:
            alert = "WATCH"
        else:
            alert = "NORMAL"

        results.append({
            "ward": name,
            "lat": ward["lat"],
            "lng": ward["lng"],
            "flood_risk": score,
            "alert_level": alert,
            "live_rainfall_mm": round(live_rainfall_mm, 1),
            "drainage_quality": round(1.0 - drain_inv, 2),
        })

    results.sort(key=lambda x: x["flood_risk"], reverse=True)
    return results


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def detect_anomalies(reports: list[dict], window_minutes: int = 60) -> list[dict]:
    """
    Detect wards with abnormal spikes in citizen reports within a time window.
    reports: list of {lat, lng, category, created_at (ISO str)}
    Returns list of anomalies with ward, spike count, and severity.
    """
    from .data_service import CRIME_ZONES  # reuse zone centroids

    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)

    # Assign each report to nearest ward
    def nearest_ward(lat, lng) -> str:
        best, best_d = "Unknown", float("inf")
        for w in WARDS:
            d = math.hypot(lat - w["lat"], lng - w["lng"])
            if d < best_d:
                best_d = d
                best = w["name"]
        return best

    zone_counts: dict[str, int] = defaultdict(int)
    for r in reports:
        try:
            created = datetime.fromisoformat(r.get("created_at", "").replace("Z", ""))
            if created >= cutoff:
                ward = nearest_ward(float(r["lat"]), float(r["lng"]))
                zone_counts[ward] += 1
        except (ValueError, KeyError, TypeError):
            continue

    # Threshold: 3+ reports in window = anomaly
    anomalies = []
    for ward_name, count in zone_counts.items():
        if count >= 3:
            ward_info = next((w for w in WARDS if w["name"] == ward_name), None)
            anomalies.append({
                "ward": ward_name,
                "lat": ward_info["lat"] if ward_info else 12.9716,
                "lng": ward_info["lng"] if ward_info else 77.5946,
                "report_count": count,
                "window_minutes": window_minutes,
                "severity": "CRITICAL" if count >= 8 else ("HIGH" if count >= 5 else "MODERATE"),
                "message": f"{count} reports in {window_minutes} min",
            })

    anomalies.sort(key=lambda x: x["report_count"], reverse=True)
    return anomalies


# ── Emergency Dispatch Optimizer ──────────────────────────────────────────────

def optimize_dispatch(
    incident_lat: float,
    incident_lng: float,
    incident_type: str,
    available_units: list[dict] | None = None,
) -> dict:
    """
    Assign best available units to an incident using a greedy nearest-first
    assignment algorithm.
    available_units: list of {id, type, lat, lng, status}
    If None, uses FACILITIES from coverage_engine.
    """
    from .coverage_engine import FACILITIES

    if available_units is None:
        available_units = [
            {"id": f["name"], "type": f["type"], "lat": f["lat"], "lng": f["lng"], "status": "AVAILABLE"}
            for f in FACILITIES
        ]

    def _dist(u):
        return math.sqrt((u["lat"] - incident_lat) ** 2 + (u["lng"] - incident_lng) ** 2)

    # Filter by type relevance
    type_priority = {
        "crime": ["police", "hospital"],
        "fire": ["fire", "hospital"],
        "medical": ["hospital", "fire"],
        "accident": ["hospital", "police", "fire"],
        "flood": ["fire", "hospital", "police"],
    }
    preferred = type_priority.get(incident_type, ["police", "hospital", "fire"])

    assignments = []
    for unit_type in preferred:
        candidates = [u for u in available_units if u["type"] == unit_type and u["status"] == "AVAILABLE"]
        if candidates:
            best = min(candidates, key=_dist)
            dist_deg = _dist(best)
            dist_km = dist_deg * 111.0
            eta_min = round((dist_km / 25.0) * 60, 1)
            assignments.append({
                "unit_id": best["id"],
                "unit_type": unit_type,
                "unit_lat": best["lat"],
                "unit_lng": best["lng"],
                "distance_km": round(dist_km, 2),
                "eta_minutes": eta_min,
                "priority": preferred.index(unit_type) + 1,
            })

    return {
        "incident": {"lat": incident_lat, "lng": incident_lng, "type": incident_type},
        "assignments": assignments,
        "total_units": len(assignments),
        "fastest_eta": min((a["eta_minutes"] for a in assignments), default=None),
    }


# ── Ward Summary (drill-down) ─────────────────────────────────────────────────

def get_ward_summary(ward_name: str, live_rainfall_mm: float = 0.0) -> dict | None:
    """Return all analytics scores for a single ward."""
    ward = next((w for w in WARDS if w["name"].lower() == ward_name.lower()), None)
    if not ward:
        return None

    pothole = next((p for p in compute_pothole_risk(live_rainfall_mm) if p["ward"] == ward["name"]), {})
    crime = next((c for c in compute_crime_hotspots() if c["ward"] == ward["name"]), {})
    flood = next((f for f in compute_flood_risk(live_rainfall_mm) if f["ward"] == ward["name"]), {})

    return {
        "ward": ward["name"],
        "lat": ward["lat"],
        "lng": ward["lng"],
        "pothole_risk": pothole.get("risk_score"),
        "pothole_level": pothole.get("risk_level"),
        "crime_risk": crime.get("risk_score"),
        "crime_label": crime.get("risk_label"),
        "flood_risk": flood.get("flood_risk"),
        "flood_alert": flood.get("alert_level"),
        "live_rainfall_mm": live_rainfall_mm,
    }
