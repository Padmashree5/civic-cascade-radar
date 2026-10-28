"""Civic Cascade Radar API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.cascade_service import compute_cascade

router = APIRouter(prefix="/cascade", tags=["cascade"])


@router.get("/radar")
async def get_cascade_radar(
    rainfall: float | None = Query(
        default=None, ge=0, le=500,
        description="Optional what-if rainfall scenario in millimetres. Omit to use nearest station data.",
    ),
    top_n: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return ranked potential waterlogging hotspots with score breakdowns."""
    return await compute_cascade(db=db, rainfall_override=rainfall, top_n=top_n)
