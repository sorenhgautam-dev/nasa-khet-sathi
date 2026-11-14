"""What the step scripts share (scripts/run_field.py runs them in order): paths, the rain versions, the twin's switches."""
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAIN_DIRS = {"corrected": "", "uncorrected": "rain_uncorrected", "dhm": "rain_dhm",    # data/checks/<field>/<dir>/
             "untuned": "rain_untuned"}
SOIL_DIRS = {"map": "", "measured": "soil_measured"}           # under the rain folder (rules.yaml field_capacity_measured)


def dhm_rain(rules):
    """Item 4b (rules.yaml gpm_series.dhm_scaling): DHM Bhaktapur's (index 1052) 1991-2020 monthly normals and the fit years,
    for --rain dhm."""
    n = pd.read_csv(REPO / "config" / "dhm_normals_1991_2020.csv", dtype={"month": str})
    n = n[(n["index"] == 1052) & (n["variable"] == "precip_mm") & (n["month"] != "annual")]
    if len(n) != 12:
        raise ValueError("config/dhm_normals_1991_2020.csv: Bhaktapur needs 12 monthly precip_mm normals")
    return {"normals_mm": {int(m): float(v) for m, v in zip(n["month"], n["value"])},
            "years": rules["gpm_series"]["dhm_scaling"]["years"]}


def rain_kw(rules, version, field_id):
    """with_rain's extra arguments for a rain version: DHM's normals for 'dhm'; for 'untuned', the gauge factors when
    rules.yaml gpm_series.gauge_calibration is on for this field (else None: the central rain is not calibrated)."""
    if version == "dhm":
        return {"dhm": dhm_rain(rules)}
    if version == "untuned":
        cal = rules["gpm_series"].get("gauge_calibration") or {}
        return {"gauge": cal["factors"] if cal.get("apply") and field_id in cal.get("fields", []) else None}
    return {}


def add_switches(ap):
    """--bare-soil, --paddy-rainfed, --season-dates, --paddy-losses and --soil: each defaults to what rules.yaml says
    (pipeline/plans/twin_options.py; --soil defaults to the map)."""
    ap.add_argument("--bare-soil", choices=("rules", "kc", "fao56"), default="rules",
                    help="bare-soil evaporation: as rules.yaml bare_soil.apply says (default), the constant Kc, or FAO-56's "
                         "surface layer (build step 2a)")
    ap.add_argument("--paddy-rainfed", choices=("rules", "off", "proposal"), default="rules",
                    help="rain-fed rice: as rules.yaml paddy_rainfed.apply says (default), the plain bucket, or the "
                         "transplanting rule whatever apply says (item 4c)")
    ap.add_argument("--season-dates", choices=("rules", "calendar", "hls"), default="rules",
                    help="sowing of the farmer's plans: as rules.yaml season_dates.apply says (default), the calendar, or "
                         "the satellite's seasons (item 4a)")
    ap.add_argument("--paddy-losses", choices=("rules", "off", "on"), default="rules",
                    help="a paddy's seepage and percolation and its puddling water: as rules.yaml paddy_losses.apply says "
                         "(default), or off, or on (owner's item 3)")
    ap.add_argument("--soil", choices=tuple(SOIL_DIRS), default="map",
                    help="field capacity: the soil map's (default), or the field team's measured one, written to "
                         "<rain folder>/soil_measured/ (rules.yaml field_capacity_measured; nothing runs without its "
                         "switch and data/field_visit/<field>/field_capacity.csv)")


def set_switches(rules, a):
    """Write the three switches of add_switches into rules as their 'force' keys (read by pipeline/plans/twin_options.py)."""
    rules.setdefault("season_dates", {})["force"] = a.season_dates
    rules["bare_soil"]["force"] = a.bare_soil
    rules.setdefault("paddy_rainfed", {})["force"] = a.paddy_rainfed
    rules.setdefault("paddy_losses", {})["force"] = a.paddy_losses


def soil_for(version, rules, field_id, soil, data=REPO / "data"):
    """The twin's soil table for --soil: the map's, or the field team's measured field capacity with the map's wilting
    point (owner's item 4; twin_options.soil_versions); None when 'measured' has no switch or no file (nothing to run)."""
    if version == "map":
        return soil
    from pipeline.fetch.field_visit import load_field_capacity
    from pipeline.plans import twin_options as to
    return to.soil_versions(rules, soil, load_field_capacity(field_id, data)).get("measured")


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
    if to.paddy_losses(rules):                                 # owner's item 3
        out["paddy_losses"] = ("a paddy's seepage and percolation on its wet days and its puddling water (rules.yaml "
                               f"paddy_losses): {to.paddy_losses(rules)}; the water score leaves out the irrigation that "
                               "replaces them (irrigation_losses_mm)")
    return out


def write_json(path, obj):
    """Write obj as indented JSON (one space, a final newline), making the folder first."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    return path
