"""
traffic.py - Routing via OSRM public API (replaces static Dijkstra graph).
Falls back to local Dijkstra if OSRM is unreachable.
"""
import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/traffic", tags=["traffic"])

_OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"


async def _osrm_route(start_lat, start_lng, end_lat, end_lng) -> dict | None:
    url = f"{_OSRM_BASE}/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=false"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
            data = resp.json()
        if data.get("code") != "Ok":
            return None
        route = data["routes"][0]
        coords = route["geometry"]["coordinates"]
        path = [[c[1], c[0]] for c in coords]  # GeoJSON is [lng,lat] → convert to [lat,lng]
        duration_sec = route["duration"]
        distance_m = route["distance"]
        eta_min = round(duration_sec / 60, 1)
        dist_km = round(distance_m / 1000, 2)
        return {
            "eta_minutes": eta_min,
            "distance_km": dist_km,
            "delay_minutes": 0,
            "status": "OSRM",
            "path": path,
            "source": "osrm",
        }
    except Exception:
        return None


@router.get("/route")
async def get_route(
    start_lat: float = Query(...),
    start_lng: float = Query(...),
    end_lat: float = Query(...),
    end_lng: float = Query(...),
):
    """
    Compute a driving route. Uses OSRM (real road network) with Dijkstra fallback.
    """
    result = await _osrm_route(start_lat, start_lng, end_lat, end_lng)
    if result:
        return result
    # Fallback to local Dijkstra
    from ..services.routing_service import compute_route
    fallback = compute_route(start_lat, start_lng, end_lat, end_lng)
    fallback["source"] = "dijkstra-fallback"
    return fallback
