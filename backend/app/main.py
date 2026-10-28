from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import asyncio

load_dotenv()

app = FastAPI(title="Smart City Intelligence API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded photos
_UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
_UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def startup():
    from .database import init_db
    init_db()


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Smart City Backend v2.0 running."}


# ── Routers ───────────────────────────────────────────────────────────────────
from .routes import flood, traffic, emergency, heatmap, insights, reports, datasets, kml, aqi
from .routes import auth, weather, analytics, layers, cascade

app.include_router(auth.router)
app.include_router(flood.router)
app.include_router(traffic.router)
app.include_router(emergency.router)
app.include_router(heatmap.router)
app.include_router(insights.router)
app.include_router(reports.router)
app.include_router(datasets.router)
app.include_router(kml.router)
app.include_router(aqi.router)
app.include_router(weather.router)
app.include_router(analytics.router)
app.include_router(layers.router)
app.include_router(cascade.router)


# ── WebSocket: live citizen report feed ──────────────────────────────────────

class _ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws) if hasattr(self.active, "discard") else None
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = _ConnectionManager()


@app.websocket("/ws/reports")
async def websocket_reports(websocket: WebSocket):
    """
    Real-time feed of citizen reports.
    Clients receive a JSON message whenever a new report is submitted.
    Also broadcasts anomaly alerts every 30 seconds if spikes are detected.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; actual broadcasts come from report creation
            await asyncio.sleep(30)
            # Periodic anomaly check
            try:
                from .services.analytics_service import detect_anomalies
                from .database import SessionLocal
                from .models.db_models import Report
                from datetime import datetime, timedelta

                db = SessionLocal()
                cutoff = datetime.utcnow() - timedelta(minutes=60)
                rows = db.query(Report).filter(Report.created_at >= cutoff).all()
                db.close()

                report_dicts = [
                    {"lat": r.lat, "lng": r.lng, "category": r.category, "created_at": r.created_at.isoformat()}
                    for r in rows
                ]
                anomalies = detect_anomalies(report_dicts)
                if anomalies:
                    await websocket.send_text(json.dumps({"type": "anomaly", "data": anomalies}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def broadcast_new_report(report: dict):
    """Called after a report is created to push it to all WS clients."""
    await ws_manager.broadcast({"type": "new_report", "data": report})
