from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReportCreate(BaseModel):
    category: str = Field(..., description="E.g., pothole, drainage, litter, accident")
    description: Optional[str] = None
    lat: float
    lng: float

class ReportResponse(ReportCreate):
    id: int
    created_at: datetime
    status: str = "OPEN"

    class Config:
        from_attributes = True

# We can also add SQLAlchemy models here when we link to DB
