# route_planner.py
import json
import math
from pathlib import Path
import numpy as np
from python_tsp.exact import solve_tsp_dynamic_programming

# ---- Files ----
NPZ_PATH     = "Shadyside_matrix.npz"  # has dist_m, codes, lats, lons (global superset)
STOPS_JSON   = "stops.json"            # tapped student stops: {code: {name, latitude, longitude}, ...}
PICKUPS_JSON = "pickups.json"          # depots in insertion order; last = origin, first = destination

BIG_M = 10**9  # large penalty to "forbid" edges

# --- Utilities ---
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def load_npz(npz_path):
    data = np.load(npz_path, allow_pickle=True)
    dist_m = data["dist_m"]  # (N,N) int32
    codes  = data["codes"]   # (N,) stop codes (strings)
    lats   = data["lats"]    # (N,) float32
    lons   = data["lons"]    # (N,) float32
    code_to_idx = {str(codes[i]): i for i in range(len(codes))}
    return dist_m, codes, lats, lons, code_to_idx

def load_pickups(path):
    d = json.loads(Path(path).read_text())
    items = list(d.items())
    first_name, first = items[0]        # destination
    last_name, last   = items[-1]       # origin
    origin = (last_name, float(last["latitude"]), float(last["longitude"]))
    dest   = (first_name, float(first["latitude"]), float(first["longitude"]))
    return origin, dest

def load_stop_codes(path):
    d = json.loads(Path(path).read_text())
    return list(d.keys())  # preserve file order (or replace with sorted(d.keys()) if you prefer)

# --- Build augmented matrix: [origin] + stops + [dest] ---
def build_augmented_matrix(stop_codes, origin, dest, dist_m, lats_all, lons_all, code_to_idx):
    k = len(stop_codes)
    n = k + 2  # origin + k stops + dest
    D = np.zeros((n, n), dtype=float)

    # indices in augmented matrix
    ORI = 0
    DES = n - 1

    # Gather global indices and coords for the k stops
    stop_gidx = [code_to_idx[c] for c in stop_codes]
    stop_lats = [float(lats_all[i]) for i in stop_gidx]
    stop_lons = [float(lons_all[i]) for i in stop_gidx]

    # Fill inter-stop costs from precomputed global matrix
    for a in range(k):
        ia = stop_gidx[a]
        for b in range(k):
            if a == b:
                D[1+a, 1+b] = 0.0
            else:
                ib = stop_gidx[b]
                D[1+a, 1+b] = float(dist_m[ia, ib])

    # Origin to stops (allow), stops to origin (forbid with BIG_M)
    for j in range(k):
        D[ORI, 1+j] = haversine_m(origin[1], origin[2], stop_lats[j], stop_lons[j])
        D[1+j, ORI] = BIG_M

    # Stops to destination (allow), destination to stops (forbid)
    for i in range(k):
        D[1+i, DES] = haversine_m(stop_lats[i], stop_lons[i], dest[1], dest[2])
        D[DES, 1+i] = BIG_M

    # Origin to destination: allow (doesn't matter; all stops must be visited)
    D[ORI, DES] = haversine_m(origin[1], origin[2], dest[1], dest[2])

    # Destination to origin: FORCE close here with zero cost
    D[DES, ORI] = 0.0

    # Disallow incoming to origin from any node except dest (already BIG_M above)
    # Disallow leaving destination to anywhere except origin (already BIG_M above)

    # Zero diagonals
    np.fill_diagonal(D, 0.0)
    return D

def extract_order_between_origin_and_dest(perm):
    """
    python-tsp returns a cycle starting at node 0 (origin).
    Our constraints force the cycle to be: origin -> ... -> dest -> origin.
    We need the subsequence strictly between origin (0) and dest (n-1).
    """
    # Find where dest appears in the cycle after the initial 0
    # perm is like [0, a, b, ..., dest, 0] conceptually (the library omits the closing 0)
    # We just slice everything after the initial 0 until we hit dest.
    path = []
    for node in perm[1:]:
        if node == (len(perm) - 1):  # n-1 is dest
            break
        path.append(node)
    print(path)
    return path  # nodes in {1..k} order

def deep_link_creator():
    # Load data
    dist_m, codes_all, lats_all, lons_all, code_to_idx = load_npz(NPZ_PATH)
    stop_codes = load_stop_codes(STOPS_JSON)
    origin, dest = load_pickups(PICKUPS_JSON)

    # Build augmented matrix and solve with python-tsp
    D = build_augmented_matrix(stop_codes, origin, dest, dist_m, lats_all, lons_all, code_to_idx)
    perm, total_cost = solve_tsp_dynamic_programming(D)

    # Extract the waypoint order (indices 1..k mapped back to stop codes)
    idx_between = extract_order_between_origin_and_dest(perm)
    waypoints_codes = [stop_codes[i - 1] for i in idx_between]  # shift because stops start at 1

    # Build deep link
    def fmt(lat, lon): return f"{lat:.6f},{lon:.6f}"
    origin_str = fmt(origin[1], origin[2])
    dest_str   = fmt(dest[1], dest[2])

    # Use the master arrays to fetch precise lat/lon for each stop code
    waypoint_coords = []
    for code in waypoints_codes:
        gi = code_to_idx[code]
        waypoint_coords.append(fmt(float(lats_all[gi]), float(lons_all[gi])))

    waypoints_param = "|".join(waypoint_coords)
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_str}"
        f"&destination={dest_str}"
        f"&waypoints={waypoints_param}"
        "&travelmode=driving"
    )
    return url

# Run
if __name__ == "__main__":
    print(deep_link_creator())