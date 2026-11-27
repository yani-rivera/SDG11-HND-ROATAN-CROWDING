"""Config loading and project-relative paths."""

from pathlib import Path

import yaml


def load_config(config_path) -> dict:
    config_path = Path(config_path).resolve()
    with config_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["_root"] = config_path.parent.parent
    cfg["_config_path"] = config_path
    return cfg


def path(cfg: dict, relative: str) -> Path:
    return (cfg["_root"] / Path(relative)).resolve()
