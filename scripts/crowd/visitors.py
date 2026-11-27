"""Share of one ship's passengers that ends up in each hexagon (an explicit assumption).

For terminal t, hexagon i:
    share[t][i] = near_t * K_t(i) + (1 - near_t) * sum_j w_j * K_j(i)
K are exponential distance kernels (cut off at max_km), weighted by land area, summing to 1.
Per-terminal near_t / decay_km / max_km come from the terminals catalog when given
(e.g. a contained private destination keeps more passengers close), else from config.
With no visitor destinations in the catalog, near_t = 1 for every terminal.
"""

import numpy as np
import pandas as pd


def _kernel(centroids, point, land_km2, decay_km, max_km):
    d_km = centroids.distance(point).to_numpy() / 1000.0
    k = land_km2 * np.exp(-d_km / decay_km)
    k[d_km > max_km] = 0.0            # nobody beyond the cutoff (no thin "everywhere" cap)
    if k.sum() == 0:
        raise ValueError("No hexagons within the visitor cutoff of a point — check its coordinates.")
    return k / k.sum()


def _param(row, col, default):
    v = getattr(row, col, None)
    return float(default) if v is None or pd.isna(v) else float(v)


def shares(hexes_m, terminals_m, destinations_m, vcfg: dict):
    cents = hexes_m.geometry.centroid
    land = hexes_m["land_km2"].to_numpy()

    has_dest = len(destinations_m) > 0
    dest_mix = np.zeros(len(hexes_m))
    if has_dest:
        w = destinations_m["weight"].astype(float).to_numpy()
        w = w / w.sum()
        for wj, pt in zip(w, destinations_m.geometry):
            dest_mix += wj * _kernel(cents, pt, land, vcfg["destination_decay_km"],
                                     vcfg["destination_max_km"])

    per_terminal, near_flags, used = [], [], []
    for row in terminals_m.itertuples():
        near = _param(row, "share_near", vcfg["share_near_terminal"]) if has_dest else 1.0
        decay = _param(row, "decay_km", vcfg["terminal_decay_km"])
        cut = _param(row, "max_km", vcfg["terminal_max_km"])
        k = _kernel(cents, row.geometry, land, decay, cut)
        per_terminal.append(near * k + (1 - near) * dest_mix)
        near_flags.append(cents.distance(row.geometry).to_numpy() / 1000.0 <= vcfg["near_port_km"])
        used.append({"name": str(row.name), "share_near": near, "decay_km": decay, "max_km": cut})
    return per_terminal, near_flags, used
