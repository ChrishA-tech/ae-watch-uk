"""Geospatial Catchment Feature Engineering for AE-Watch UK.

Computes PostGIS/H3 spatial catchment congestion features and
Inverse-Distance-Weighted (IDW) spillover metrics across neighboring
Cheshire & Merseyside ICB Trusts within 25 km of Liverpool University Hospitals (REM).
Author: CHRISH PEP FELIX A
"""

import math
from typing import Any

import h3
import polars as pl

from ae_watch.utils.logger import logger

# Trust hospital site coordinates
TRUST_CENTROIDS = {
    "REM": {"name": "Liverpool University Hospitals", "lat": 53.4093, "lon": -2.9566},
    "RJR": {"name": "Countess of Chester Hospital", "lat": 53.2104, "lon": -2.8986},
    "RBL": {"name": "Wirral University Teaching Hospital", "lat": 53.3644, "lon": -3.0782},
    "RWW": {"name": "Warrington and Halton Hospitals", "lat": 53.3768, "lon": -2.6074},
    "RBS": {"name": "Alder Hey Children's NHS FT", "lat": 53.4243, "lon": -2.8953},
    "REP": {"name": "Liverpool Women's NHS FT", "lat": 53.3965, "lon": -2.9602},
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic points in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_trust_h3_index(trust_code: str, resolution: int = 7) -> str:
    """Return H3 hexagonal cell index for a Trust primary hospital site."""
    centroid = TRUST_CENTROIDS.get(trust_code.upper())
    if not centroid:
        # Fallback to REM centroid if unknown trust
        centroid = TRUST_CENTROIDS["REM"]
    return h3.latlng_to_cell(centroid["lat"], centroid["lon"], resolution)


def compute_trust_distance_matrix() -> dict[tuple[str, str], float]:
    """Compute pairwise distance matrix in kilometers across target Trusts."""
    distances: dict[tuple[str, str], float] = {}
    trusts = list(TRUST_CENTROIDS.keys())
    for i, t1 in enumerate(trusts):
        for j, t2 in enumerate(trusts):
            if i == j:
                distances[(t1, t2)] = 0.0
            else:
                c1 = TRUST_CENTROIDS[t1]
                c2 = TRUST_CENTROIDS[t2]
                d = haversine_distance_km(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
                distances[(t1, t2)] = round(d, 3)
    return distances


DISTANCE_MATRIX = compute_trust_distance_matrix()


def compute_idw_catchment_spillover(
    df: pl.DataFrame,
    target_trust: str = "REM",
    radius_km: float = 25.0,
) -> pl.DataFrame:
    """Compute Inverse-Distance-Weighted (IDW) spillover metrics from neighboring Trusts within radius_km.

    Weights decay inversely with distance: w_ij = 1 / d_ij.
    Calculates weighted neighbor breach rate and weighted attendance pressure per period_date.
    """
    logger.info("computing_idw_catchment_spillover", target_trust=target_trust, radius_km=radius_km)

    # Filter to periods where data exists
    periods = df.select("period_date").unique().sort("period_date")["period_date"].to_list()
    results: list[dict[str, Any]] = []

    for period in periods:
        period_df = df.filter(pl.col("period_date") == period)
        trust_rows = {
            row["trust_code"]: row
            for row in period_df.iter_rows(named=True)
            if row.get("trust_code") in TRUST_CENTROIDS
        }

        # For target_trust, find neighbors within radius_km
        sum_weights = 0.0
        weighted_breach_sum = 0.0
        weighted_att_sum = 0.0
        neighbor_count = 0

        for neighbor_code, neighbor_data in trust_rows.items():
            if neighbor_code == target_trust:
                continue

            dist = DISTANCE_MATRIX.get((target_trust, neighbor_code), 999.0)
            if 0.0 < dist <= radius_km:
                weight = 1.0 / dist
                sum_weights += weight
                breach_pct = float(neighbor_data.get("breach_4hr_pct") or 0.0)
                attendances = float(neighbor_data.get("total_attendances") or 0.0)

                weighted_breach_sum += weight * breach_pct
                weighted_att_sum += weight * attendances
                neighbor_count += 1

        idw_neighbor_breach_rate = (
            round(weighted_breach_sum / sum_weights, 3) if sum_weights > 0.0 else 0.0
        )
        idw_neighbor_attendance_pressure = (
            round(weighted_att_sum / sum_weights, 3) if sum_weights > 0.0 else 0.0
        )

        results.append(
            {
                "period_date": period,
                "trust_code": target_trust,
                "idw_neighbor_breach_rate": idw_neighbor_breach_rate,
                "idw_neighbor_attendance_pressure": idw_neighbor_attendance_pressure,
                "active_neighbors_count": neighbor_count,
                "h3_res7_cell": get_trust_h3_index(target_trust, resolution=7),
            }
        )

    return pl.DataFrame(results)
