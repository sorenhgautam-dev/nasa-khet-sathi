"""Write a MOCK demo field and index so the UI can be built against the contract before real data.

    python -m pipeline.export.mock            # writes site/data/fields/demo.json and site/data/index.json

Every value in the field file is made up. It is labelled MOCK (field name, sources, every tab) so it can
never pass for real data, and validate.py warns while any MOCK file remains. Only the demo point and
bbox come from config/fields/demo.yaml: since 2026-11-12 that is a labelled PLACEHOLDER field (the old
CLAUDE.md point is Bhaktapur's old city), and the index bbox is the field's fetch box. Real exports
replace the mock parts from build step 5 onward.
"""
import json
import sys
from pathlib import Path

from pipeline.export.validate import REPO, validate_field, validate_index
from pipeline.fetch.fields import load_field

_CFG = load_field("demo")
LAT, LON = _CFG["lat"], _CFG["lon"]          # PLACEHOLDER field centre (config/fields/demo.yaml)
BBOX = list(_CFG["bbox"])                    # prepared area = the fetch box
SW = [min(p[0] for p in _CFG["polygon"]), min(p[1] for p in _CFG["polygon"])]   # mock sections start here
CELL_DEG = 0.0001                            # about 11 m north-south, 10 m east-west at 27.7 N
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _sections(rows=3, cols=4):
    statuses = ["green", "yellow", "red", "grey"]
    out = []
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c + 1
            x0, y0 = SW[0] + c * CELL_DEG, SW[1] + r * CELL_DEG
            x1, y1 = x0 + CELL_DEG, y0 + CELL_DEG
            corners = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            out.append({
                "id": f"s{k}",
                "polygon": [[round(x, 6), round(y, 6)] for x, y in corners],
                "status": statuses[k % 4],
                "wetness": 30 + 5 * k,
                "temp": round(18.0 + 0.1 * k, 1) if k % 3 == 1 else None,   # null: the probe has not read it
                "sure": round(0.1 + 0.05 * k, 2),
            })
    return out


def _months():
    rain = ["low"] * 4 + ["medium", "high", "high", "high", "medium"] + ["low"] * 3
    soil = ["dry"] * 4 + ["medium", "wet", "wet", "wet", "wet", "medium", "dry", "dry"]
    heat = ["none", "none", "some", "high", "high", "some", "none", "none", "none", "none", "none", "none"]
    frost = ["high", "risk"] + ["none"] * 9 + ["risk"]
    cover = ["crop"] * 3 + ["partial", "bare", "bare", "partial", "crop", "crop", "crop", "bare", "partial"]
    return [dict(m=m, rain=a, soil=b, heat=c, frost=d, cover=e)
            for m, a, b, c, d, e in zip(MONTHS, rain, soil, heat, frost, cover)]


TAB_KEYS = ("why", "evidence", "benefits", "unknown", "check")


def _tabs(plan_name):
    return {k: f"MOCK text for the {k} tab of '{plan_name}'. Real text comes from build step 7."
            for k in TAB_KEYS}


def _tabs_ne(plan_name):
    return {k: f"MOCK '{plan_name}' योजनाको {k} ट्याबको नमुना पाठ। साँचो पाठ build step 7 ले बनाउँछ।"
            for k in TAB_KEYS}


def _plans():
    specs = [
        ("current", "What you do now", [("rice", "06-15", "10-30"), ("wheat", "11-15", "04-10")],
         {"harvest": 72, "water": 40, "cover": 35, "soil_kept": 60}),
        ("cover_gap", "Fill the empty months", [("rice", "06-15", "10-30"), ("lentil", "11-01", "03-15")],
         {"harvest": 70, "water": 62, "cover": 70, "soil_kept": 75}),
        ("follow_shift", "Plant later, with the rain", [("rice", "07-01", "11-10"), ("mustard", "11-20", "02-28")],
         {"harvest": 76, "water": 55, "cover": 55, "soil_kept": 66}),
    ]
    return [{"id": i, "name": n, "crops": [{"crop": c, "start": s, "end": e} for c, s, e in crops],
             "score": score, "tabs": _tabs(n), "tips": [f"MOCK tip for '{n}'."],
             "tabs_ne": _tabs_ne(n), "tips_ne": [f"MOCK '{n}' को नमुना सुझाव।"]}
            for i, n, crops, score in specs]


def _replay(offset):
    events = {2006: "drought", 2009: "drought", 2017: "flood", 2021: "flood"}
    return [{"year": y, "harvest": max(0, min(100, 60 + offset + (y * 7) % 25 - (20 if y in events else 0))),
             "dry_days": (y * 3) % 30, "event": events.get(y, "none"),
             "irrigated": {"harvest": max(0, min(100, 85 + offset + (y * 7) % 10)), "dry_days": (y * 3) % 5}}
            for y in range(2001, 2026)]


def build_field():
    plans = _plans()
    return {
        "field": {"name": f"{_CFG['name']} (MOCK data)", "lat": LAT, "lon": LON,
                  "water_source": _CFG.get("water_source") or "unknown", "sections": _sections()},
        "diary": {"shift_days": 12, "bare_days": 110, "guess": ["rice", "wheat"],
                  "groundwater": {"trend_cm_per_year": -1.2, "direction": "falling", "confidence": 0.7},
                  "months": _months()},
        "plans": plans,
        "replay": {p["id"]: _replay(offset) for p, offset in zip(plans, (0, -2, 4))},
        "future": {"years": [2026, 2040],
                   "nothing_changes": {"harvest": [70, 55], "harvest_low": [62, 41], "harvest_high": [76, 66]},
                   "with_plan": {"harvest": [78, 74], "harvest_low": [72, 63], "harvest_high": [83, 81]}},
        "sources": [{"name": "MOCK data for building the site", "product": "pipeline/export/mock.py",
                     "resolution": "none (made up)", "years": "none", "type": "model"}],
    }


def build_index():
    return {"fields": [{"id": "demo", "name": _CFG["name"], "country": _CFG["country"],
                        "lat": LAT, "lon": LON, "bbox": list(BBOX)}]}


def write_all(out_dir):
    out_dir = Path(out_dir)
    field, index = build_field(), build_index()
    errors = validate_field(field) + validate_index(index)
    if errors:
        raise ValueError("mock does not meet the contract:\n" + "\n".join(errors))
    (out_dir / "fields").mkdir(parents=True, exist_ok=True)
    (out_dir / "fields" / "demo.json").write_text(json.dumps(field, indent=1, ensure_ascii=False) + "\n")
    (out_dir / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    return out_dir


if __name__ == "__main__":
    print(f"wrote mock to {write_all(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'site' / 'data')}")
