from fastapi import APIRouter, Query
from typing import List, Optional
from ..services.coverage_engine import find_nearest, get_all_coverage_for_point, get_under_served_zones
from ..services.osm_service import get_facilities_geojson, fetch_facilities_from_overpass

router = APIRouter(prefix="/emergency", tags=["emergency"])

@router.get("/nearest")
def get_nearest_facility(
    lat: float,
    lng: float,
    facility_type: str = Query(..., description="fire, hospital, or police")
):
    return find_nearest(lat, lng, facility_type)

@router.get("/coverage")
def get_full_coverage(lat: float, lng: float):
    return get_all_coverage_for_point(lat, lng)

@router.get("/under-served")
def get_under_served():
    return {"under_served_zones": get_under_served_zones()}

@router.get("/facilities")
def get_facilities(facility_type: str = None):
    """Static fallback GeoJSON of Bangalore facilities."""
    return get_facilities_geojson(facility_type)

@router.get("/simulate")
def simulate_emergency_response(
    lat: float,
    lng: float,
    radius_km: float = Query(1.0, description="Radius in km (for rain/flood mode)"),
    mode: str = Query("crime", description="'rain' or 'crime'"),
):
    """
    Simulate emergency response for an incident or flooded zone.
    Returns nearest police, hospital, and fire station with ETA and route details.
    Used by the map simulation overlay.
    """
    from ..services.coverage_engine import get_all_coverage_for_point, FACILITIES, haversine, RESPONSE_THRESHOLDS, CITY_SPEED_KMPH

    # Manpower estimates per unit type (personnel dispatched per vehicle/unit)
    MANPOWER = {"fire": 6, "hospital": 4, "police": 3}

    if mode == "rain":
        # Rain/flood: dispatch ALL facilities within search radius, sorted by distance
        search_radius = max(radius_km * 2.5, 5.0)
        responders = []
        for f in FACILITIES:
            d = haversine(lat, lng, f["lat"], f["lng"])
            if d <= search_radius:
                eta = (d / CITY_SPEED_KMPH) * 60
                threshold = RESPONSE_THRESHOLDS.get(f["type"], 10.0)
                is_delayed = eta > threshold
                responders.append({
                    "type": f["type"],
                    "name": f["name"],
                    "facility_lat": f["lat"],
                    "facility_lng": f["lng"],
                    "distance_km": round(d, 2),
                    "eta_minutes": round(eta, 1),
                    "status": "UNDER-SERVED" if is_delayed else "OPTIMAL",
                    "delay_warning": "CRITICAL DELAY" if eta > threshold * 1.5 else ("DELAYED" if is_delayed else "NORMAL"),
                    "manpower": MANPOWER.get(f["type"], 3),
                })
        responders.sort(key=lambda r: r["distance_km"])
        total_manpower = sum(r["manpower"] for r in responders)
        summary = (
            f"{len(responders)} units dispatched within {search_radius:.1f} km — "
            f"{total_manpower} personnel mobilised. "
            f"Nearest: {responders[0]['name']} ({responders[0]['eta_minutes']} min)." if responders
            else "No facilities found within radius."
        )
    else:
        # Crime: one fastest unit of each type — response time is critical
        coverage = get_all_coverage_for_point(lat, lng)
        responders = []
        for ftype, data in coverage.items():
            if "facility" not in data:
                continue
            f = data["facility"]
            responders.append({
                "type": ftype,
                "name": f["name"],
                "facility_lat": f["lat"],
                "facility_lng": f["lng"],
                "distance_km": data["distance_km"],
                "eta_minutes": data["eta_minutes"],
                "status": data["status"],
                "delay_warning": data["delay_warning"],
                "manpower": MANPOWER.get(ftype, 3),
            })
        summary = (
            f"{len(responders)} units dispatched. "
            f"Fastest ETA: {min((r['eta_minutes'] for r in responders), default=0):.1f} min."
        )

    return {
        "mode": mode,
        "incident": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "responders": responders,
        "summary": summary,
    }


@router.get("/facilities-osm")
def get_facilities_osm(
    city: str = Query("Bangalore", description="City name"),
    amenity: str = Query("all", description="Comma-separated amenity types or 'all'")
):
    """
    Fetch live facility data from OpenStreetMap via Overpass API.
    amenity options: fire_station, hospital, clinic, police, ambulance_station,
                     pharmacy, school, college — or 'all'.
    """
    if amenity == "all":
        types = None
    else:
        types = [a.strip() for a in amenity.split(",")]
    return fetch_facilities_from_overpass(city=city, amenity_types=types)
