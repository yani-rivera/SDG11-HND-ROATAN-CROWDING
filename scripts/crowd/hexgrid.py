"""Flat-top hexagon grid over the land, in a metric CRS (pure shapely)."""

import math

import geopandas as gpd
from shapely.geometry import Polygon


def _hexagon(cx, cy, r):
    return Polygon([(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                    for a in range(0, 360, 60)])


def build(land_m: gpd.GeoDataFrame, cell_size_m: float, min_land_fraction: float):
    """land_m must be in a metric CRS. Returns hexagons with land_km2 and land_fraction."""
    r = cell_size_m / math.sqrt(3)          # circumradius from flat-to-flat width
    dx, dy = 1.5 * r, cell_size_m
    minx, miny, maxx, maxy = land_m.total_bounds
    land = land_m.geometry.iloc[0]
    hexes, col, x = [], 0, minx - r
    while x <= maxx + r:
        y = miny - dy + (dy / 2 if col % 2 else 0)
        while y <= maxy + dy:
            h = _hexagon(x, y, r)
            if h.intersects(land):
                inter = h.intersection(land).area
                frac = inter / h.area
                if frac >= min_land_fraction:
                    hexes.append({"geometry": h, "land_km2": inter / 1e6, "land_fraction": frac})
            y += dy
        x += dx
        col += 1
    gdf = gpd.GeoDataFrame(hexes, crs=land_m.crs)
    gdf.insert(0, "hex_id", [f"H{i:04d}" for i in range(len(gdf))])
    return gdf
