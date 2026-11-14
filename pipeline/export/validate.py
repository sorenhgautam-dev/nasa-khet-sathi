"""Validate exports against the output contract.

    python -m pipeline.export.validate                # checks site/data/
    python -m pipeline.export.validate --data-dir DIR
    python -m pipeline.export.validate --final        # the freeze check: also fails while anything is MOCK

Schema checks come from schema.json / index_schema.json. The checks below cover what JSON Schema
cannot say: order, uniqueness, cross-references and matching array lengths.
"""
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_schema(name):
    return json.loads((HERE / name).read_text())


def _schema_errors(doc, schema_name):
    v = Draft202012Validator(load_schema(schema_name))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in v.iter_errors(doc)]


def _dupes(values):
    seen, dupes = set(), set()
    for v in values:
        (dupes if v in seen else seen).add(v)
    return sorted(dupes)


def _final_errors(doc):
    """What a file ready to freeze must also meet (REVIEW_2 M13; --final). Not part of the everyday check, because
    the mock that the site was built with does not meet it: no made-up (MOCK) numbers left, three different
    rotations, each plan's harvest score the mean of its replay (within 1 point of rounding). Blocks named in `mock`
    are allowed: they hold no numbers and the site says 'not ready yet' (owner's answer 2, 2026-11-13)."""
    errors = []
    if "MOCK" in json.dumps(doc, ensure_ascii=False):
        errors.append("final: the file still contains MOCK data")
    crops = {p["id"]: tuple(c["crop"] for c in p["crops"]) for p in doc["plans"]}
    ids = list(crops)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if crops[a] == crops[b]:
                errors.append(f"final: plans {a} and {b} grow the same crops (at least three rotations are asked for)")
    for p in doc["plans"]:
        years = doc["replay"].get(p["id"], [])
        if years:
            mean = sum(y["harvest"] for y in years) / len(years)
            if abs(p["score"]["harvest"] - mean) > 1.0:
                errors.append(f"final: plans/{p['id']}: score.harvest {p['score']['harvest']} is not the mean of its "
                              f"replay ({mean:.1f})")
    return errors


