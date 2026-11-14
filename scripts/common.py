"""What the step scripts share (scripts/run_field.py runs them in order): paths, the rain versions, the twin's switches."""
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAIN_DIRS = {"corrected": "", "uncorrected": "rain_uncorrected", "dhm": "rain_dhm"}   # data/checks/<field>/<dir>/


def dhm_rain(rules):
    """Item 4b (rules.yaml gpm_series.dhm_scaling): DHM Bhaktapur's (index 1052) 1991-2020 monthly normals and the fit years,
    for --rain dhm."""
    n = pd.read_csv(REPO / "config" / "dhm_normals_1991_2020.csv", dtype={"month": str})
    n = n[(n["index"] == 1052) & (n["variable"] == "precip_mm") & (n["month"] != "annual")]
    if len(n) != 12:
        raise ValueError("config/dhm_normals_1991_2020.csv: Bhaktapur needs 12 monthly precip_mm normals")
    return {"normals_mm": {int(m): float(v) for m, v in zip(n["month"], n["value"])},
            "years": rules["gpm_series"]["dhm_scaling"]["years"]}


def add_switches(ap):
    """--bare-soil, --paddy-rainfed and --season-dates: each defaults to what rules.yaml says (pipeline/plans/twin_options.py)."""
    ap.add_argument("--bare-soil", choices=("rules", "kc", "fao56"), default="rules",
                    help="bare-soil evaporation: as rules.yaml bare_soil.apply says (default), the constant Kc, or FAO-56's "
                         "surface layer (build step 2a)")
    ap.add_argument("--paddy-rainfed", choices=("rules", "off", "proposal"), default="rules",
                    help="rain-fed rice: as rules.yaml paddy_rainfed.apply says (default), the plain bucket, or the "
                         "transplanting rule whatever apply says (item 4c)")
    ap.add_argument("--season-dates", choices=("rules", "calendar", "hls"), default="rules",
                    help="sowing of the farmer's plans: as rules.yaml season_dates.apply says (default), the calendar, or "
                         "the satellite's seasons (item 4a)")


def set_switches(rules, a):
    """Write the three switches of add_switches into rules as their 'force' keys (read by pipeline/plans/twin_options.py)."""
    rules.setdefault("season_dates", {})["force"] = a.season_dates
    rules["bare_soil"]["force"] = a.bare_soil
    rules.setdefault("paddy_rainfed", {})["force"] = a.paddy_rainfed


def switch_labels(rules, soil, season_dates=None):
    """The labels a run carries for the switches that are on (none while all are off): bare soil, season dates, paddy."""
    from pipeline.plans import twin_options as to
    out, bare, paddy = {}, to.bare_setting(rules, soil), to.paddy_rule(rules)
    if isinstance(bare, dict):                                 # build step 2a
        out["bare_soil"] = f"FAO-56 surface layer (eqs. 71-79; rules.yaml bare_soil): {bare}"
    if season_dates:                                           # item 4a
        out["season_dates"] = season_dates
    if paddy:                                                  # item 4c (owner's decision 2026-11-14)
        out["paddy_rainfed"] = ("rain-fed transplanting rule (rules.yaml paddy_rainfed; calendar-dated paddy seasons only): "
                                + str({k: v for k, v in paddy.items() if k not in ("force", "status")}))
    return out


def write_json(path, obj):
    """Write obj as indented JSON (one space, a final newline), making the folder first."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    return path
