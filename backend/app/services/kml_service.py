"""
kml_service.py - Parse KML files and return GeoJSON-compatible feature lists.
Handles Polygon, LineString, and Point geometries + ExtendedData properties.
Detects KML namespace dynamically to support Google Earth and OGC KML variants.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any


def _detect_ns(root: ET.Element) -> str:
    """Extract namespace URI from root element tag."""
    tag = root.tag
    if tag.startswith("{"):
        return tag[1:tag.index("}")]
    return ""


def _parse_coord_string(text: str) -> List[List[float]]:
    """'lng,lat,alt lng,lat,alt ...' → [[lng, lat], ...]"""
    coords = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                coords.append([float(parts[0]), float(parts[1])])
            except ValueError:
                continue
    return coords


def parse_kml(filepath: Path, max_features: int = 500) -> List[Dict[str, Any]]:
    """
    Parse a KML file and return GeoJSON-compatible features.
    Each item: { "geometry": {...}, "properties": {...} }
    """
    try:
        tree = ET.parse(filepath)
    except (ET.ParseError, FileNotFoundError):
        return []

    root = tree.getroot()
    ns = _detect_ns(root)

    def tag(name: str) -> str:
        return f"{{{ns}}}{name}" if ns else name

    features = []

    for placemark in root.iter(tag("Placemark")):
        if len(features) >= max_features:
            break

        # ── Properties from name + ExtendedData ──
        props: Dict[str, Any] = {}
        name_el = placemark.find(tag("name"))
        if name_el is not None and name_el.text:
            props["name"] = name_el.text.strip()

        schema_data = placemark.find(f".//{tag('SchemaData')}")
        if schema_data is not None:
            for sd in schema_data.findall(tag("SimpleData")):
                props[sd.get("name", "")] = sd.text or ""

        extended = placemark.find(f".//{tag('ExtendedData')}")
        if extended is not None:
            for data_el in extended.findall(tag("Data")):
                k = data_el.get("name", "")
                v_el = data_el.find(tag("value"))
                if k and v_el is not None:
                    props[k] = v_el.text or ""

        # ── Geometry ──
        geometry = None

        polygon = placemark.find(f".//{tag('Polygon')}")
        if polygon is not None:
            outer = polygon.find(f".//{tag('outerBoundaryIs')}//{tag('coordinates')}")
            if outer is not None and outer.text:
                ring = _parse_coord_string(outer.text)
                if ring:
                    geometry = {"type": "Polygon", "coordinates": [ring]}

        if geometry is None:
            linestring = placemark.find(f".//{tag('LineString')}")
            if linestring is not None:
                coords_el = linestring.find(tag("coordinates"))
                if coords_el is not None and coords_el.text:
                    coords = _parse_coord_string(coords_el.text)
                    if coords:
                        geometry = {"type": "LineString", "coordinates": coords}

        if geometry is None:
            point = placemark.find(f".//{tag('Point')}")
            if point is not None:
                coords_el = point.find(tag("coordinates"))
                if coords_el is not None and coords_el.text:
                    coords = _parse_coord_string(coords_el.text)
                    if coords:
                        geometry = {"type": "Point", "coordinates": coords[0]}

        if geometry:
            features.append({"geometry": geometry, "properties": props})

    return features
