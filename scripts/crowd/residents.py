"""Residents per hexagon: from a population raster if given, else by land area."""

import numpy as np


def allocate(hexes, total: int, raster_path=None, scale_to_total=True):
    """Return (residents per hexagon, mode, raster_total).

    The raster (if any) decides WHERE people live. With scale_to_total the counts are
    rescaled so they sum to `total` (e.g. an official figure); otherwise the raster's own
    total is kept.
    """
    if raster_path is None:
        weights = hexes["land_km2"].to_numpy()
        return weights / weights.sum() * total, "land_area_placeholder", None
    weights = _raster_sums(hexes, raster_path)
    raster_total = float(weights.sum())
    if raster_total <= 0:
        raise ValueError("Population raster gives zero people inside the island hexagons.")
    if scale_to_total:
        return weights / raster_total * total, "population_raster", raster_total
    return weights, "population_raster", raster_total


def _raster_sums(hexes, raster_path):
    import rasterio
    from rasterio.mask import mask

    out = []
    with rasterio.open(raster_path) as src:
        geoms = hexes.to_crs(src.crs).geometry
        nodata = src.nodata
        for g in geoms:
            try:
                arr, _ = mask(src, [g], crop=True, filled=False)
            except ValueError:            # hexagon outside the raster
                out.append(0.0)
                continue
            vals = arr.compressed().astype("float64")
            if nodata is not None:
                vals = vals[vals != nodata]
            out.append(float(vals[vals > 0].sum()))
    return np.asarray(out)
