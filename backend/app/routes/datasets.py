"""
datasets.py route - Serves all available datasets for the city map.
"""
from fastapi import APIRouter
from ..services.heatmap_engine import get_layer

router = APIRouter(prefix="/datasets", tags=["datasets"])

AVAILABLE_DATASETS = [
    {"id": "potholes",     "label": "Potholes",              "color": "#ff7700"},
    {"id": "crime",        "label": "Crime – Synthetic",      "color": "#ff0033"},
    {"id": "crime_ncrb",   "label": "Crime – NCRB 2023",      "color": "#cc0000"},
    {"id": "drainage",     "label": "Drainage Issues",        "color": "#0088ff"},
    {"id": "garbage_dump", "label": "Garbage Dumps",          "color": "#ff4400"},
    {"id": "traffic",      "label": "Traffic Congestion",     "color": "#ffaa00"},
    {"id": "stp",          "label": "Sewage Treatment Plants","color": "#00ccaa"},
    {"id": "street_dogs",  "label": "Street Dog Density",     "color": "#ff8800"},
    {"id": "crashes",      "label": "Road Crashes (BTP 2025)","color": "#ff2200"},
]

@router.get("/")
def list_datasets():
    return {"datasets": AVAILABLE_DATASETS}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str):
    meta = next((d for d in AVAILABLE_DATASETS if d["id"] == dataset_id), None)
    if not meta:
        return {"error": f"Dataset '{dataset_id}' not found.", "available": [d["id"] for d in AVAILABLE_DATASETS]}

    # potholes uses data_service directly
    if dataset_id == "potholes":
        from ..services.data_service import load_potholes
        data = load_potholes()
    else:
        data = get_layer(dataset_id)

    return {
        "id": dataset_id,
        "label": meta["label"],
        "count": len(data),
        "points": data,
    }
