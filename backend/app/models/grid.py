from typing import Optional
from pydantic import BaseModel

class GridPoint(BaseModel):
    lat: float
    lng: float
    intensity: float  # 0.0 to 1.0 representing risk/density
    label: Optional[str] = None
