"""
weather.py - Live weather endpoints via Open-Meteo (free, no API key).
"""
from fastapi import APIRouter, Query
from ..services.weather_service import (
    get_all_stations_weather,
    fetch_station_weather,
    get_rainfall_heatmap,
    WEATHER_STATIONS,
)

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/stations")
async def get_weather_stations():
    """Live weather for all Bengaluru monitoring stations."""
    return await get_all_stations_weather()


@router.get("/station")
async def get_single_station(
    lat: float = Query(...),
    lng: float = Query(...),
    name: str = Query("Custom Location"),
):
    """Live weather for a specific lat/lng."""
    return await fetch_station_weather(lat, lng, name)


@router.get("/rainfall")
async def get_rainfall_heatmap_endpoint():
    """Rainfall intensity as heatmap points (for /heatmap/rainfall layer)."""
    return await get_rainfall_heatmap()
