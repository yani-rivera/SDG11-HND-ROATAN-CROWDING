"""Provenance record: script version, config and input hashes, package versions."""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata

from . import __version__

PACKAGES = ["geopandas", "shapely", "pyproj", "pyogrio", "rasterio", "numpy", "pandas", "pyyaml"]


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write(cfg, inputs: dict, extra: dict, out_path):
    def ver(p):
        try:
            return metadata.version(p)
        except metadata.PackageNotFoundError:
            return None
    rec = {
        "project": cfg["project"]["id"],
        "script": "scripts/build_hexes.py",
        "script_version": __version__,
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_file": str(cfg["_config_path"].relative_to(cfg["_root"])),
        "config_sha256": sha256(cfg["_config_path"]),
        "inputs": {k: {"path": str(p.relative_to(cfg["_root"])), "sha256": sha256(p)}
                   for k, p in inputs.items()},
        "packages": {p: ver(p) for p in PACKAGES},
        **extra,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
