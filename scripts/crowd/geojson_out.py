"""GeoJSON exports (RFC 7946, WGS84) for use in QGIS or elsewhere.

- hexes.geojson      residents, visitor shares, visitors for 1–3 ships and for every month
- terminals.geojson  terminal points with their spread settings
- contours_<panel>.geojson  Tanaka contour lines per poster panel (level + light shade 0–1)
"""

import json
import re

import numpy as np


def _write(fc, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def hexes(data, path, visitors_for, display_scale=1.0):
    from shapely.affinity import scale
    from shapely.geometry import mapping, shape

    feats = data["hexes"]["features"]
    kfac = 1.0 / display_scale         # undo the visual gap: full hexagon cells for GIS use
    ships_cols = {f"vis_{s}_ship{'s' if s > 1 else ''}": visitors_for(data, s, None)
                  for s in range(1, data["ships"]["max_ships"] + 1)}
    month_cols = {f"vis_{m['year']}_{m['month']:02d}": visitors_for(data, 0, m) for m in data["months"]}
    out = []
    for i, f in enumerate(feats):
        p = f["properties"]
        props = {"hex_id": p["id"], "residents": round(p["res"], 1), "land_km2": p["land_km2"]}
        for t, s in enumerate(p["share"]):
            props[f"share_terminal_{t + 1}"] = s
        for k, v in {**ships_cols, **month_cols}.items():
            props[k] = round(float(v[i]), 1)
        geom = scale(shape(f["geometry"]), kfac, kfac, origin="centroid")
        out.append({"type": "Feature", "geometry": mapping(geom), "properties": props})
    _write({"type": "FeatureCollection",
            "metadata": {"ship_capacity": data["ships"]["default_capacity"],
                         "residents_mode": data["residents_mode"],
                         "note": "vis_* = cruise visitors per hexagon (cruise only; no air or ferry). "
                                 "Month columns = average day (monthly passengers / days)."},
            "features": out}, path)


def terminals(data, path):
    params = {t["name"]: t for t in data.get("terminal_params", [])}
    out = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [t["lon"], t["lat"]]},
            "properties": {"name": t["name"], **{k: v for k, v in params.get(t["name"], {}).items()
                                                 if k != "name"}}}
           for t in data["terminals"]]
    _write({"type": "FeatureCollection", "features": out}, path)


def contours(data, panel_label, tot, path):
    """Contour lines of the density surface, split per segment run with a light shade."""
    import math

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g, tk = data["grid"], data["tanaka"]
    xs = g["west"] + (np.arange(g["width"]) + 0.5) * g["dlon"]
    ys = g["north"] - (np.arange(g["height"]) + 0.5) * g["dlat"]
    fig, ax = plt.subplots()
    cs = ax.contour(xs, ys, tot, levels=tk["thresholds_per_km2"])
    plt.close(fig)
    az = math.radians(tk["light_azimuth_deg"])
    LX, LY = math.sin(az), math.cos(az)

    def samp(x, y):
        j = int(np.clip(round((x - g["west"]) / g["dlon"] - 0.5), 0, g["width"] - 1))
        i = int(np.clip(round((g["north"] - y) / g["dlat"] - 0.5), 0, g["height"] - 1))
        return tot[i, j]

    out = []
    for level, segs in zip(cs.levels, cs.allsegs):
        for line in segs:
            for (x0, y0), (x1, y1) in zip(line[:-1], line[1:]):
                dx, dy = (x1 - x0) / g["dlon"], (y1 - y0) / g["dlat"]
                ln = math.hypot(dx, dy)
                if ln == 0:
                    continue
                nx, ny = dy / ln, -dx / ln
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                if samp(mx + nx * g["dlon"] * 0.5, my + ny * g["dlat"] * 0.5) > \
                   samp(mx - nx * g["dlon"] * 0.5, my - ny * g["dlat"] * 0.5):
                    nx, ny = -nx, -ny
                shade = round((nx * LX + ny * LY + 1) / 2, 3)
                out.append({"type": "Feature",
                            "geometry": {"type": "LineString",
                                         "coordinates": [[round(x0, 6), round(y0, 6)],
                                                         [round(x1, 6), round(y1, 6)]]},
                            "properties": {"level_per_km2": float(level), "shade": shade}})
    _write({"type": "FeatureCollection",
            "metadata": {"panel": panel_label,
                         "note": "shade 1 = edge facing the light (NW), 0 = facing away"},
            "features": out}, path)


def all_outputs(data, pcfg, out_dir, visitors_for, surfaces, display_scale=1.0):
    hexes(data, out_dir / "hexes.geojson", visitors_for, display_scale)
    terminals(data, out_dir / "terminals.geojson")
    months = {f"{m['year']}-{m['month']:02d}": m for m in data["months"]}
    for p in pcfg["panels"]:
        m = months.get(p["month"]) if p.get("month") else None
        vis = visitors_for(data, p.get("ships", 0), m)
        tot, _ = surfaces(data, vis)
        contours(data, p["label"], tot, out_dir / f"contours_{_slug(p['label'])}.geojson")
