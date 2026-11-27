"""Read the island outline and the point catalogs."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from shapely.ops import unary_union


def read_outline(outline_path, layer, clip_bbox):
    gdf = gpd.read_file(outline_path, layer=layer).to_crs(4326)
    land = unary_union([g for g in gdf.geometry if g is not None]).buffer(0)
    if clip_bbox:
        land = land.intersection(box(*clip_bbox))
    if land.is_empty:
        raise ValueError("Outline is empty after clipping — check outline.clip_bbox.")
    return gpd.GeoDataFrame(geometry=[land], crs=4326)


def read_points(catalog_path, required=("name", "lat", "lon"), allow_empty=False):
    df = pd.read_csv(catalog_path, encoding="utf-8-sig")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{catalog_path} is missing columns {missing}")
    if df.empty:
        if allow_empty:
            return gpd.GeoDataFrame(df, geometry=[], crs=4326)
        raise ValueError(f"{catalog_path} has no rows.")
    blank = df[df["lat"].isna() | df["lon"].isna()]
    if not blank.empty:
        raise ValueError(
            f"{catalog_path}: fill lat/lon for {blank['name'].tolist()} before running.")
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=4326)
