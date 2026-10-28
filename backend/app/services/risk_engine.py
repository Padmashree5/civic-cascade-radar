"""
risk_engine.py — Flood simulation using rainfall intensity + historically-validated
elevation and drainage data for Bengaluru zones.

Elevation data: SRTM 30m DEM (NASA/ISRO BHUVAN)
Drainage scores: BBMP Storm Water Drain Master Plan (2015–2022)
Historical risk: BBMP Flood Survey Reports 2017, 2019, 2021, 2022 + IMD rainfall records
"""
import math
from typing import List, Dict, Any

# Historical flood occurrence weight from BBMP survey records
_HISTORICAL_BASE: Dict[str, float] = {
    "HIGH":   0.40,
    "MEDIUM": 0.18,
    "LOW":    0.0,
}

# Zone data backed by SRTM elevation, BBMP SWD drain scores, and flood survey history
ZONES = [
    # ── HIGH flood risk — BBMP flood surveys 2017–2022 ──
    # Koramangala: Encroached lake beds, repeated flooding every monsoon
    {"name": "Koramangala",    "lat": 12.9352, "lng": 77.6245, "elev": 867, "drain": 2, "historical_risk": "HIGH"},
    # BTM Layout: Madivala lake catchment, annual inundation
    {"name": "BTM Layout",     "lat": 12.9165, "lng": 77.6101, "elev": 861, "drain": 3, "historical_risk": "HIGH"},
    # HSR Layout: Built on dried lake beds, chronic flooding
    {"name": "HSR Layout",     "lat": 12.9116, "lng": 77.6389, "elev": 864, "drain": 3, "historical_risk": "HIGH"},
    # Bellandur: Lowest zone, Bellandur lake overflow area
    {"name": "Bellandur",      "lat": 12.9201, "lng": 77.6700, "elev": 855, "drain": 2, "historical_risk": "HIGH"},
    # Ejipura: Low-lying depression, severe waterlogging
    {"name": "Ejipura",        "lat": 12.9441, "lng": 77.6234, "elev": 867, "drain": 3, "historical_risk": "HIGH"},
    # Varthur: Varthur lake overflow, major flooding 2022
    {"name": "Varthur",        "lat": 12.9388, "lng": 77.7264, "elev": 863, "drain": 2, "historical_risk": "HIGH"},
    # Marathahalli: Varthur lake downstream, IT corridor flooding 2022
    {"name": "Marathahalli",   "lat": 12.9591, "lng": 77.6971, "elev": 866, "drain": 3, "historical_risk": "HIGH"},

    # ── MEDIUM flood risk ──
    # Indiranagar: Ulsoor lake adjacent, moderate flooding history
    {"name": "Indiranagar",    "lat": 12.9784, "lng": 77.6408, "elev": 878, "drain": 5, "historical_risk": "MEDIUM"},
    # Jayanagar: Aging drainage, moderate risk
    {"name": "Jayanagar",      "lat": 12.9308, "lng": 77.5838, "elev": 874, "drain": 5, "historical_risk": "MEDIUM"},
    # JP Nagar: Lake-adjacent zones, periodic flooding
    {"name": "JP Nagar",       "lat": 12.9102, "lng": 77.5850, "elev": 869, "drain": 5, "historical_risk": "MEDIUM"},
    # Ulsoor: Ulsoor lake flood zone
    {"name": "Ulsoor",         "lat": 12.9860, "lng": 77.6235, "elev": 871, "drain": 4, "historical_risk": "MEDIUM"},
    # Electronic City: Industrial drainage, seasonal waterlogging
    {"name": "Electronic City","lat": 12.8391, "lng": 77.6781, "elev": 862, "drain": 6, "historical_risk": "MEDIUM"},
    # Hebbal: Hebbal lake overflow zone, northern valley
    {"name": "Hebbal",         "lat": 13.0354, "lng": 77.5967, "elev": 895, "drain": 6, "historical_risk": "MEDIUM"},
    # Banaswadi: Valley-adjacent, moderate risk
    {"name": "Banaswadi",      "lat": 13.0107, "lng": 77.6444, "elev": 880, "drain": 5, "historical_risk": "MEDIUM"},
    # Whitefield: IT corridor lakes, moderate flooding history
    {"name": "Whitefield",     "lat": 12.9698, "lng": 77.7499, "elev": 868, "drain": 4, "historical_risk": "MEDIUM"},

    # ── LOW flood risk — elevated terrain, better drainage ──
    # Malleshwaram: Elevated ridge, well-maintained British-era drains
    {"name": "Malleshwaram",   "lat": 12.9983, "lng": 77.5706, "elev": 907, "drain": 8, "historical_risk": "LOW"},
    # Yeshwanthpur: Highest elevation in dataset, good drainage
    {"name": "Yeshwanthpur",   "lat": 13.0262, "lng": 77.5519, "elev": 927, "drain": 7, "historical_risk": "LOW"},
    # Rajajinagar: Mid-elevation, improved drainage post-2019
    {"name": "Rajajinagar",    "lat": 12.9911, "lng": 77.5538, "elev": 893, "drain": 5, "historical_risk": "LOW"},
    # City Centre (MG Road): Elevated plateau, good storm drain coverage
    {"name": "City Centre",    "lat": 12.9716, "lng": 77.5946, "elev": 896, "drain": 6, "historical_risk": "LOW"},
]

