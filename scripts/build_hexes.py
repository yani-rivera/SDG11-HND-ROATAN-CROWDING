"""Build the hexagon data for the Roatán crowding interactive.

Usage (from the project root):
    python scripts/build_hexes.py --config config/config.yaml
Then open docs/index.html in a browser.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crowd import cruises, export, grid, hexgrid, inputs, provenance, residents, visitors  # noqa: E402
from crowd.config import load_config, path  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    args = ap.parse_args(argv)
    cfg = load_config(Path(args.config))
    cat, oc = cfg["catalogs"], cfg["outputs"]

    # 1. inputs
    o = cfg["outline"]
    land = inputs.read_outline(path(cfg, o["path"]), o.get("layer"), o.get("clip_bbox"))
    terminals = inputs.read_points(path(cfg, cat["terminals"]),
                                   required=("name", "source_port", "lat", "lon"))
    dests = inputs.read_points(path(cfg, cat["destinations"]),
                               required=("name", "lat", "lon", "weight"), allow_empty=True)

    # 2. cruise calls per terminal and month
    ccfg = cfg["cruises"]
    calls, monthly, report, ship_median, biggest = cruises.load(
        path(cfg, ccfg["path"]), ccfg, terminals, path(cfg, cat["months"]))
    months = cruises.web_months(monthly, len(terminals), path(cfg, cat["months"]))
    latest = max(ship_median)
    if str(cfg["ships"]["default_capacity"]).lower() == "auto":
        cfg["ships"]["default_capacity"] = ship_median[latest]
    print(f"Cruise data: {len(calls)} calls, {len(months)} months; "
          f"median passengers per call {latest}: {ship_median[latest]}")
    if report["rows_exact_duplicates_kept"]:
        print(f"Note: {report['rows_exact_duplicates_kept']} rows are exact duplicates (kept).")

    # 3. hexagons, residents, visitor spread
    crs_m = land.estimate_utm_crs()
    land_m = land.to_crs(crs_m)
    hexes_m = hexgrid.build(land_m, cfg["hexgrid"]["cell_size_m"],
                            cfg["hexgrid"]["min_land_fraction"])
    print(f"{len(hexes_m)} hexagons of {cfg['hexgrid']['cell_size_m']} m")

    rcfg = cfg["residents"]
    raster = path(cfg, rcfg["raster"]) if rcfg.get("raster") else None
    scale = bool(rcfg.get("scale_to_total", True))
    hexes_m["residents"], res_mode, raster_total = residents.allocate(
        hexes_m, rcfg["total"], raster, scale)
    res_total_used = float(hexes_m["residents"].sum())
    cfg["residents"]["total_used"] = round(res_total_used)
    cfg["residents"]["raster_total"] = round(raster_total) if raster_total else None
    if res_mode == "land_area_placeholder":
        print("Note: no population raster set — residents spread by land area (placeholder).")
    else:
        print(f"Residents placed with the raster: raster total {raster_total:,.0f}; "
              f"{'scaled to' if scale else 'kept at'} {res_total_used:,.0f}")

    per_t, near_f, t_params = visitors.shares(hexes_m, terminals.to_crs(crs_m),
                                              dests.to_crs(crs_m), cfg["visitors"])

    # 4. outputs
    hexes_wgs = hexes_m.to_crs(4326)
    tol = o.get("display_simplify_m", 0)     # lighter coastline for the page only
    land_web = land_m.simplify(tol).to_crs(4326) if tol else land
    g = grid.build(hexes_wgs, cfg["tanaka"]["grid_cell_m"])
    print(f"Density grid: {g['width']} x {g['height']} cells of {cfg['tanaka']['grid_cell_m']} m")
    extra_web = {"months": months, "ship_median": ship_median, "biggest_call": biggest,
                 "terminal_params": t_params,
                 "grid": {**{k: g[k] for k in ("width", "height", "west", "north", "dlon", "dlat")},
                          "idx": g["idx"].tolist()}}
    export.web_data(cfg, hexes_wgs, land_web, terminals, per_t, near_f, res_mode, extra_web,
                    path(cfg, oc["web_data"]), path(cfg, oc["data_json"]))
    export.tables(hexes_wgs, per_t, near_f, terminals, path(cfg, oc["gpkg"]), path(cfg, oc["csv"]))
    export.monthly_table(monthly, terminals, path(cfg, oc["monthly_csv"]))

    ins = {"outline": path(cfg, o["path"]), "terminals": path(cfg, cat["terminals"]),
           "destinations": path(cfg, cat["destinations"]), "months": path(cfg, cat["months"]),
           "cruises": path(cfg, ccfg["path"])}
    if raster:
        ins["population_raster"] = raster
    provenance.write(cfg, ins, {"hexagons": len(hexes_m), "metric_crs": str(crs_m),
                                "residents_mode": res_mode, "terminal_params": t_params,
                                "residents_raster_total": cfg["residents"]["raster_total"],
                                "residents_total_used": cfg["residents"]["total_used"],
                                "cruise_report": report, "ship_median_by_year": ship_median},
                     path(cfg, oc["provenance"]))
    print(f"Done: {path(cfg, oc['web_data'])}")


if __name__ == "__main__":
    main()
