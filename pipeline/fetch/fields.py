"""Load config/fields/<id>.yaml. Unknown values stay null; nothing here fills them in."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO / "config" / "fields"
REQUIRED = ["id", "lat", "lon"]


class FieldConfigError(ValueError):
    pass


def load_field(field_id, config_dir=CONFIG_DIR):
    path = Path(config_dir) / f"{field_id}.yaml"
    if not path.is_file():
        raise FieldConfigError(f"no config for field '{field_id}' at {path}")
    cfg = yaml.safe_load(path.read_text()) or {}
    for key in REQUIRED:
        if cfg.get(key) is None:
            raise FieldConfigError(f"{path.name}: '{key}' is required")
    if cfg["id"] != field_id:
        raise FieldConfigError(f"{path.name}: id '{cfg['id']}' must match the file name")
    if not -90 <= float(cfg["lat"]) <= 90:
        raise FieldConfigError(f"{path.name}: lat {cfg['lat']} out of range")
    if not -180 <= float(cfg["lon"]) <= 180:
        raise FieldConfigError(f"{path.name}: lon {cfg['lon']} out of range")
    return cfg
