"""
generate_new_datasets.py
Run once to produce synthetic CSVs for all new dashboard layers.
  python datasets/generate_new_datasets.py
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).parent
rng = random.Random(2025)

# ── Shared city zones ─────────────────────────────────────────────────────────
ZONES = [
    (12.9716, 77.5946, "Majestic"),
    (12.9352, 77.6244, "Whitefield"),
    (12.9780, 77.6408, "Marathahalli"),
    (12.8340, 77.6602, "Bommanahalli"),
    (13.0067, 77.5963, "Hebbal"),
    (12.9007, 77.5996, "Jayanagar"),
    (12.9600, 77.5700, "Rajajinagar"),
    (12.8440, 77.6100, "BTM Layout"),
    (12.9280, 77.6276, "HAL"),
    (13.0360, 77.5970, "Yelahanka"),
    (12.9580, 77.6060, "Indiranagar"),
    (12.9200, 77.5800, "Basavanagudi"),
    (12.9350, 77.6270, "Koramangala"),
    (12.8455, 77.6603, "Electronic City"),
    (12.9076, 77.5838, "JP Nagar"),
    (12.9091, 77.5466, "Banashankari"),
]

def jitter(base, spread=0.025):
    return round(base + rng.uniform(-spread, spread), 6)


# ── 1. BMTC Bus Stops ─────────────────────────────────────────────────────────
BMTC_ROUTES = [
    "500C", "201", "335E", "401", "KIA-9", "VAJRA", "500D", "G1", "G7",
    "219", "250", "174", "351", "402", "600", "MFS-6",
]
FREQ_LABELS = ["High", "High", "Medium", "Medium", "Low"]

rows = []
for lat, lng, zone in ZONES:
    n = rng.randint(8, 18)
    for _ in range(n):
        freq = rng.uniform(0.3, 1.0)
        rows.append({
            "stop_name": f"{zone} Bus Stop {rng.randint(1,99)}",
            "lat": jitter(lat, 0.030),
            "lng": jitter(lng, 0.030),
            "route": rng.choice(BMTC_ROUTES),
            "frequency": round(freq, 2),
            "frequency_label": FREQ_LABELS[int(freq * 4.99)],
            "zone": zone,
        })

with open(OUT / "bmtc_bus_stops.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"bmtc_bus_stops.csv  — {len(rows)} rows")


# ── 2. Noise Pollution Stations ───────────────────────────────────────────────
NOISE_PLACES = ["Junction", "Market", "Residential", "School Zone", "Industrial", "Hospital Zone"]

rows = []
for lat, lng, zone in ZONES:
    for i in range(rng.randint(3, 6)):
        db = round(rng.uniform(48, 98), 1)
        rows.append({
            "name": f"{zone} — {rng.choice(NOISE_PLACES)}",
            "lat": jitter(lat, 0.020),
            "lng": jitter(lng, 0.020),
            "db_level": db,
            "zone": zone,
        })

with open(OUT / "noise_stations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"noise_stations.csv  — {len(rows)} rows")


# ── 3. Metro Stations ─────────────────────────────────────────────────────────
METRO_STATIONS = [
    # (name, lat, lng, line, line_color, daily_ridership)
    ("Majestic (Nadaprabhu Kempegowda)", 12.9770, 77.5713, "Purple", "#9c27b0", 85000),
    ("MG Road",                           12.9756, 77.6094, "Purple", "#9c27b0", 62000),
    ("Trinity",                           12.9701, 77.6173, "Purple", "#9c27b0", 38000),
    ("Indiranagar",                       12.9784, 77.6408, "Purple", "#9c27b0", 45000),
    ("Baiyappanahalli",                   12.9924, 77.6593, "Purple", "#9c27b0", 30000),
    ("Whitefield",                        12.9698, 77.7499, "Purple", "#9c27b0", 28000),
    ("Mysore Road",                       12.9582, 77.5219, "Purple", "#9c27b0", 22000),
    ("Nadaprabhu Kempegowda (Green)",     12.9770, 77.5713, "Green",  "#4caf50", 85000),
    ("Sandal Soap Factory",               13.0013, 77.5715, "Green",  "#4caf50", 18000),
    ("Yeshwanthpur",                      13.0196, 77.5480, "Green",  "#4caf50", 25000),
    ("Hesaraghatta Road",                 13.0490, 77.5260, "Green",  "#4caf50", 12000),
    ("Nagasandra",                        13.0680, 77.5090, "Green",  "#4caf50", 9000),
    ("Jayanagar",                         12.9250, 77.5830, "Yellow", "#ffc107", 35000),
    ("Bommasandra",                       12.8152, 77.6834, "Pink",   "#e91e63", 15000),
    ("Yelahanka",                         13.1007, 77.5960, "Yellow", "#ffc107", 20000),
    ("Koramangala",                       12.9352, 77.6245, "Yellow", "#ffc107", 40000),
    ("Electronic City",                   12.8455, 77.6603, "Pink",   "#e91e63", 32000),
    ("Hebbal",                            13.0450, 77.5970, "Green",  "#4caf50", 28000),
    ("RV Road",                           12.9400, 77.5780, "Yellow", "#ffc107", 22000),
    ("Banashankari",                      12.9091, 77.5466, "Yellow", "#ffc107", 18000),
]

rows = [
    {
        "name": name, "lat": lat, "lng": lng,
        "line": line, "line_color": color,
        "daily_ridership": ridership,
        "ridership_index": round(min(1.0, ridership / 90000), 3),
    }
    for name, lat, lng, line, color, ridership in METRO_STATIONS
]

with open(OUT / "metro_stations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"metro_stations.csv  — {len(rows)} rows")


# ── 4. School & College Locations ────────────────────────────────────────────
SCHOOL_TYPES = ["Government School", "Private School", "CBSE School", "College", "University"]
SCHOOL_NAMES = [
    "Kendriya Vidyalaya", "Delhi Public School", "National High School",
    "Bishop Cotton", "Christ University", "RV College", "BMS College",
    "Vijaya College", "Jyoti Nivas College", "Mount Carmel",
    "Clarence High School", "Baldwin Boys", "St Joseph",
]

rows = []
for lat, lng, zone in ZONES:
    for _ in range(rng.randint(4, 9)):
        school_type = rng.choice(SCHOOL_TYPES)
        students = rng.randint(300, 4500)
        rows.append({
            "name": f"{rng.choice(SCHOOL_NAMES)} — {zone}",
            "lat": jitter(lat, 0.025),
            "lng": jitter(lng, 0.025),
            "type": school_type,
            "students": students,
            "intensity": round(min(1.0, students / 5000), 3),
            "zone": zone,
        })

with open(OUT / "school_locations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"school_locations.csv — {len(rows)} rows")


# ── 5. Street Lights ─────────────────────────────────────────────────────────
LIGHT_STATUSES = ["working", "working", "working", "dim", "faulty"]

rows = []
for lat, lng, zone in ZONES:
    for _ in range(rng.randint(20, 40)):
        rows.append({
            "lat": jitter(lat, 0.030),
            "lng": jitter(lng, 0.030),
            "status": rng.choice(LIGHT_STATUSES),
            "zone": zone,
        })

with open(OUT / "street_lights.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"street_lights.csv   — {len(rows)} rows")


# ── 6. Tree Canopy ────────────────────────────────────────────────────────────
DENSE_ZONES = {"Jayanagar", "Basavanagudi", "Indiranagar", "JP Nagar", "Koramangala"}

rows = []
for lat, lng, zone in ZONES:
    base_density = 0.65 if zone in DENSE_ZONES else 0.35
    for _ in range(rng.randint(10, 20)):
        density = round(min(1.0, base_density + rng.uniform(-0.2, 0.2)), 3)
        rows.append({
            "lat": jitter(lat, 0.025),
            "lng": jitter(lng, 0.025),
            "canopy_density": density,
            "ward": zone,
        })

with open(OUT / "tree_canopy.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"tree_canopy.csv     — {len(rows)} rows")


# ── 7. BWSSB Water Quality Zones ─────────────────────────────────────────────
rows = []
for lat, lng, zone in ZONES:
    ph = round(rng.uniform(6.8, 8.2), 2)
    tds = rng.randint(120, 580)
    quality = round(rng.uniform(0.45, 0.98), 3)
    rows.append({
        "zone_name": f"BWSSB Zone — {zone}",
        "lat": jitter(lat, 0.010),
        "lng": jitter(lng, 0.010),
        "quality_score": quality,
        "ph": ph,
        "tds": tds,
        "ward": zone,
    })

with open(OUT / "bwssb_water_zones.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"bwssb_water_zones.csv — {len(rows)} rows")


# ── 8. Construction Permits ───────────────────────────────────────────────────
PERMIT_TYPES = ["Residential", "Commercial", "Road Work", "Utility", "Demolition"]
PERMIT_STATUS = ["Active", "Active", "Completed", "Pending"]

rows = []
for lat, lng, zone in ZONES:
    for _ in range(rng.randint(5, 12)):
        rows.append({
            "lat": jitter(lat, 0.028),
            "lng": jitter(lng, 0.028),
            "type": rng.choice(PERMIT_TYPES),
            "status": rng.choice(PERMIT_STATUS),
            "ward": zone,
            "intensity": round(rng.uniform(0.3, 0.9), 2),
        })

with open(OUT / "construction_permits.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"construction_permits.csv — {len(rows)} rows")

print("\nAll datasets generated successfully.")
