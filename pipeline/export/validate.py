"""Validate exports against the output contract.

    python -m pipeline.export.validate                # checks site/data/
    python -m pipeline.export.validate --data-dir DIR

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


def validate_field(doc):
    """Return a list of problems; empty means the field file meets the contract."""
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
    for key, years in doc["replay"].items():
        if key not in plan_ids:
            errors.append(f"replay/{key}: no plan with this id")
        if d := _dupes([y["year"] for y in years]):
            errors.append(f"replay/{key}: duplicate years {d}")
    n = len(doc["future"]["years"])
    for series in ("nothing_changes", "with_plan"):
        s = doc["future"][series]
        for key in ("harvest", "harvest_low", "harvest_high"):
            if len(s[key]) != n:
                errors.append(f"future/{series}/{key}: needs {n} values, one per year")
        for i, (lo, mid, hi) in enumerate(zip(s["harvest_low"], s["harvest"], s["harvest_high"])):
            if not lo <= mid <= hi:
                errors.append(f"future/{series}: year {i} needs harvest_low <= harvest <= harvest_high")
    gw = doc["diary"]["groundwater"]
    if gw["direction"] == "falling" and gw["trend_cm_per_year"] >= 0:
        errors.append("diary/groundwater: 'falling' needs a negative trend")
    if gw["direction"] == "rising" and gw["trend_cm_per_year"] <= 0:
        errors.append("diary/groundwater: 'rising' needs a positive trend")
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
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(REPO / "site" / "data"))
    data_dir = Path(ap.parse_args(argv).data_dir)
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
        errs = validate_field(doc)
        entry = next((f for f in (index or {}).get("fields", []) if f["id"] == path.stem), None)
        if index is not None and entry is None:
            errs.append("not listed in index.json")
        elif entry and not errs and not _inside(entry["bbox"], doc["field"]["lon"], doc["field"]["lat"]):
            errs.append("field lat/lon outside its bbox in index.json")
        if errs:
            problems[str(path)] = errs
        if "MOCK" in path.read_text():
            print(f"WARNING {path}: contains MOCK data, must be replaced before submission")

    for f in (index or {}).get("fields", []):
        if not (data_dir / "fields" / f"{f['id']}.json").exists():
            problems.setdefault(str(index_path), []).append(f"{f['id']}: listed but no fields/{f['id']}.json")

    for path, errs in problems.items():
        for e in errs:
            print(f"FAIL {path}: {e}")
    checked = len(field_files) + (index is not None)
    print(f"{checked} file(s) checked, {len(problems)} with problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
