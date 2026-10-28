"""
groq_service.py - Uses Groq LLM to generate actual city insights from aggregated data.

The Groq API key should be set in .env: GROQ_API_KEY=<your key>
"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


async def call_groq(prompt: str) -> str:
    """Send a prompt to Groq and return the response text."""
    if not GROQ_API_KEY:
        return "GROQ_API_KEY not set. Please add it to backend/.env"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an urban infrastructure analyst for Bengaluru, India. "
                    "Analyze the provided city data and give concise, actionable insights "
                    "in a structured JSON format. Be specific about zones and severity."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_API_URL, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def chat_about_city(question: str) -> str:
    """Answer a free-form question about Bengaluru city data."""
    if not GROQ_API_KEY:
        return "GROQ_API_KEY not configured. Add it to backend/.env to enable AI chat."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert urban analyst for Bengaluru (Bangalore), India. "
                    "You have deep knowledge of BBMP zones, traffic, crime, infrastructure, "
                    "flooding, road quality, emergency services, and civic data. "
                    "Answer concisely and specifically — include zones, numbers, and actionable advice."
                ),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.5,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_API_URL, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def generate_city_insights(summary: dict) -> dict:
    """
    Given a summary dict of city data, return structured insights from Groq.
    `summary` should contain counts/zones per layer.
    """
    # Build rich zone breakdown strings for the prompt
    top_potholes = summary.get("top_pothole_hotspots", [])[:5]
    crime_zones = summary.get("crime_by_zone", {})
    drain_zones = summary.get("drainage_by_zone", {})

    top_crime = sorted(crime_zones.items(), key=lambda x: x[1], reverse=True)[:5]
    top_drain = sorted(drain_zones.items(), key=lambda x: x[1], reverse=True)[:5]

    prompt = f"""
You are a senior urban infrastructure analyst for Bengaluru, India (BBMP / BMTC advisory team).
Analyze the following real and synthetic smart-city data and produce a prioritised action report.

=== DATA SUMMARY ===
City: {summary.get("city", "Bengaluru, India")}
Analysis date: {summary.get("analysis_date", "2026-03-31")}

POTHOLE DATA (real CSV – {summary.get("total_potholes", 0)} records):
  Severity breakdown: {json.dumps(summary.get("pothole_severity", {}))}
  Top hotspot grid cells (lat/lng rounded to 0.1°):
{chr(10).join(f"    {h['grid']}: {h['count']} potholes" for h in top_potholes)}

CRIME DATA (synthetic – {summary.get("total_crime_incidents", 0)} incidents):
  Top zones by incident count:
{chr(10).join(f"    {z}: {c} incidents" for z, c in top_crime)}

DRAINAGE DATA (synthetic – {summary.get("total_drainage_issues", 0)} issues):
  Top zones by issue count:
{chr(10).join(f"    {z}: {c} issues" for z, c in top_drain)}

=== INSTRUCTIONS ===
1. Cross-reference the three datasets to identify compounding risks (e.g. high potholes + poor drainage = monsoon flood risk).
2. Identify the 5 most critical infrastructure weaknesses specific to Bengaluru wards/neighbourhoods.
3. For each weakness state: the responsible civic body (BBMP, BDA, BWSSB, BESCOM, etc.).
4. Estimate affected population where possible (use typical Bengaluru ward density ~25,000–80,000).
5. Give a 1–2 sentence SMART recommendation (specific, measurable, time-bound if possible).

Respond ONLY in the following JSON format, no markdown, no extra text:
{{
  "title": "Bengaluru Smart City Infrastructure Report",
  "generated_at": "{summary.get("analysis_date", "2026-03-31")}",
  "top_weaknesses": [
    {{
      "rank": 1,
      "zone": "<specific Bengaluru ward or neighbourhood>",
      "issue": "<specific issue with numbers>",
      "severity": "CRITICAL|HIGH|MEDIUM",
      "civic_body": "<BBMP|BDA|BWSSB|BESCOM|Traffic Police>",
      "affected_population": "<number estimate>",
      "recommendation": "<SMART recommendation>"
    }}
  ],
  "summary_narrative": "<3-4 sentence overall assessment of Bengaluru infrastructure health, highlighting the most urgent pre-monsoon actions>"
}}
"""

    raw = await call_groq(prompt)

    # Try to parse the JSON response
    try:
        # Strip potential markdown code fences if model adds them
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        # Return the raw string wrapped in a dict if parsing fails
        return {
            "title": "City Infrastructure Analysis – Bengaluru",
            "raw_response": raw,
            "error": "Response was not valid JSON"
        }
