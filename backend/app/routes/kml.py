from fastapi import APIRouter
from pathlib import Path
from ..services.kml_service import parse_kml

router = APIRouter(prefix="/kml", tags=["kml"])

_DATASETS = Path(__file__).parent.parent.parent.parent / "datasets"

_KML_FILES = {
    "ground_potential": _DATASETS / "ground_potential_map.kml",
    "road_width":       _DATASETS / "road_width_map.kml",
    "wards":            _DATASETS / "boundary_wards.kml",
}

_KML_META = {
    "ground_potential": {"label": "Groundwater Potential",  "max_features": 400},
    "road_width":       {"label": "Road Width Map",          "max_features": 500},
    "wards":            {"label": "BBMP Ward Boundaries",    "max_features": 300},
}


@router.get("/{layer_id}")
def get_kml_layer(layer_id: str):
    if layer_id not in _KML_FILES:
        return {"error": f"Unknown KML layer: {layer_id}", "available": list(_KML_FILES.keys())}

    meta = _KML_META[layer_id]
    features = parse_kml(_KML_FILES[layer_id], max_features=meta["max_features"])
    return {
        "id": layer_id,
        "label": meta["label"],
        "count": len(features),
        "features": features,
    }