def validate_field(doc, final=False):
    """Return a list of problems; empty means the field file meets the contract. final=True adds the freeze checks."""
    errors = _schema_errors(doc, "schema.json")
    if errors:
        return errors
    section_ids = [s["id"] for s in doc["field"]["sections"]]
    if d := _dupes(section_ids):
        errors.append(f"field/sections: duplicate ids {d}")
    if [m["m"] for m in doc["diary"]["months"]] != MONTHS:
        errors.append("diary/months: must run Jan to Dec in order")
    plan_ids = [p["id"] for p in doc["plans"]]
    if d := _dupes(plan_ids):
        errors.append(f"plans: duplicate ids {d}")
    for p in doc["plans"]:
        if len(p["tips_ne"]) != len(p["tips"]):
            errors.append(f"plans/{p['id']}: tips_ne needs one Nepali tip per English tip "
                          f"({len(p['tips_ne'])} vs {len(p['tips'])})")
    for pid in plan_ids:                    # REVIEW_2 M13: a plan card with no years behind it
        if pid not in doc["replay"]:
            errors.append(f"plans/{pid}: no replay for this plan")
    for key, years in doc["replay"].items():
        if key not in plan_ids:
            errors.append(f"replay/{key}: no plan with this id")
        if d := _dupes([y["year"] for y in years]):
            errors.append(f"replay/{key}: duplicate years {d}")
        elif [y["year"] for y in years] != list(range(years[0]["year"], years[0]["year"] + len(years))):
            errors.append(f"replay/{key}: years must run year by year, in order, with no gap")
        for y in years:                     # owner's decisions 1 and 4b: the second rain version only where it differs
            u = y.get("dhm_rain")
            if u and all(u.get(k) == y.get(k) for k in ("harvest", "dry_days", "event", "irrigated")):
                errors.append(f"replay/{key}/{y['year']}: dhm_rain is given but changes nothing")
    # owner's answer 9 to REVIEW_2 (2026-11-13): one weather event per year for the field, the same on every plan
    by_year = {}
    for key, years in doc["replay"].items():
        for y in years:
            for tag, row in (("", y), (" (DHM-scaled rain)", y.get("dhm_rain"))):
                if row and "event_season" in row and row["event"] != "drought":
                    errors.append(f"replay/{key}/{y['year']}{tag}: event_season is only for a drought")
            by_year.setdefault(y["year"], set()).add((y["event"], y.get("event_season")))
    differ = sorted(y for y, v in by_year.items() if len(v) > 1)
    if differ:
        errors.append(f"replay: a year must carry the same event (and season) on every plan; they differ in {differ}")
    for p in doc["plans"]:
        u = p.get("score_dhm_rain")
        if u and u == p["score"]:
            errors.append(f"plans/{p['id']}: score_dhm_rain is given but changes nothing")
    # owner's answer 2 to REVIEW_2 (2026-11-13): a block that is not computed yet is named in `mock` and holds no numbers
    not_ready = doc.get("mock", [])
    empty_sections = [s["id"] for s in doc["field"]["sections"]
                      if s["wetness"] is None and s["temp"] is None and s["status"] == "grey" and s["sure"] == 0]
    if "field.sections" in not_ready:
        if len(empty_sections) != len(doc["field"]["sections"]):
            errors.append("field.sections is named in `mock`, so every section must be grey with null wetness and temp and sure 0")
    elif any(s["wetness"] is None for s in doc["field"]["sections"]):
        errors.append("field.sections: a section without wetness needs 'field.sections' in `mock`")
    if ("future" in not_ready) != (doc["future"] is None):
        errors.append("future: it is null exactly when 'future' is named in `mock`")
    # build step 9 (2026-11-14): the outlook block, and each plan's and each current option's own series
    series_list = []
    if doc["future"] is not None:
        series_list += [(f"future/{k}", doc["future"][k]) for k in ("nothing_changes", "with_plan")]
    for p in doc["plans"]:
        series_list += [(f"plans/{p['id']}/{k}", p[k]) for k in ("future", "future_dhm_rain") if k in p]
    for o in (doc.get("current_options") or {}).get("options", []):
        series_list += [(f"current_options/{o['id']}/{k}", o[k]) for k in ("future", "future_dhm_rain") if k in o]
    for name, s in series_list:
        if doc["future"] is None:
            errors.append(f"{name}: a 2040 outlook needs the future block (future.years)")
            continue
        n = len(doc["future"]["years"])
        for key in ("harvest", "harvest_low", "harvest_high"):
            if len(s[key]) != n:
                errors.append(f"{name}/{key}: needs {n} values, one per year")
        for i, (lo, mid, hi) in enumerate(zip(s["harvest_low"], s["harvest"], s["harvest_high"])):
            if not lo <= mid <= hi:
                errors.append(f"{name}: year {i} needs harvest_low <= harvest <= harvest_high")
    sd = doc["method"]["season_detection"]
    by_id = {m["id"]: m for m in sd["methods"]}
    if sorted(by_id) != ["changepoint", "detective", "threshold"]:
        errors.append("method/season_detection/methods: needs threshold, changepoint and detective once each")
    else:
        for m in sd["methods"]:
            if sorted(y["year"] for y in m["by_year"]) != sorted(sd["held_out_years"]):
                errors.append(f"method/season_detection/{m['id']}: by_year must cover exactly the held-out years")
        base, ch = by_id["threshold"]["score"], sd["chosen"]
        best = max(by_id, key=lambda k: by_id[k]["score"])
        want = best if best == "threshold" or by_id[best]["score"] - base >= sd["margin"] - 1e-9 else "threshold"
        if ch != want:
            errors.append(f"method/season_detection/chosen: the rule fixed in advance picks '{want}', not '{ch}'")
        if by_id["detective"]["si"] is not True or by_id["threshold"]["si"] or by_id["changepoint"]["si"]:
            errors.append("method/season_detection: only the detective is the SI method")
    dy = doc["diary"]          # owner, 2026-11-14: the shift sits inside its own range
    if dy.get("shift_days") is not None and dy.get("shift_days_low") is not None and dy.get("shift_days_high") is not None:
        if not dy["shift_days_low"] <= dy["shift_days"] <= dy["shift_days_high"]:
            errors.append("diary/shift_days: needs shift_days_low <= shift_days <= shift_days_high")
    gw = doc["diary"]["groundwater"]
    if gw["direction"] == "falling" and gw["trend_cm_per_year"] >= 0:
        errors.append("diary/groundwater: 'falling' needs a negative trend")
    if gw["direction"] == "rising" and gw["trend_cm_per_year"] <= 0:
        errors.append("diary/groundwater: 'rising' needs a positive trend")
    errors += _current_options_errors(doc)
    if final:
        errors += _final_errors(doc)
    return errors


def _current_options_errors(doc):
    """Owner's answer 6 to REVIEW_2 (2026-11-13): the current plan once for each rotation the farmer may confirm."""
    co = doc.get("current_options")
    if not co:
        return []
    errors = []
    opts = {o["id"]: o for o in co["options"]}
    if len(opts) != len(co["options"]):
        errors.append("current_options: duplicate option ids")
    if co["default"] not in opts:
        return errors + [f"current_options: default '{co['default']}' is not one of the options {sorted(opts)}"]
    cur = next((p for p in doc["plans"] if p["id"] == "current"), None)
    d = opts[co["default"]]
    if cur is None or any(d[k] != cur[k] for k in ("crops", "score", "tabs", "tips", "tabs_ne", "tips_ne")) \
            or d.get("score_dhm_rain") != cur.get("score_dhm_rain") or d["replay"] != doc["replay"].get("current"):
        errors.append("current_options: the default option must be what plans (id current) and replay.current show")
    years = [y["year"] for y in doc["replay"].get("current", [])]
    suggested = sorted(p["id"] for p in doc["plans"] if p["id"] != "current")
    crops_seen = {}
    for o in co["options"]:
        if [y["year"] for y in o["replay"]] != years:
            errors.append(f"current_options/{o['id']}: its replay must cover the same years as replay.current")
        if sorted(o["compared"]) != suggested:
            errors.append(f"current_options/{o['id']}: compared must hold exactly the suggested plans {suggested}")
        if len(o["tips_ne"]) != len(o["tips"]):
            errors.append(f"current_options/{o['id']}: tips_ne needs one Nepali tip per English tip")
        key = tuple(c["crop"] for c in o["crops"])
        if key in crops_seen:
            errors.append(f"current_options: {o['id']} and {crops_seen[key]} grow the same crops")
        crops_seen[key] = o["id"]
        ev = {y["year"]: (y["event"], y.get("event_season")) for y in o["replay"]}
        ref = {y["year"]: (y["event"], y.get("event_season")) for y in doc["replay"].get("current", [])}
        if ev != ref and [y["year"] for y in o["replay"]] == years:
            errors.append(f"current_options/{o['id']}: a year must carry the same event as on every plan")
    return errors


