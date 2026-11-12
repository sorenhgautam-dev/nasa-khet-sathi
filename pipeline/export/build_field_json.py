"""Build step 5 export: write the real replay into site/data/fields/<id>.json, changing nothing else.

    .venv/bin/python -m pipeline.export.build_field_json --field demo

Reads data/checks/<field>/replay.json (written by scripts/run_replay.py) and the field file as it stands
(still MOCK elsewhere until later steps). Refuses, and leaves the file untouched, when the replay was not
made with GPM rain (D6: POWER never stands in for the whole series; temporary station rain is for checks
only), when its years are not one unbroken run ending in 2025, when a year after the first misses a crop
of the rotation, or when a year has no event. Only complete years are exported: a first year that lacks a
crop of the rotation (2001 has rice only) is left out (owner's batch decisions item 14, 2026-11-12). It also
sets field.water_source from the replay ('unknown' while the field's water is not known: the site shows the
rain-fed and irrigated cases side by side, item 8). The result must validate against schema.json before it
is written.
"""
from collections import Counter
import argparse
import copy
import json
import sys
from pathlib import Path

from pipeline.export.validate import validate_field

REPO = Path(__file__).resolve().parents[2]
FIRST_YEAR, LAST_YEAR = 2001, 2025


def complete_years(years, rotation):
    """The years to export: an unbroken run ending in LAST_YEAR, each holding every crop of the rotation. Only
    the first year may be incomplete (its winter crop was sown before the weather record) and it is dropped."""
    got = [y["year"] for y in years]
    if not got or got[0] < FIRST_YEAR or got[-1] != LAST_YEAR or got != list(range(got[0], LAST_YEAR + 1)):
        gaps = sorted(set(range(FIRST_YEAR, LAST_YEAR + 1)) - set(got))
        raise ValueError(f"replay years must run unbroken to {LAST_YEAR}; got {got[:2]}...{got[-2:]}, missing {gaps}")
    want = Counter(rotation)
    bad = [y["year"] for y in years if Counter(y["crops"]) != want]
    if bad and bad[0] == got[0]:
        bad = bad[1:]
    if bad:
        raise ValueError(f"year(s) {bad} miss a crop of the rotation {list(rotation)}: only the first year may")
    return [y["year"] for y in years if Counter(y["crops"]) == want]


def apply_replay(doc, replay, plan_id="current"):
    """Return a copy of `doc` with replay[plan_id] = [{year, harvest, dry_days, event}, ...]."""
    if replay["labels"].get("rain_source") != "gpm":
        raise ValueError(f"replay rain is '{replay['labels'].get('rain_source')}', not GPM (D6): not exported")
    keep = complete_years(replay["years"], replay["labels"]["rotation"])
    if not replay.get("events"):
        raise ValueError("no events computed for this replay yet (rules.yaml events)")
    if "placeholder" in str(replay["labels"].get("rotation_source", "")).lower() \
            and "placeholder" not in doc["field"]["name"].lower():
        raise ValueError("the replay uses a placeholder rotation but the field file is not labelled placeholder")
    missing = [y for y in keep if str(y) not in replay["events"]]
    if missing:
        raise ValueError(f"no event for year(s) {missing}")
    irr = {y["year"]: y for y in replay.get("irrigated_years") or []}
    if sorted(irr) != [y["year"] for y in replay["years"]]:
        raise ValueError("the irrigated case must cover the same years as the field's own case (owner's go, 2026-11-12)")
    out = copy.deepcopy(doc)
    out["field"]["water_source"] = replay["labels"].get("water_source") or "unknown"
    out["replay"][plan_id] = [{"year": y["year"], "harvest": int(round(y["harvest"])), "dry_days": int(y["dry_days"]),
                               "event": replay["events"][str(y["year"])],
                               "irrigated": {"harvest": int(round(irr[y["year"]]["harvest"])),
                                             "dry_days": int(irr[y["year"]]["dry_days"])}}
                              for y in replay["years"] if y["year"] in keep]
    errs = validate_field(out)
    if errs:
        raise ValueError(f"field file would break the contract: {errs}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    src = REPO / "data" / "checks" / a.field / "replay.json"
    dest = REPO / "site" / "data" / "fields" / f"{a.field}.json"
    if not src.exists():
        print(f"NOT YET POSSIBLE: {src.relative_to(REPO)} does not exist (scripts/run_replay.py needs GPM rain). "
              f"{dest.relative_to(REPO)} left unchanged.")
        return 2
    replay = json.loads(src.read_text())
    try:
        doc = apply_replay(json.loads(dest.read_text()), replay["export"], plan_id="current")
    except ValueError as e:
        print(f"REFUSED: {e}. {dest.relative_to(REPO)} left unchanged.")
        return 1
    dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote replay.current ({len(doc['replay']['current'])} years) into {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
