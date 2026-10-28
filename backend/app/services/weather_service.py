"""
weather_service.py - Live weather via Open-Meteo (free, no key required).
Fetches current conditions + 7-day forecast for Bengaluru weather stations.
Falls back to synthetic data if the API is unreachable.
"""
import httpx
import random
from pathlib import Path
from .cache_service import weather_cache

# Known Bengaluru weather station locations (lat, lng, name)
WEATHER_STATIONS = [
    (12.9716, 77.5946, "Majestic / City Centre"),
    (12.9352, 77.6244, "Whitefield"),
    (13.0067, 77.5963, "Hebbal"),
    (12.8900, 77.6400, "Koramangala"),
    (12.9580, 77.6060, "Indiranagar"),
    (12.9007, 77.5996, "Jayanagar"),
    (12.8340, 77.6602, "Electronic City"),
    (13.0360, 77.5970, "Yelahanka"),
    (12.9780, 77.6408, "Marathahalli"),
    (12.9200, 77.5800, "Basavanagudi"),
    (12.9600, 77.5700, "Rajajinagar"),
    (12.8700, 77.6100, "BTM Layout"),
]

_OM_BASE = "https://api.open-meteo.com/v1/forecast"
_OM_PARAMS = (
    "current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,weather_code,wind_speed_10m,wind_direction_10m&"
    "hourly=precipitation_probability,precipitation&"
    "daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code&"
    "timezone=Asia%2FKolkata&forecast_days=7"
)

_WMO_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}


def _wmo_desc(code: int) -> str:
    return _WMO_DESCRIPTIONS.get(code, f"Code {code}")


def _synthetic_station(lat: float, lng: float, name: str, rng: random.Random) -> dict:
    """Fallback synthetic weather when API is unavailable."""
    temp = round(rng.uniform(22.0, 34.0), 1)
    precip = round(rng.uniform(0.0, 8.0), 2)
    return {
        "name": name,
        "lat": lat,
        "lng": lng,
        "temperature_c": temp,
        "feels_like_c": round(temp - rng.uniform(1, 3), 1),
        "humidity_pct": round(rng.uniform(55, 90), 1),
        "precipitation_mm": precip,
        "wind_speed_kmh": round(rng.uniform(5, 30), 1),
        "wind_dir_deg": rng.randint(0, 359),
        "condition": "Partly cloudy",
        "condition_code": 2,
        "intensity": round(min(1.0, precip / 10.0 + temp / 40.0), 3),
        "source": "synthetic",
    }


async def fetch_station_weather(lat: float, lng: float, name: str) -> dict:
    key = f"weather_{lat:.3f}_{lng:.3f}"
    cached = weather_cache.get(key)
    if cached is not None:
        return cached

    url = f"{_OM_BASE}?latitude={lat}&longitude={lng}&{_OM_PARAMS}"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            d = resp.json()
        cur = d.get("current", {})
        temp = cur.get("temperature_2m", 28.0)
        precip = cur.get("precipitation", 0.0)
        humidity = cur.get("relative_humidity_2m", 70)
        wind_speed = cur.get("wind_speed_10m", 10)
        code = cur.get("weather_code", 0)

        result = {
            "name": name,
            "lat": lat,
            "lng": lng,
            "temperature_c": round(temp, 1),
            "feels_like_c": round(cur.get("apparent_temperature", temp), 1),
            "humidity_pct": round(humidity, 1),
            "precipitation_mm": round(precip, 2),
            "wind_speed_kmh": round(wind_speed, 1),
            "wind_dir_deg": cur.get("wind_direction_10m", 180),
            "condition": _wmo_desc(code),
            "condition_code": code,
            "intensity": round(min(1.0, precip / 10.0 + temp / 45.0), 3),
            "daily": [
                {
                    "date": d["daily"]["time"][i],
                    "max_c": d["daily"]["temperature_2m_max"][i],
                    "min_c": d["daily"]["temperature_2m_min"][i],
                    "precip_mm": d["daily"]["precipitation_sum"][i],
                    "condition": _wmo_desc(d["daily"]["weather_code"][i]),
                }
                for i in range(min(7, len(d.get("daily", {}).get("time", []))))
            ],
            "source": "open-meteo",
        }
    except Exception:
        rng = random.Random(int(lat * 1000 + lng * 100))
        result = _synthetic_station(lat, lng, name, rng)

    weather_cache.set(key, result)
    return result


async def get_all_stations_weather() -> list[dict]:
    """Fetch weather for all Bengaluru stations concurrently."""
    import asyncio
    tasks = [
        fetch_station_weather(lat, lng, name)
        for lat, lng, name in WEATHER_STATIONS
    ]
    return await asyncio.gather(*tasks)


async def get_rainfall_heatmap() -> list[dict]:
    """Derive rainfall intensity heatmap from all station live data."""
    stations = await get_all_stations_weather()
    return [
        {
            "lat": s["lat"],
            "lng": s["lng"],
            "intensity": round(min(1.0, s["precipitation_mm"] / 15.0), 3),
            "label": (
                f'<b>{s["name"]}</b><br/>'
                f'Rain: {s["precipitation_mm"]} mm<br/>'
                f'Condition: {s["condition"]}<br/>'
                f'Temp: {s["temperature_c"]}°C'
            ),
        }
        for s in stations
    ]
