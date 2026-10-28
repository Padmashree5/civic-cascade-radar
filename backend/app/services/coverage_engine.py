"""
coverage_engine.py — Compute emergency facility coverage and identify under-served zones.
Uses haversine distance and response-time thresholds defined per facility type.
"""
import math
from typing import List, Dict, Any, Optional

# ---- Load real facility data from CSV, fall back to static set ----
def _load_facilities() -> List[Dict]:
    try:
        from .data_service import load_emergency_services
        csv_data = load_emergency_services()
        if csv_data:
            return csv_data
    except Exception as e:
        print(f"[coverage_engine] Could not load CSV facilities: {e}")
    # Static fallback
    return [
        # ── Fire Stations ──
        {"id": "F1",  "type": "fire",     "name": "Shivajinagar Fire Station",       "lat": 12.9866, "lng": 77.6033},
        {"id": "F2",  "type": "fire",     "name": "Rajajinagar Fire Station",         "lat": 12.9965, "lng": 77.5481},
        {"id": "F3",  "type": "fire",     "name": "Koramangala Fire Station",         "lat": 12.9354, "lng": 77.6231},
        {"id": "F4",  "type": "fire",     "name": "Hebbal Fire Station",              "lat": 13.0370, "lng": 77.5956},
        {"id": "F5",  "type": "fire",     "name": "Malleshwaram Fire Station",        "lat": 12.9960, "lng": 77.5700},
        {"id": "F6",  "type": "fire",     "name": "Jayanagar Fire Station",           "lat": 12.9300, "lng": 77.5830},
        {"id": "F7",  "type": "fire",     "name": "Electronic City Fire Station",     "lat": 12.8400, "lng": 77.6780},
        {"id": "F8",  "type": "fire",     "name": "Whitefield Fire Station",          "lat": 12.9680, "lng": 77.7480},
        {"id": "F9",  "type": "fire",     "name": "Yeshwanthpur Fire Station",        "lat": 13.0200, "lng": 77.5490},
        # ── Hospitals ──
        {"id": "H1",  "type": "hospital", "name": "Bowring & Lady Curzon Hospital",   "lat": 12.9784, "lng": 77.6114},
        {"id": "H2",  "type": "hospital", "name": "Nimhans Hospital",                 "lat": 12.9416, "lng": 77.5952},
        {"id": "H3",  "type": "hospital", "name": "Manipal Hospital",                 "lat": 12.9580, "lng": 77.6470},
        {"id": "H4",  "type": "hospital", "name": "St. John's Medical College",       "lat": 12.9267, "lng": 77.6209},
        {"id": "H5",  "type": "hospital", "name": "Fortis Hospital Bannerghatta",     "lat": 12.8730, "lng": 77.5977},
        {"id": "H6",  "type": "hospital", "name": "Jayadeva Institute of Cardiology", "lat": 12.9356, "lng": 77.6067},
        {"id": "H7",  "type": "hospital", "name": "Bangalore Baptist Hospital",       "lat": 13.0240, "lng": 77.5887},
        {"id": "H8",  "type": "hospital", "name": "Columbia Asia Hospital Hebbal",    "lat": 13.0350, "lng": 77.5950},
        {"id": "H9",  "type": "hospital", "name": "Narayana Health City",             "lat": 12.8684, "lng": 77.6021},
        {"id": "H10", "type": "hospital", "name": "Sakra World Hospital Whitefield",  "lat": 12.9590, "lng": 77.7080},
        {"id": "H11", "type": "hospital", "name": "Cloudnine Hospital Whitefield",    "lat": 12.9720, "lng": 77.7450},
        # ── Police Stations ──
        {"id": "P1",  "type": "police",   "name": "Cubbon Park Police Station",       "lat": 12.9741, "lng": 77.5940},
        {"id": "P2",  "type": "police",   "name": "Whitefield Police Station",        "lat": 12.9698, "lng": 77.7499},
        {"id": "P3",  "type": "police",   "name": "HSR Layout Police Station",        "lat": 12.9116, "lng": 77.6389},
        {"id": "P4",  "type": "police",   "name": "Yeshwanthpur Police Station",      "lat": 13.0262, "lng": 77.5519},
        {"id": "P5",  "type": "police",   "name": "Jayanagar Police Station",         "lat": 12.9229, "lng": 77.5793},
        {"id": "P6",  "type": "police",   "name": "Koramangala Police Station",       "lat": 12.9354, "lng": 77.6231},
        {"id": "P7",  "type": "police",   "name": "Marathahalli Police Station",      "lat": 12.9591, "lng": 77.6971},
        {"id": "P8",  "type": "police",   "name": "Hebbal Police Station",            "lat": 13.0354, "lng": 77.5967},
        {"id": "P9",  "type": "police",   "name": "Electronic City Police Station",   "lat": 12.8391, "lng": 77.6781},
        {"id": "P10", "type": "police",   "name": "Indiranagar Police Station",       "lat": 12.9784, "lng": 77.6408},
        {"id": "P11", "type": "police",   "name": "Rajajinagar Police Station",       "lat": 12.9911, "lng": 77.5538},
        {"id": "P12", "type": "police",   "name": "Malleshwaram Police Station",      "lat": 12.9983, "lng": 77.5706},
    ]

