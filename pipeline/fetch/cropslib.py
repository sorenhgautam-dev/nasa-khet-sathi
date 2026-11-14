"""Load config/crops.json (the crop library). Every parameter carries a source in `sources`; a parameter
with no published value is null and its source says TODO-VERIFY (tests/test_crops_lib.py).

load_crops(field=...) gives the library as the field's country profile says (config/countries/; owner's item 3,
2026-11-14): a Nepal field keeps crops.json's own windows (the same object as load_crops()); a field with no profile takes
its zone's windows from the FAO Crop Calendar (pipeline/fetch/cropcalendar.py, data/clean/<field>/crop_calendar.json)."""
import json
from pathlib import Path

CROPS_PATH = Path(__file__).resolve().parents[2] / "config" / "crops.json"
PARAMS = ["family", "legume", "stages_days", "kc", "zr_m", "p", "ky", "calendar"]


def load_crops(path=CROPS_PATH, field=None, data_dir=None):
    data = json.loads(Path(path).read_text())
    if field is None:
        return data["crops"]
    from pipeline.fetch import cropcalendar as cc
    from pipeline.fetch.profiles import profile_for
    windows = profile_for(field)["crop_calendar"]["windows"]
    if windows == "crops.json":
        return data["crops"]
    if windows != "fao_api":
        raise ValueError(f"profile crop_calendar.windows {windows!r}: expected 'crops.json' or 'fao_api'")
    zp = cc.zone_path(field["id"], *([data_dir] if data_dir else []))
    if not zp.exists():
        raise FileNotFoundError(f"{zp} is missing: run python -m pipeline.fetch.cropcalendar --field {field['id']}")
    return cc.apply_zone(data["crops"], json.loads(zp.read_text()))
