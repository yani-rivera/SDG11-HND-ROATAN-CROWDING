"""Static Tanaka posters and GeoJSON exports from the data built by build_hexes.py.

Usage (from the project root, after build_hexes.py):
    python scripts/make_posters.py --config config/config.yaml
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crowd import geojson_out, provenance, tanaka  # noqa: E402
from crowd.config import load_config, path  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    args = ap.parse_args(argv)
    cfg = load_config(Path(args.config))
    data_path = path(cfg, cfg["outputs"]["data_json"])
    if not data_path.exists():
        raise FileNotFoundError(f"{data_path} not found — run scripts/build_hexes.py first.")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    pcfg = cfg["posters"]
    out = path(cfg, pcfg["out_dir"]) / "roatan_tanaka_panels.png"
    tanaka.poster(data, pcfg, out)
    gj_dir = path(cfg, cfg["outputs"]["geojson_dir"])
    geojson_out.all_outputs(data, pcfg, gj_dir, tanaka.visitors_for, tanaka.surfaces,
                            cfg["hexgrid"].get("display_scale", 1.0))
    print(f"GeoJSON: {gj_dir}")
    provenance.write(cfg, {"crowd_data": data_path}, {"script": "scripts/make_posters.py",
                     "poster": str(out.relative_to(cfg["_root"]))},
                     path(cfg, pcfg["out_dir"]) / "provenance_posters.json")
    print(f"Done: {out}")


if __name__ == "__main__":
    main()
