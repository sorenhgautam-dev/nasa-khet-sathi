"""Load config/crops.json (the crop library). Every parameter carries a source in `sources`; a parameter
with no published value is null and its source says TODO-VERIFY (tests/test_crops_lib.py)."""
import json
from pathlib import Path

CROPS_PATH = Path(__file__).resolve().parents[2] / "config" / "crops.json"
PARAMS = ["family", "legume", "stages_days", "kc", "zr_m", "p", "ky", "calendar"]


def load_crops(path=CROPS_PATH):
    data = json.loads(Path(path).read_text())
    return data["crops"]
