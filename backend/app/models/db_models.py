"""
db_models.py - SQLAlchemy ORM models for persistent storage.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Report(Base):
    __tablename__ = "reports"

    id          = Column(Integer, primary_key=True, index=True)
    category    = Column(String(64), index=True, nullable=False)
    description = Column(Text, nullable=True)
    lat         = Column(Float, nullable=False)
    lng         = Column(Float, nullable=False)
    status      = Column(String(32), default="OPEN", nullable=False)
    photo_path  = Column(String(512), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    upvotes     = relationship("Upvote", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reports_category_status", "category", "status"),
        Index("ix_reports_created_at", "created_at"),
    )


class Upvote(Base):
    __tablename__ = "upvotes"

    id          = Column(Integer, primary_key=True)
    report_id   = Column(Integer, ForeignKey("reports.id"), nullable=False)
    ip_hash     = Column(String(64), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    report      = relationship("Report", back_populates="upvotes")

    __table_args__ = (
        Index("ix_upvotes_report_ip", "report_id", "ip_hash", unique=True),
    )
