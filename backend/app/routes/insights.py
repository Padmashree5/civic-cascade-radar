"""
insights.py route - Provides city insights, optionally powered by Groq LLM.

GET /insights/          → Static template insights (no API key needed)
GET /insights/ai        → Groq LLM-powered analysis (needs GROQ_API_KEY in .env)
GET /insights/summary   → Data summary stats fed to Groq
"""
from fastapi import APIRouter
from pydantic import BaseModel
from ..services.data_service import load_potholes, generate_crime_data, generate_drainage_data
from ..services.groq_service import generate_city_insights, chat_about_city


class ChatRequest(BaseModel):
    question: str

router = APIRouter(prefix="/insights", tags=["insights"])


def _build_summary() -> dict:
    """Aggregate statistics from all datasets to pass to Groq."""
    potholes = load_potholes()
    crimes = generate_crime_data()
    drains = generate_drainage_data()

    severity_count: dict[str, int] = {}
    for p in potholes:
        sev = p.get("severity", "Unknown")
        severity_count[sev] = severity_count.get(sev, 0) + 1

    crime_zones: dict[str, int] = {}
    for c in crimes:
        z = c["zone"]
        crime_zones[z] = crime_zones.get(z, 0) + 1

    drain_zones: dict[str, int] = {}
    for d in drains:
        z = d["zone"]
        drain_zones[z] = drain_zones.get(z, 0) + 1

    grid: dict[str, int] = {}
    for p in potholes:
        key = f"({round(p['lat'] * 10) / 10}, {round(p['lng'] * 10) / 10})"
        grid[key] = grid.get(key, 0) + 1

    top_pothole_grids = sorted(grid.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_potholes": len(potholes),
        "pothole_severity": severity_count,
        "top_pothole_hotspots": [{"grid": k, "count": v} for k, v in top_pothole_grids],
        "total_crime_incidents": len(crimes),
        "crime_by_zone": crime_zones,
        "top_crime_zone": max(crime_zones, key=crime_zones.get) if crime_zones else None,
        "total_drainage_issues": len(drains),
        "drainage_by_zone": drain_zones,
        "top_drainage_zone": max(drain_zones, key=drain_zones.get) if drain_zones else None,
        "city": "Bengaluru, India",
        "analysis_date": "2026-03-31"
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    """Answer a free-form question about Bengaluru using Groq AI."""
    answer = await chat_about_city(req.question)
    return {"answer": answer}


@router.get("/summary")
def get_data_summary():
    """Return the raw data summary used for AI analysis."""
    return _build_summary()


@router.get("/ai")
async def get_ai_insights():
    """
    Call Groq LLM with city data summary and return structured insights.
    Requires GROQ_API_KEY to be set in backend/.env
    """
    summary = _build_summary()
    result = await generate_city_insights(summary)
    return result


@router.get("/")
def get_static_insights():
    """
    Return pre-computed static insights derived from real data.
    """
    summary = _build_summary()
    top_crime_zone = summary.get("top_crime_zone", "Majestic")
    top_drain_zone = summary.get("top_drainage_zone", "Majestic")
    total_ph = summary["total_potholes"]
    critical = summary["pothole_severity"].get("Critical", 0)

    return {
        "title": "CITY WEAKNESS REPORT – Bengaluru",
        "top_weaknesses": [
            {
                "rank": 1,
                "zone": "South Bengaluru (Jayanagar–Jayadeva Corridor)",
                "issue": f"High pothole density — {critical} Critical potholes from {total_ph} total detected.",
                "severity": "CRITICAL",
                "recommendation": "Emergency road resurfacing required before monsoon. Deploy BBMP rapid-response teams."
            },
            {
                "rank": 2,
                "zone": top_crime_zone,
                "issue": f"Highest crime concentration with {summary['crime_by_zone'].get(top_crime_zone, 'N/A')} incidents reported.",
                "severity": "HIGH",
                "recommendation": "Increase night police patrolling frequency and deploy CCTV coverage."
            },
            {
                "rank": 3,
                "zone": top_drain_zone,
                "issue": "Severe drainage blockages likely to cause flash-flooding during monsoon.",
                "severity": "HIGH",
                "recommendation": "Pre-monsoon drainage clearing campaign required. Prioritize blocked drains near low-lying areas."
            },
            {
                "rank": 4,
                "zone": "North Zone (Yelahanka–Hebbal)",
                "issue": "Emergency response coverage gap — fire station distance exceeds 5km in several wards.",
                "severity": "HIGH",
                "recommendation": "Establish a temporary fire response outpost or relocate nearest unit."
            },
            {
                "rank": 5,
                "zone": "East Bengaluru (Whitefield–HAL)",
                "issue": "Traffic bottlenecks worsened by pothole clusters reducing effective road width.",
                "severity": "MEDIUM",
                "recommendation": "Coordinate road repair with traffic diversion planning during off-peak hours."
            }
        ],
        "data_summary": {
            "potholes_total": total_ph,
            "crimes_total": summary["total_crime_incidents"],
            "drainage_total": summary["total_drainage_issues"]
        }
    }
