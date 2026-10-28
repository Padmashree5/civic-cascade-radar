from fastapi import APIRouter
from ..services.risk_engine import simulate_flood

router = APIRouter(prefix="/flood", tags=["flood"])

@router.get("/risk")
def get_flood_risk(rainfall: float = 0.0):
    """
    Flood simulation endpoint. Returns a GeoJSON FeatureCollection
    of zones with their risk levels based on rainfall amount.
    """
    return simulate_flood(rainfall)
