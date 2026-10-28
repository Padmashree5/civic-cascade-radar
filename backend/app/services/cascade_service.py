"""
Civic Cascade Radar: transparent preliminary hotspot ranking.

This service combines flood-prone locations from a bundled KML dataset with
rainfall, nearby garbage-dump points, citizen reports, and clearly labelled
expert-prior data from risk_engine.ZONES.

Important: this is a heuristic demo score, not a validated flood forecast.
"""
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ..models.db_models import Report
from .heatmap_engine import _load_garbage_csv
from .kml_service import parse_kml
from .risk_engine import ZONES
from .weather_service import get_all_stations_weather

_DATASETS = Path(__file__).resolve().parents[3] / "datasets"
_FLOOD_KML = _DATASETS / "flood_prone_location.kml"
_GROUNDWATER_KML = _DATASETS / "ground_potential_map.kml"

# Weights sum to 1.0. These are product-design choices, not trained weights.
W_RAINFALL = 0.30
W_LOCAL_PRESSURE = 0.25
W_ZONE_PRIOR = 0.25
W_CITIZEN_REPORTS = 0.20

_flood_points_cache: list[dict[str, Any]] | None = None
_garbage_points_cache: list[dict[str, Any]] | None = None
_groundwater_features_cache: list[dict[str, Any]] | None = None
_groundwater_index_cache: list[tuple[dict[str, Any], list[list[float]], tuple[float, float, float, float]]] | None = None


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres (Haversine)."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def _load_flood_points() -> list[dict[str, Any]]:
    """Load actual point placemarks from the bundled flood-prone KML."""
    global _flood_points_cache
    if _flood_points_cache is not None:
        return _flood_points_cache

    result = []
    for feature in parse_kml(_FLOOD_KML, max_features=5000):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue
        try:
            lng, lat = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        result.append({
            "name": str(feature.get("properties", {}).get("name") or "Flood-prone location").strip(),
            "lat": lat,
            "lng": lng,
            "source": "flood_prone_location.kml",
        })
    _flood_points_cache = result
    return result


def _load_garbage_points() -> list[dict[str, Any]]:
    """Load garbage point data through the existing CSV loader."""
    global _garbage_points_cache
    if _garbage_points_cache is None:
        try:
            _garbage_points_cache = [
                p for p in _load_garbage_csv()
                if _valid_coordinates(p.get("lat"), p.get("lng"))
            ]
        except (OSError, ValueError, KeyError):
            _garbage_points_cache = []
    return _garbage_points_cache


def _valid_coordinates(lat: Any, lng: Any) -> bool:
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180
    except (TypeError, ValueError):
        return False


def _load_groundwater_features() -> list[dict[str, Any]]:
    """Load polygons once. Used as context only, not as a soil-infiltration claim."""
    global _groundwater_features_cache
    if _groundwater_features_cache is None:
        _groundwater_features_cache = parse_kml(_GROUNDWATER_KML, max_features=5000)
    return _groundwater_features_cache


