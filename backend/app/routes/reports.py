"""
reports.py - Citizen report CRUD with SQLite persistence, upvoting, and photo upload.
"""
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Report, Upvote
from ..models.report import ReportCreate, ReportResponse

router = APIRouter(prefix="/reports", tags=["reports"])

UPLOADS_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _to_response(r: Report) -> dict:
    return {
        "id": r.id,
        "category": r.category,
        "description": r.description,
        "lat": r.lat,
        "lng": r.lng,
        "status": r.status,
        "photo_path": r.photo_path,
        "created_at": r.created_at.isoformat(),
        "upvotes": len(r.upvotes) if r.upvotes else 0,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    db_report = Report(
        category=report.category,
        description=report.description,
        lat=report.lat,
        lng=report.lng,
        status="OPEN",
        created_at=datetime.utcnow(),
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return _to_response(db_report)


@router.get("/")
def get_reports(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Report)
    if category:
        q = q.filter(Report.category == category)
    if status:
        q = q.filter(Report.status == status)
    rows = q.order_by(Report.created_at.desc()).limit(limit).all()
    return [_to_response(r) for r in rows]


@router.get("/stats/summary")
def report_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(func.count(Report.id)).scalar()
    by_category = dict(
        db.query(Report.category, func.count(Report.id)).group_by(Report.category).all()
    )
    by_status = dict(
        db.query(Report.status, func.count(Report.id)).group_by(Report.status).all()
    )
    return {"total": total, "by_category": by_category, "by_status": by_status}


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_response(r)


@router.patch("/{report_id}/status")
def update_status(
    report_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    r.status = status
    db.commit()
    return {"id": report_id, "status": status}


# ── Photo Upload ──────────────────────────────────────────────────────────────

@router.post("/with-photo")
async def create_report_with_photo(
    category: str = Form(...),
    description: Optional[str] = Form(None),
    lat: float = Form(...),
    lng: float = Form(...),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    photo_path = None
    if photo and photo.filename:
        ext = Path(photo.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
        content = await photo.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 5 MB)")
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
        (UPLOADS_DIR / filename).write_bytes(content)
        photo_path = f"/uploads/{filename}"

    db_report = Report(
        category=category,
        description=description,
        lat=lat,
        lng=lng,
        status="OPEN",
        photo_path=photo_path,
        created_at=datetime.utcnow(),
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return _to_response(db_report)


# ── Upvoting ──────────────────────────────────────────────────────────────────

@router.post("/{report_id}/upvote")
def upvote_report(report_id: int, request: Request, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    raw_ip = request.client.host if request.client else "anon"
    ip_hash = hashlib.sha256(raw_ip.encode()).hexdigest()[:32]

    existing = db.query(Upvote).filter(
        Upvote.report_id == report_id, Upvote.ip_hash == ip_hash
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already upvoted")

    db.add(Upvote(report_id=report_id, ip_hash=ip_hash))
    db.commit()
    count = db.query(Upvote).filter(Upvote.report_id == report_id).count()
    return {"report_id": report_id, "upvotes": count}