FACILITIES: List[Dict] = _load_facilities()

# Response time thresholds (minutes) — if ETA exceeds this → UNDER-SERVED
RESPONSE_THRESHOLDS: Dict[str, float] = {
    "fire":     8.0,
    "hospital": 12.0,
    "police":   10.0,
}

CITY_SPEED_KMPH = 25.0  # average speed for ETA calculation


def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest(lat: float, lng: float, facility_type: str) -> Dict[str, Any]:
    candidates = [f for f in FACILITIES if f["type"] == facility_type]
    if not candidates:
        return {"error": f"No facilities of type '{facility_type}' found."}

    def dist_eta(f):
        d = haversine(lat, lng, f["lat"], f["lng"])
        eta = (d / CITY_SPEED_KMPH) * 60
        return d, eta

    best = min(candidates, key=lambda f: haversine(lat, lng, f["lat"], f["lng"]))
    dist_km, eta_mins = dist_eta(best)
    threshold = RESPONSE_THRESHOLDS.get(facility_type, 10.0)

    return {
        "facility": best,
        "distance_km": round(dist_km, 2),
        "eta_minutes": round(eta_mins, 1),
        "status": "UNDER-SERVED" if eta_mins > threshold else "OPTIMAL",
        "delay_warning": "CRITICAL DELAY" if eta_mins > threshold * 1.5 else ("DELAYED" if eta_mins > threshold else "NORMAL"),
    }


def get_all_coverage_for_point(lat: float, lng: float) -> Dict[str, Any]:
    """Return nearest facility of each type for a given location."""
    results = {}
    for ftype in ["fire", "hospital", "police"]:
        results[ftype] = find_nearest(lat, lng, ftype)
    return results


def get_under_served_zones() -> List[Dict[str, Any]]:
    """
    Check a grid of Bangalore city points and identify areas with UNDER-SERVED coverage.
    Returns a list of problem zones.
    """
    # Sample grid: ~20 key areas to check
    check_points = [
        {"name": "Whitefield", "lat": 12.9698, "lng": 77.7499},
        {"name": "Electronic City", "lat": 12.8391, "lng": 77.6781},
        {"name": "Kanakapura", "lat": 12.7907, "lng": 77.5774},
        {"name": "Yelahanka", "lat": 13.0998, "lng": 77.5962},
        {"name": "HSR Layout", "lat": 12.9116, "lng": 77.6389},
        {"name": "Koramangala", "lat": 12.9354, "lng": 77.6231},
        {"name": "City Centre", "lat": 12.9716, "lng": 77.5946},
        {"name": "Hebbal", "lat": 13.0354, "lng": 77.5967},
    ]

    under_served = []
    for pt in check_points:
        for ftype in ["fire", "hospital", "police"]:
            res = find_nearest(pt["lat"], pt["lng"], ftype)
            if res.get("status") == "UNDER-SERVED":
                under_served.append({
                    "zone": pt["name"],
                    "facility_type": ftype,
                    "eta_minutes": res["eta_minutes"],
                    "nearest_facility": res["facility"]["name"],
                    "delay_warning": res["delay_warning"],
                })
    return under_served
