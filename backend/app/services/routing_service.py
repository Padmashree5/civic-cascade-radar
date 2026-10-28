"""
routing_service.py — Custom Dijkstra's algorithm for point-to-point ETA.
Works entirely in-memory with a city graph built from known Bangalore intersections.
"""
import heapq
import math
from typing import Dict, List, Tuple, Optional


# ---- Haversine distance (km) -----
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---- Static city graph: (node_id -> {lat, lng}) + edges ----
CITY_NODES: Dict[int, Tuple[float, float]] = {
    0:  (12.9716, 77.5946),   # City Centre
    1:  (12.9700, 77.5800),   # Malleshwaram
    2:  (12.9756, 77.6029),   # Indiranagar
    3:  (12.9550, 77.6100),   # Koramangala
    4:  (12.9900, 77.5700),   # Yeshwanthpur
    5:  (12.9650, 77.5600),   # Rajajinagar
    6:  (12.9800, 77.6100),   # Banaswadi
    7:  (12.9400, 77.6200),   # HSR Layout
    8:  (12.9300, 77.5800),   # Jayanagar
    9:  (12.9200, 77.6050),   # BTM Layout
    10: (12.9950, 77.6050),   # Hebbal
    11: (12.9100, 77.5750),   # JP Nagar
}

# Directed weighted edges: (from, to, congestion_factor)
# congestion_factor > 1 means slower (traffic), < 1 means faster (highway)
CITY_EDGES: List[Tuple[int, int, float]] = [
    (0, 1, 1.2), (1, 0, 1.3),
    (0, 2, 1.0), (2, 0, 1.0),
    (0, 3, 1.5), (3, 0, 1.4),
    (0, 4, 1.1), (4, 0, 1.1),
    (1, 4, 1.0), (4, 1, 1.0),
    (1, 5, 1.0), (5, 1, 1.0),
    (2, 3, 1.3), (3, 2, 1.3),
    (2, 6, 1.0), (6, 2, 1.0),
    (3, 7, 1.2), (7, 3, 1.2),
    (3, 9, 1.1), (9, 3, 1.1),
    (4, 10, 0.9), (10, 4, 0.9),
    (6, 10, 1.0), (10, 6, 1.0),
    (7, 8, 1.0), (8, 7, 1.0),
    (7, 9, 1.0), (9, 7, 1.0),
    (8, 9, 1.2), (9, 8, 1.2),
    (8, 11, 1.0), (11, 8, 1.0),
    (9, 11, 1.1), (11, 9, 1.1),
]


def _build_adj():
    adj: Dict[int, List[Tuple[int, float]]] = {n: [] for n in CITY_NODES}
    for u, v, factor in CITY_EDGES:
        dist_km = haversine(*CITY_NODES[u], *CITY_NODES[v])
        weight = dist_km * factor  # effective distance
        adj[u].append((v, weight))
    return adj


ADJ = _build_adj()


def _nearest_node(lat: float, lng: float) -> int:
    return min(CITY_NODES, key=lambda n: haversine(lat, lng, *CITY_NODES[n]))


def dijkstra(start: int, end: int) -> Tuple[float, List[int]]:
    """Returns (total_weight, path_node_ids). weight ≈ effective distance km."""
    dist = {n: float("inf") for n in CITY_NODES}
    prev: Dict[int, Optional[int]] = {n: None for n in CITY_NODES}
    dist[start] = 0.0
    pq = [(0.0, start)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == end:
            break
        for v, w in ADJ.get(u, []):
            nd = dist[u] + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    # Reconstruct path
    path = []
    cur: Optional[int] = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    return dist[end], path


def compute_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> dict:
    src = _nearest_node(start_lat, start_lng)
    dst = _nearest_node(end_lat, end_lng)

    if src == dst:
        direct_km = haversine(start_lat, start_lng, end_lat, end_lng)
        return {
            "eta_minutes": round(direct_km * 2, 1),
            "distance_km": round(direct_km, 2),
            "delay_minutes": 0,
            "status": "NORMAL",
            "path": [[start_lat, start_lng], [end_lat, end_lng]],
        }

    effective_dist, path_nodes = dijkstra(src, dst)

    if effective_dist == float("inf"):
        # Fallback: straight-line
        d = haversine(start_lat, start_lng, end_lat, end_lng)
        return {
            "eta_minutes": round(d * 3, 1),
            "distance_km": round(d, 2),
            "delay_minutes": 0,
            "status": "NO_ROUTE",
            "path": [[start_lat, start_lng], [end_lat, end_lng]],
        }

    # Build GeoJSON-style coordinate path
    coords = [[start_lat, start_lng]]
    for nid in path_nodes:
        lat, lng = CITY_NODES[nid]
        coords.append([lat, lng])
    coords.append([end_lat, end_lng])

    speed_kmh = 25  # average city speed
    eta_mins = (effective_dist / speed_kmh) * 60
    delay = 10 if effective_dist > 5 else 0
    status = "HEAVY_TRAFFIC" if delay > 0 else "NORMAL"

    return {
        "eta_minutes": round(eta_mins + delay, 1),
        "distance_km": round(effective_dist, 2),
        "delay_minutes": delay,
        "status": status,
        "path": coords,
    }
