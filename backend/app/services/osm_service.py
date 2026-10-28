"""
osm_service.py — City infrastructure data provider.
Fetches real facility data from OpenStreetMap via the Overpass API.
Falls back to static data if Overpass is unavailable.
"""
import json
import math
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

# ---- Cache ----
_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
CACHE_TTL = 300  # 5 minutes


def _fetch_overpass(query: str) -> Optional[dict]:
    """Execute an Overpass QL query and return parsed JSON or None."""
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"User-Agent": "SmartCityIntel/1.0"})
        with urllib.request.urlopen(req, timeout=65) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[Overpass] error: {e}")
        return None


def _overpass_to_geojson(raw: dict, facility_type: str) -> List[Dict]:
    """Convert Overpass JSON elements to GeoJSON Feature dicts."""
    features = []
    for el in raw.get("elements", []):
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if not lat or not lon:
            continue
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or f"Unnamed {facility_type.replace('_', ' ').title()}"
        features.append({
            "type": "Feature",
            "properties": {
                "id": str(el.get("id", "")),
                "name": name,
                "facility_type": facility_type,
                "amenity": tags.get("amenity", facility_type),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "operator": tags.get("operator"),
                "beds": tags.get("beds"),
                "speciality": tags.get("healthcare:speciality"),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        })
    return features


# ---- Facility type → Overpass amenity tag mapping ----
AMENITY_MAP = {
    "fire_station":       'amenity=fire_station',
    "hospital":           'amenity=hospital',
    "clinic":             'amenity=clinic',
    "police":             'amenity=police',
    "ambulance_station":  'amenity=ambulance_station',
    "pharmacy":           'amenity=pharmacy',
    "school":             'amenity=school',
    "college":            'amenity=college',
}

ALL_AMENITIES = list(AMENITY_MAP.values())


def fetch_facilities_from_overpass(city: str = "Bangalore", amenity_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Fetch facilities from OpenStreetMap via Overpass API.
    amenity_types: list of keys from AMENITY_MAP, or None for all.
    Returns a GeoJSON FeatureCollection.
    """
    cache_key = f"{city}::{','.join(amenity_types or ['all'])}"
    now = time.time()

    if cache_key in _cache and (now - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
        return _cache[cache_key]

    if amenity_types is None:
        amenity_types = list(AMENITY_MAP.keys())

    # Build Overpass QL query
    amenity_filters = "\n  ".join(
        f'nwr["{f.split("=")[0]}"="{f.split("=")[1]}"](area.city);'
        for key in amenity_types
        for f in [AMENITY_MAP.get(key, f'amenity={key}')]
    )

    query = f"""
[out:json][timeout:60];
area[name="{city}"]->.city;
(
  {amenity_filters}
);
out center tags;
"""

    raw = _fetch_overpass(query)
    if not raw:
        # Fall back to static data
        return get_facilities_geojson()

    all_features: List[Dict] = []
    for key in amenity_types:
        tag_val = AMENITY_MAP.get(key, key).split("=")[1]
        for el in raw.get("elements", []):
            tags = el.get("tags", {})
            if tags.get("amenity") == tag_val or tags.get(AMENITY_MAP.get(key, "").split("=")[0]) == tag_val:
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lon = el.get("lon") or el.get("center", {}).get("lon")
                if not lat or not lon:
                    continue
                name = (tags.get("name") or tags.get("name:en") or
                        f"Unnamed {key.replace('_', ' ').title()}")
                all_features.append({
                    "type": "Feature",
                    "properties": {
                        "id": str(el.get("id", "")),
                        "name": name,
                        "facility_type": key,
                        "amenity": tags.get("amenity", key),
                        "phone": tags.get("phone") or tags.get("contact:phone"),
                        "operator": tags.get("operator"),
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                })

    result = {"type": "FeatureCollection", "features": all_features, "source": "OpenStreetMap/Overpass"}
    _cache[cache_key] = result
    _cache_ts[cache_key] = now
    return result


# ---- Static fallback (used when Overpass is down) ----
from .coverage_engine import FACILITIES


def get_facilities_geojson(facility_type: str = None) -> Dict[str, Any]:
    """Static GeoJSON of known Bangalore facilities (fallback)."""
    features = []
    for f in FACILITIES:
        if facility_type and f["type"] != facility_type:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "id": f["id"],
                "name": f["name"],
                "facility_type": f["type"],
                "amenity": f["type"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [f["lng"], f["lat"]],
            },
        })
    return {"type": "FeatureCollection", "features": features, "source": "static"}


def get_city_zones() -> List[Dict[str, Any]]:
    return [
        {"name": "City Centre",     "lat": 12.9716, "lng": 77.5946},
        {"name": "Indiranagar",     "lat": 12.9784, "lng": 77.6408},
        {"name": "Koramangala",     "lat": 12.9354, "lng": 77.6231},
        {"name": "HSR Layout",      "lat": 12.9116, "lng": 77.6389},
        {"name": "Whitefield",      "lat": 12.9698, "lng": 77.7499},
        {"name": "Electronic City", "lat": 12.8391, "lng": 77.6781},
        {"name": "Hebbal",          "lat": 13.0354, "lng": 77.5967},
        {"name": "Yeshwanthpur",    "lat": 13.0262, "lng": 77.5519},
    ]
