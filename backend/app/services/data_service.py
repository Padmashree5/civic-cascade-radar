"""
data_service.py - Loads real and synthetic datasets for the Smart City backend.

Real datasets loaded:
- Pothole data: bengaluru_potholes.csv
- Garbage dump: garbage_dump_banglore.csv
- STP: stp.csv.csv
- Emergency services: bengaluru_emergency_services.csv

Synthetic datasets generated:
- Crime data: randomised points across Bengaluru's key zones
- Drainage issues: randomised points across Bengaluru
"""
import csv
import random
import os
from io import StringIO
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATASETS_DIR = Path(__file__).parent.parent.parent.parent / "datasets"
EMERGENCY_CSV = DATASETS_DIR / "bengaluru_emergency_services.csv"

# Maps CSV "Type" values → internal type used by coverage_engine
_TYPE_NORM = {
    "police": "police",
    "hospital": "hospital",
    "fire_station": "fire",
    "fire": "fire",
    "ambulance": "hospital",
    "clinic": "hospital",
}

# Category labels from pothole CSV (integer 0-3)
POTHOLE_SEVERITY = {0: "Low", 1: "Medium", 2: "High", 3: "Critical"}

# ── Real Pothole Data ────────────────────────────────────────────────────────

def load_potholes() -> list[dict]:
    """Load real pothole data from CSV. Returns list of dicts."""
    potholes = []
    csv_path = DATA_DIR / "bengaluru_potholes.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["lat"])
                lng = float(row["long"])
                category = int(row["category"]) if row["category"] else 1
                potholes.append({
                    "lat": lat,
                    "lng": lng,
                    "severity": POTHOLE_SEVERITY.get(category, "Medium"),
                    "category_code": category,
                    "intensity": round(min(1.0, (category + 1) / 4.0), 2),
                    "created_at": row.get("created_at", ""),
                })
            except (ValueError, KeyError):
                continue
    return potholes

# ── Synthetic Crime Data ─────────────────────────────────────────────────────

CRIME_ZONES = [
    # (center_lat, center_lng, zone_name, num_incidents)
    (12.9716, 77.5946, "Majestic", 45),
    (12.9352, 77.6244, "Whitefield", 32),
    (12.9780, 77.6408, "Marathahalli", 28),
    (12.8340, 77.6602, "Bommanahalli", 20),
    (13.0067, 77.5963, "Hebbal", 18),
    (12.9007, 77.5996, "Jayanagar", 15),
    (12.9600, 77.5700, "Rajajinagar", 22),
    (12.8440, 77.6600, "BTM Layout", 30),
    (12.9280, 77.6276, "HAL", 12),
    (13.0360, 77.5970, "Yelahanka", 17),
]

CRIME_TYPES = ["Theft", "Vehicle Crime", "Assault", "Burglary", "Drug Offence"]

def generate_crime_data() -> list[dict]:
    """Generate synthetic crime data around known high-density zones."""
    random.seed(42)  # reproducible synthetic data
    crimes = []
    for lat, lng, zone, count in CRIME_ZONES:
        for _ in range(count):
            crimes.append({
                "lat": round(lat + random.uniform(-0.018, 0.018), 6),
                "lng": round(lng + random.uniform(-0.018, 0.018), 6),
                "zone": zone,
                "crime_type": random.choice(CRIME_TYPES),
                "intensity": round(random.uniform(0.4, 1.0), 2),
            })
    return crimes

# ── Synthetic Drainage Data ──────────────────────────────────────────────────

DRAINAGE_ZONES = [
    (12.9580, 77.6060, "Indiranagar", 25),
    (12.9200, 77.5800, "Basavanagudi", 20),
    (12.9716, 77.5946, "Majestic", 30),
    (12.8900, 77.5900, "Banashankari", 18),
    (12.9000, 77.6500, "HSR Layout", 15),
    (13.0500, 77.5900, "Jakkur", 12),
    (12.8700, 77.6600, "Electronic City", 22),
    (12.9450, 77.7000, "Marathahalli Outer", 17),
]

DRAINAGE_STATES = ["Blocked", "Overflowing", "Broken Cover", "Partial Block"]

def load_emergency_services() -> list[dict]:
    """Load real emergency services from bengaluru_emergency_services.csv."""
    services = []
    if not EMERGENCY_CSV.exists():
        return services
    with open(EMERGENCY_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                raw_type = row.get("Type", "").lower().strip()
                norm_type = _TYPE_NORM.get(raw_type, raw_type)
                services.append({
                    "id": f"CSV_{i}",
                    "name": row["Name"].strip(),
                    "type": norm_type,
                    "lat": float(row["Latitude"]),
                    "lng": float(row["Longitude"]),
                    "address": row.get("Address", "").strip(),
                })
            except (ValueError, KeyError):
                continue
    return services


def generate_drainage_data() -> list[dict]:
    """Generate synthetic drainage issue data across Bengaluru."""
    random.seed(99)
    drains = []
    for lat, lng, zone, count in DRAINAGE_ZONES:
        for _ in range(count):
            drains.append({
                "lat": round(lat + random.uniform(-0.02, 0.02), 6),
                "lng": round(lng + random.uniform(-0.02, 0.02), 6),
                "zone": zone,
                "state": random.choice(DRAINAGE_STATES),
                "intensity": round(random.uniform(0.3, 0.95), 2),
            })
    return drains
