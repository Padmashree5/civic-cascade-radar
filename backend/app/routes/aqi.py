import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/aqi", tags=["aqi"])

# Bengaluru bounding box
_BOUNDS = "12.7,77.4,13.2,77.9"

def _aqi_category(aqi: int) -> tuple[str, str]:
    """Returns (category label, hex color) for a given AQI value."""
    if aqi <= 50:   return "Good",                           "#00e400"
    if aqi <= 100:  return "Moderate",                       "#ffde33"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups", "#ff9933"
    if aqi <= 200:  return "Unhealthy",                      "#cc0033"
    if aqi <= 300:  return "Very Unhealthy",                 "#660099"
    return              "Hazardous",                         "#7e0023"


@router.get("/stations")
async def get_aqi_stations():
    token = os.getenv("AQICN_TOKEN", "demo")
    url = f"https://api.waqi.info/map/bounds/?latlng={_BOUNDS}&token={token}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AQICN fetch failed: {e}")

    if data.get("status") != "ok":
        raise HTTPException(status_code=502, detail=f"AQICN error: {data.get('data', 'unknown')}")

    points = []
    for s in data.get("data", []):
        try:
            aqi_raw = s.get("aqi", "-")
            if aqi_raw == "-" or aqi_raw is None:
                continue
            aqi = int(aqi_raw)
            lat = float(s["lat"])
            lng = float(s["lon"])
            name = s.get("station", {}).get("name", "Unknown Station")
            updated = s.get("station", {}).get("time", "")
            category, color = _aqi_category(aqi)
            intensity = round(min(1.0, aqi / 300.0), 3)
            label = (
                f'<div style="font-family:sans-serif;font-size:12px">'
                f'<b>{name}</b><br/>'
                f'AQI: <b style="color:{color}">{aqi}</b>'
                f' &mdash; <span style="color:{color}">{category}</span><br/>'
                f'<small style="color:#888">Updated: {updated}</small>'
                f'</div>'
            )
            points.append({"lat": lat, "lng": lng, "intensity": intensity, "label": label, "color": color})
        except (ValueError, KeyError, TypeError):
            continue

    return points