def _point_in_ring(lng: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon check for a KML polygon ring."""
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)):
            crossing_lng = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
            if lng < crossing_lng:
                inside = not inside
        j = i
    return inside


def _groundwater_context(lat: float, lng: float) -> str | None:
    """Return the groundwater-potential label for a containing polygon if found."""
    global _groundwater_index_cache
    if _groundwater_index_cache is None:
        indexed = []
        for feature in _load_groundwater_features():
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Polygon":
                continue
            rings = geometry.get("coordinates") or []
            if not rings or not rings[0]:
                continue
            outer = rings[0]
            valid = [p for p in outer if len(p) >= 2]
            if not valid:
                continue
            lons = [p[0] for p in valid]
            lats = [p[1] for p in valid]
            indexed.append((feature, outer, (min(lons), min(lats), max(lons), max(lats))))
        _groundwater_index_cache = indexed

    for feature, outer, bounds in _groundwater_index_cache:
        min_lng, min_lat, max_lng, max_lat = bounds
        if lng < min_lng or lng > max_lng or lat < min_lat or lat > max_lat:
            continue
        if _point_in_ring(lng, lat, outer):
            props = feature.get("properties") or {}
            value = props.get("GW_PROS")
            return str(value).strip() if value else None
    return None


def _nearest_zone(lat: float, lng: float) -> dict[str, Any]:
    """Nearest hand-coded zone; these values are expert priors, not live sensors."""
    return min(ZONES, key=lambda zone: _distance_m(lat, lng, zone["lat"], zone["lng"]))


def _rainfall_norm(mm: float) -> float:
    """Normalize rainfall override/current precipitation to a bounded demo signal."""
    return max(0.0, min(1.0, float(mm) / 50.0))


def _zone_prior(zone: dict[str, Any]) -> float:
    """Combine existing zone history/drain/elevation fields as a labelled prior."""
    history = {"HIGH": 1.0, "MEDIUM": 0.55, "LOW": 0.20}.get(
        str(zone.get("historical_risk", "LOW")).upper(), 0.20
    )
    drain = max(0.0, min(1.0, 1.0 - float(zone.get("drain", 5)) / 10.0))
    elevations = [float(item["elev"]) for item in ZONES if "elev" in item]
    low_elevation = 1.0 - (
        (float(zone.get("elev", max(elevations))) - min(elevations))
        / (max(elevations) - min(elevations) or 1.0)
    )
    return max(0.0, min(1.0, 0.60 * history + 0.25 * drain + 0.15 * low_elevation))


async def compute_cascade(
    db,
    rainfall_override: float | None = None,
    top_n: int = 25,
    radius_m: float = 500.0,
    report_hours: int = 48,
) -> dict[str, Any]:
    """
    Rank bundled flood-prone points using available signals.

    `rainfall_override` is an explicit what-if scenario in mm. If omitted,
    nearest station precipitation is used; synthetic weather fallbacks remain
    marked as synthetic by weather_service.
    """
    flood_points = _load_flood_points()
    garbage_points = _load_garbage_points()
    stations = await get_all_stations_weather()

    cutoff = datetime.utcnow() - timedelta(hours=report_hours)
    try:
        reports = (
            db.query(Report)
            .filter(Report.created_at >= cutoff)
            .filter(Report.category.in_(["drainage", "garbage_dump", "pothole"]))
            .all()
        )
    except Exception as exc:
        # Do not silently treat a database failure as zero citizen reports: that
        # would produce an apparently complete but misleading risk score.
        raise HTTPException(
            status_code=503,
            detail="Citizen-report data is temporarily unavailable; radar scores could not be computed reliably.",
        ) from exc

    hotspots = []
    for point in flood_points:
        lat, lng = point["lat"], point["lng"]
        zone = _nearest_zone(lat, lng)
        nearest_station = min(
            stations,
            key=lambda station: _distance_m(lat, lng, station["lat"], station["lng"]),
        ) if stations else None

        if rainfall_override is not None:
            rain_mm = max(0.0, min(500.0, float(rainfall_override)))
            rain_source = "what-if override"
            weather_source = "user scenario"
        elif nearest_station:
            rain_mm = max(0.0, float(nearest_station.get("precipitation_mm", 0.0)))
            rain_source = str(nearest_station.get("source", "unknown"))
            weather_source = rain_source
        else:
            rain_mm = 0.0
            rain_source = "unavailable"
            weather_source = "unavailable"

        nearby_garbage = sum(
            1 for item in garbage_points
            if _distance_m(lat, lng, float(item["lat"]), float(item["lng"])) <= radius_m
        )
        nearby_reports = [
            report for report in reports
            if _valid_coordinates(report.lat, report.lng)
            and _distance_m(lat, lng, float(report.lat), float(report.lng)) <= radius_m
        ]

        # A capped density curve avoids one cluster overwhelming every other signal.
        garbage_signal = min(1.0, nearby_garbage / 8.0)
        citizen_signal = min(1.0, len(nearby_reports) / 5.0)
        rain_signal = _rainfall_norm(rain_mm)
        zone_signal = _zone_prior(zone)
        score = (
            W_RAINFALL * rain_signal
            + W_LOCAL_PRESSURE * garbage_signal
            + W_ZONE_PRIOR * zone_signal
            + W_CITIZEN_REPORTS * citizen_signal
        )
        score = round(max(0.0, min(1.0, score)), 3)
        severity = "CRITICAL" if score >= 0.75 else "HIGH" if score >= 0.55 else "MEDIUM" if score >= 0.35 else "LOW"

        try:
            groundwater = _groundwater_context(lat, lng)
        except (OSError, ValueError, TypeError):
            groundwater = None

        hotspots.append({
            "name": point["name"],
            "lat": lat,
            "lng": lng,
            "score": score,
            "severity": severity,
            "breakdown": {
                "rainfall": round(rain_signal, 3),
                "nearby_garbage": round(garbage_signal, 3),
                "expert_zone_prior": round(zone_signal, 3),
                "citizen_reports": round(citizen_signal, 3),
            },
            "nearby": {
                "garbage_dumps_within_500m": nearby_garbage,
                "citizen_reports_within_500m": len(nearby_reports),
            },
            "context": {
                "nearest_expert_zone": zone["name"],
                "zone_prior_source": "risk_engine.ZONES (hand-coded expert prior)",
                "groundwater_potential": groundwater,
                "groundwater_source": "ground_potential_map.kml" if groundwater else None,
                "rainfall_mm": round(rain_mm, 2),
                "rainfall_source": rain_source,
                "nearest_weather_station": nearest_station.get("name") if nearest_station else None,
                "weather_source": weather_source,
                "historical_location_source": point["source"],
                "garbage_source": "garbage_dump_banglore.csv",
            },
        })

    hotspots.sort(key=lambda item: item["score"], reverse=True)
    top_n = max(1, min(int(top_n), 100))
    selected = hotspots[:top_n]
    critical = sum(1 for item in hotspots if item["severity"] == "CRITICAL")
    high = sum(1 for item in hotspots if item["severity"] == "HIGH")

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "score_type": "heuristic demo score; not a validated flood prediction",
        "rainfall_mode": "what-if override" if rainfall_override is not None else "nearest weather station",
        "counts": {
            "flood_prone_dataset_points": len(flood_points),
            "garbage_dataset_points": len(garbage_points),
            "hotspots_returned": len(selected),
            "high": high,
            "critical": critical,
        },
        "weights": {
            "rainfall": W_RAINFALL,
            "nearby_garbage": W_LOCAL_PRESSURE,
            "expert_zone_prior": W_ZONE_PRIOR,
            "citizen_reports": W_CITIZEN_REPORTS,
        },
        "summary": (
            f"Ranked {len(flood_points)} flood-prone dataset locations. "
            f"{critical} scored CRITICAL and {high} scored HIGH using the current heuristic."
        ),
        "hotspots": selected,
        "data_notes": [
            "Flood-prone locations and garbage dumps come from bundled datasets; their provenance has not been independently verified here.",
            "Rainfall uses Open-Meteo station data when available; the existing weather service may fall back to synthetic values, which are labelled in each result.",
            "Drainage, elevation, and historical zone fields are hand-coded expert priors, not live sensors.",
            "Groundwater potential is returned as context only; it is not treated as a measured soil infiltration or drainage-capacity value.",
            "The score is a transparent demonstration heuristic and must not be presented as a guaranteed flood prediction.",
        ],
    }