_ELEV_MIN = min(z["elev"] for z in ZONES)
_ELEV_MAX = max(z["elev"] for z in ZONES)


def _flood_score(zone: Dict, rainfall_mm: float) -> float:
    """
    Flood risk score 0.0–1.0 combining:
    - 30% rainfall intensity (IMD-scale, log-normalised to 200mm)
    - 15% terrain elevation (SRTM, lower = higher risk)
    - 15% drainage capacity (BBMP SWD score, lower = higher risk)
    - 40% historical flood occurrence (BBMP survey records)
    """
    elev_norm = 1.0 - (zone["elev"] - _ELEV_MIN) / (_ELEV_MAX - _ELEV_MIN + 1)
    drain_risk = 1.0 - zone["drain"] / 10.0
    rain_norm = min(math.log1p(rainfall_mm) / math.log1p(200), 1.0)
    hist_base = _HISTORICAL_BASE.get(zone.get("historical_risk", "LOW"), 0.0)

    score = 0.30 * rain_norm + 0.15 * elev_norm + 0.15 * drain_risk + 0.40 * hist_base
    return round(min(score, 1.0), 3)


def _risk_label(score: float) -> str:
    if score >= 0.55:
        return "HIGH"
    if score >= 0.32:
        return "MEDIUM"
    return "LOW"


def simulate_flood(rainfall_mm: float) -> Dict[str, Any]:
    features: List[Dict] = []
    high_count = medium_count = 0

    for zone in ZONES:
        score = _flood_score(zone, rainfall_mm)
        label = _risk_label(score)
        if label == "HIGH":
            high_count += 1
        elif label == "MEDIUM":
            medium_count += 1

        features.append({
            "type": "Feature",
            "properties": {
                "name": zone["name"],
                "risk": label,
                "score": score,
                "elevation_m": zone["elev"],
                "drainage_score": zone["drain"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [zone["lng"], zone["lat"]],
            },
        })

    if high_count > 0:
        summary = f"⚠ {high_count} HIGH-RISK zones detected ({rainfall_mm}mm rainfall)"
    elif medium_count > 0:
        summary = f"⚡ {medium_count} MEDIUM-RISK zones detected ({rainfall_mm}mm rainfall)"
    else:
        summary = f"✅ All zones SAFE at {rainfall_mm}mm rainfall"

    return {"type": "FeatureCollection", "features": features, "summary": summary}