def words_problems(doc):
    """site/data/words.json (owner's answer 16, 2026-11-13): the blocks the site reads must be there and not empty."""
    errors = [f"words: '{k}' is missing or empty" for k in ("screens", "shared", "glossary", "crop_explainers") if not doc.get(k)]
    if not errors and len(doc["screens"]) != 10:
        errors.append(f"words: ten screens are expected, found {len(doc['screens'])}")
    return errors


def _inside(bbox, lon, lat):
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def validate_index(doc):
    errors = _schema_errors(doc, "index_schema.json")
    if errors:
        return errors
    if d := _dupes([f["id"] for f in doc["fields"]]):
        errors.append(f"fields: duplicate ids {d}")
    for f in doc["fields"]:
        b = f["bbox"]
        if not (b[0] < b[2] and b[1] < b[3]):
            errors.append(f"fields/{f['id']}/bbox: min must be below max")
        elif not _inside(b, f["lon"], f["lat"]):
            errors.append(f"fields/{f['id']}: lat/lon outside its bbox")
    areas = {a["id"]: a for a in doc.get("areas", [])}           # REVIEW_2 H6: areas from build_index.py
    if d := _dupes([a["id"] for a in doc.get("areas", [])]):
        errors.append(f"areas: duplicate ids {d}")
    listed = {f["id"]: f for f in doc["fields"]}
    for a in areas.values():
        for fid in a["fields"]:
            if fid not in listed:
                errors.append(f"areas/{a['id']}: field {fid} is not listed in fields")
            elif listed[fid]["area"] != a["id"]:
                errors.append(f"areas/{a['id']}: field {fid} names area {listed[fid]['area']}")
            elif not _inside(a["bbox"], listed[fid]["lon"], listed[fid]["lat"]):
                errors.append(f"areas/{a['id']}: field {fid} lies outside the area's bbox")
    for f in doc["fields"]:
        if f.get("area") is not None and f["area"] not in areas:
            errors.append(f"fields/{f['id']}: area {f['area']} is not in areas")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(REPO / "site" / "data"))
    ap.add_argument("--final", action="store_true",
                    help="the freeze check before submission: MOCK data and the other final checks are failures")
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir)
    problems = {}

    index_path = data_dir / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else None
    if index is None:
        problems[str(index_path)] = ["missing"]
    elif errs := validate_index(index):
        problems[str(index_path)] = errs

    field_files = sorted((data_dir / "fields").glob("*.json"))
    for path in field_files:
        doc = json.loads(path.read_text())
        errs = validate_field(doc, final=args.final)
        entry = next((f for f in (index or {}).get("fields", []) if f["id"] == path.stem), None)
        if index is not None and entry is None:
            errs.append("not listed in index.json")
        elif entry and not errs and not _inside(entry["bbox"], doc["field"]["lon"], doc["field"]["lat"]):
            errs.append("field lat/lon outside its bbox in index.json")
        if errs:
            problems[str(path)] = errs
        if "MOCK" in path.read_text() and not args.final:
            print(f"WARNING {path}: contains MOCK data, must be replaced before submission (--final makes this a failure)")
        if doc.get("mock"):
            print(f"NOTE {path}: not ready yet (the site must say so): {', '.join(doc['mock'])}")

    for f in (index or {}).get("fields", []):
        if not (data_dir / "fields" / f"{f['id']}.json").exists():
            problems.setdefault(str(index_path), []).append(f"{f['id']}: listed but no fields/{f['id']}.json")
    for a in (index or {}).get("areas", []):
        if not (data_dir / a["map"][len("data/"):]).exists():          # map is relative to the site: data/area/<id>.json
            problems.setdefault(str(index_path), []).append(f"areas/{a['id']}: map {a['map']} does not exist")

    words_path = data_dir / "words.json"
    if words_path.exists():
        if errs := words_problems(json.loads(words_path.read_text())):
            problems[str(words_path)] = errs
    elif args.final:
        problems[str(words_path)] = ["missing (python -m pipeline.export.build_words)"]

    for path, errs in problems.items():
        for e in errs:
            print(f"FAIL {path}: {e}")
    checked = len(field_files) + (index is not None) + words_path.exists()
    print(f"{checked} file(s) checked, {len(problems)} with problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
