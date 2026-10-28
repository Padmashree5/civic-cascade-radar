"""
analytics.py - ML-lite analytics endpoints: predictions, hotspots, anomalies.
"""
from fastapi import APIRouter, Query, Depends
from ..services.analytics_service import (
    compute_pothole_risk,
    compute_crime_hotspots,
    compute_flood_risk,
    detect_anomalies,
    optimize_dispatch,
    get_ward_summary,
    WARDS,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pothole-risk")
def pothole_risk(rainfall_mm: float = Query(0.0, description="Current rainfall in mm")):
    """Predicted pothole risk score per ward."""
    return {"wards": compute_pothole_risk(rainfall_mm)}


@router.get("/crime-hotspot")
def crime_hotspot(hour: int = Query(None, ge=0, le=23)):
    """Predicted crime hotspot risk per ward, optionally at a given hour."""
    return {"wards": compute_crime_hotspots(hour)}


@router.get("/flood-risk")
def flood_risk(rainfall_mm: float = Query(0.0)):
    """Per-ward flood risk combining terrain, drainage, and live rainfall."""
    return {"wards": compute_flood_risk(rainfall_mm)}


@router.get("/anomalies")
def get_anomalies(window_minutes: int = Query(60, ge=5, le=1440)):
    """
    Detect wards with abnormal citizen report spikes in the last N minutes.
    Reads from the SQLite DB.
    """
    from ..database import SessionLocal
    from ..models.db_models import Report
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        rows = db.query(Report).filter(Report.created_at >= cutoff).all()
        report_dicts = [
            {
                "lat": r.lat,
                "lng": r.lng,
                "category": r.category,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()

    return {"anomalies": detect_anomalies(report_dicts, window_minutes)}


@router.post("/emergency-dispatch")
def emergency_dispatch_optimizer(
    incident_lat: float = Query(...),
    incident_lng: float = Query(...),
    incident_type: str = Query("crime"),
):
    """Optimally assign nearest available units to an incident."""
    return optimize_dispatch(incident_lat, incident_lng, incident_type)


@router.get("/ward-summary")
def ward_summary(
    ward: str = Query(..., description="Ward name, e.g. 'Koramangala'"),
    rainfall_mm: float = Query(0.0),
):
    """Full analytics snapshot for a single ward (used by map drill-down)."""
    result = get_ward_summary(ward, rainfall_mm)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Ward '{ward}' not found")
    return result


@router.get("/wards")
def list_wards():
    """List all known wards with lat/lng."""
    return {"wards": WARDS}
