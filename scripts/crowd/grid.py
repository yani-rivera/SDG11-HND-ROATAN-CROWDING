"""Regular lon/lat grid over the hexagons: each cell knows which hexagon it falls in.

Used by the Tanaka view (browser) and the posters (Python) to turn hexagon counts into a
smooth people-density surface.
"""

import math

import geopandas as gpd
import numpy as np


def build(hexes_wgs, cell_m: float):
    w, s, e, n = hexes_wgs.total_bounds
    lat0 = (s + n) / 2
    dlat = cell_m / 110_574.0
    dlon = cell_m / (111_320.0 * math.cos(math.radians(lat0)))
    pad = 3                                      # empty cells around the island for smoothing
    west, north = w - pad * dlon, n + pad * dlat
    width = int(math.ceil((e - w) / dlon)) + 2 * pad
    height = int(math.ceil((n - s) / dlat)) + 2 * pad

    xs = west + (np.arange(width) + 0.5) * dlon
    ys = north - (np.arange(height) + 0.5) * dlat
    gx, gy = np.meshgrid(xs, ys)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(gx.ravel(), gy.ravel()), crs=4326)
    hx = hexes_wgs[["geometry"]].reset_index(drop=True)
    hx["hex_i"] = np.arange(len(hx))
    j = gpd.sjoin(pts, hx, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    idx = j["hex_i"].fillna(-1).astype(int).to_numpy()
    return {"width": width, "height": height, "west": west, "north": north,
            "dlon": dlon, "dlat": dlat, "idx": idx}


def density(grid, hex_people, hex_land_km2):
    """People per km² per cell (0 at sea)."""
    idx = grid["idx"]
    dens = np.zeros(idx.shape, dtype="float64")
    land = idx >= 0
    dens[land] = np.asarray(hex_people)[idx[land]] / np.asarray(hex_land_km2)[idx[land]]
    return dens.reshape(grid["height"], grid["width"])


def gaussian_blur(arr, sigma):
    """Separable Gaussian blur in pure numpy (no scipy needed)."""
    if sigma <= 0:
        return arr
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(arr, r, mode="constant")
    tmp = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, tmp)
