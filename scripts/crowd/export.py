"""Write the web data file (a JS file, so the page also works opened from disk),
plus GPKG and CSV copies of the hexagons."""

import json


def _round_coords(geom, nd=5):
    gj = geom.__geo_interface__
    def r(c):
        return [round(c[0], nd), round(c[1], nd)]
    return {"type": "Polygon", "coordinates": [[r(c) for c in ring] for ring in gj["coordinates"]]}


def _round_any(obj, nd=5):
    """Round every coordinate in a GeoJSON geometry dict."""
    def walk(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [walk(x) for x in c]
    return {"type": obj["type"], "coordinates": walk(obj["coordinates"])}


def web_data(cfg, hexes_wgs, land_wgs, terminals_wgs, per_terminal, near_flags,
             res_mode, extra, out_path, json_path=None):
    from shapely.affinity import scale

    k = cfg["hexgrid"].get("display_scale", 1.0)   # small gaps between towers
    features = []
    for i, row in enumerate(hexes_wgs.itertuples()):
        features.append({
            "type": "Feature",
            "geometry": _round_coords(scale(row.geometry, k, k, origin="centroid")),
            "properties": {
                "id": row.hex_id,
                "res": round(float(row.residents), 2),
                "land_km2": round(float(row.land_km2), 5),
                "share": [round(float(s[i]), 7) for s in per_terminal],
                "near": [bool(n[i]) for n in near_flags],
            },
        })
    land_geom = json.loads(json.dumps(land_wgs.geometry.iloc[0].__geo_interface__))
    land_geom = _round_any(land_geom)
    payload = {
        "title": cfg["project"]["title"],
        "subtitle": cfg["project"]["subtitle"],
        "colours": cfg["colours"],
        "ships": cfg["ships"],
        "residents_total": cfg["residents"].get("total_used", cfg["residents"]["total"]),
        "residents_note": cfg["residents"].get("raster_note", ""),
        "residents_raster_total": cfg["residents"].get("raster_total"),
        "residents_mode": res_mode,
        "visitors": cfg["visitors"],
        **extra,
        "notes": [cfg["residents"]["source_note"], cfg["cruises"]["source_note"],
                  cfg["ships"]["source_note"]],
        "scope_note": cfg["cruises"].get("scope_note", ""),
        "economy": cfg.get("economy"),
        "terminals": [{"name": str(r.name), "lon": float(r.geometry.x), "lat": float(r.geometry.y)}
                      for r in terminals_wgs.itertuples()],
        "hexes": {"type": "FeatureCollection", "features": features},
        "land": {"type": "Feature", "geometry": land_geom, "properties": {}},
        "bounds": [round(float(v), 5) for v in land_wgs.total_bounds],
        "cell_size_m": cfg["hexgrid"]["cell_size_m"],
        "tanaka": cfg["tanaka"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # JSON is valid JS; escape "</" so the data can never close a script tag.
    text = text.replace("</", "<\\/")
    out_path.write_text(f"window.CROWD_DATA = {text};\n", encoding="utf-8")


def monthly_table(monthly, terminals_wgs, csv):
    out = monthly.copy()
    out["terminal_name"] = out["terminal"].map(dict(enumerate(terminals_wgs["name"])))
    csv.parent.mkdir(parents=True, exist_ok=True)
    out[["year", "month", "terminal_name", "calls", "passengers"]].to_csv(
        csv, index=False, encoding="utf-8-sig")


def tables(hexes_wgs, per_terminal, near_flags, terminals_wgs, gpkg, csv):
    out = hexes_wgs.copy()
    for t, (s, n) in enumerate(zip(per_terminal, near_flags), start=1):
        out[f"share_terminal_{t}"] = s
        out[f"near_terminal_{t}"] = n
    gpkg.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(gpkg, layer="hexes", driver="GPKG")
    out.drop(columns="geometry").to_csv(csv, index=False, encoding="utf-8-sig")
