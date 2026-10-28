from fastapi import APIRouter
from typing import List
from ..models.grid import GridPoint
from ..services.heatmap_engine import get_layer
from ..database import SessionLocal
from ..models.db_models import Report

router = APIRouter(prefix="/heatmap", tags=["heatmap"])

_CITIZEN_CATEGORIES = {"garbage_dump", "pothole", "drainage"}


def _get_citizen_reports(category: str) -> list[dict]:
    """Pull matching citizen reports from SQLite to augment heatmap layers."""
    db = SessionLocal()
    try:
        rows = db.query(Report).filter(Report.category == category).all()
        return [{"lat": r.lat, "lng": r.lng} for r in rows]
    finally:
        db.close()


@router.get("/{layer_id}", response_model=List[GridPoint])
def get_heatmap_layer(layer_id: str):
    """
    Returns heatmap intensity points for a given layer.
    Citizen reports are merged into pothole, garbage_dump, and drainage layers.
    """
    extra = _get_citizen_reports(layer_id) if layer_id in _CITIZEN_CATEGORIES else []
    points = get_layer(layer_id, extra_points=extra)
    return [
        GridPoint(lat=p["lat"], lng=p["lng"], intensity=p["intensity"], label=p.get("label"))
        for p in points
    ]
