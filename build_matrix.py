# build_shadyside_matrix_min.py
import json
import math
from pathlib import Path
import numpy as np

STOPS_JSON = "Shadyside.json"
OUT_NPZ    = "Shadyside_matrix.npz"
OUT_INDEX  = "Shadyside_index.json"

def load_stops_dict(path):
    data = json.loads(Path(path).read_text())
    # Deterministic order: sort by code (keys). If you prefer file insertion order, use list(data.keys()).
    codes = sorted(data.keys())
    lats  = np.array([float(data[c]["latitude"])  for c in codes], dtype=np.float64)
    lons  = np.array([float(data[c]["longitude"]) for c in codes], dtype=np.float64)
    return codes, lats, lons

def haversine_matrix(lat_deg, lon_deg):
    """Vectorized Haversine NxN in meters (int32)."""
    R = 6371000.0  # Earth radius (m)
    lat = np.radians(lat_deg)[:, None]  # (N,1)
    lon = np.radians(lon_deg)[:, None]  # (N,1)
    dlat = lat - lat.T
    dlon = lon - lon.T
    a = np.sin(dlat/2.0)**2 + np.cos(lat) * np.cos(lat.T) * np.sin(dlon/2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    dist = R * c
    np.fill_diagonal(dist, 0.0)
    return dist.astype(np.int32)  # meters as integers (compact & OR-Tools-friendly)

def main():
    codes, lats, lons = load_stops_dict(STOPS_JSON)
    dist_m = haversine_matrix(lats, lons)

    # Save compact multi-array NPZ
    np.savez_compressed(
        OUT_NPZ,
        dist_m=dist_m,
        codes=np.array(codes, dtype=object),
        lats=lats.astype(np.float32),
        lons=lons.astype(np.float32),
    )

    # Also save an index map for convenience
    code_to_index = {c: i for i, c in enumerate(codes)}
    index_to_code = {i: c for i, c in enumerate(codes)}
    Path(OUT_INDEX).write_text(json.dumps(
        {"index_to_code": index_to_code, "code_to_index": code_to_index},
        indent=2
    ))

    print(f"[OK] {OUT_NPZ} saved with matrix shape {dist_m.shape} (N={len(codes)}).")
    print(f"[OK] {OUT_INDEX} saved.")

if __name__ == "__main__":
    main()