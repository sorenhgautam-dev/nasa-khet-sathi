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
        ("safest", "Safest in bad years", [("rice", "06-15", "10-30"), ("lentil", "11-01", "03-15")],
         {"harvest": 76, "water": 55, "cover": 55, "soil_kept": 66}),
    ]
    return [{"id": i, "name": n, "crops": [{"crop": c, "start": s, "end": e} for c, s, e in crops],
             "score": score, "tabs": _tabs(n), "tips": [f"MOCK tip for '{n}'."],
             "tabs_ne": _tabs_ne(n), "tips_ne": [f"MOCK '{n}' को नमुना सुझाव।"]}
            for i, n, crops, score in specs]


def _with_ranges(plans, replay):
    """Owner's decision 1 (2026-11-13): where GPM's uncorrected rain changes a result, the file carries it beside."""
    plans[1]["score_dhm_rain"] = {**plans[1]["score"], "harvest": plans[1]["score"]["harvest"] + 4}
    for y in replay["current"]:
        if y["year"] in (2020, 2022):
            y["dhm_rain"] = {"harvest": min(100, y["harvest"] + 6), "dry_days": max(0, y["dry_days"] - 5),
                                     "event": "flood" if y["year"] == 2020 else y["event"], "irrigated": dict(y["irrigated"])}
    return plans, replay


def _replay(offset):
    events = {2006: "drought", 2009: "drought", 2017: "flood", 2021: "flood"}
    return [{"year": y, "harvest": max(0, min(100, 60 + offset + (y * 7) % 25 - (20 if y in events else 0))),
             "dry_days": (y * 3) % 30, "event": events.get(y, "none"),
             "irrigated": {"harvest": max(0, min(100, 85 + offset + (y * 7) % 10)), "dry_days": (y * 3) % 5}}
            for y in range(2001, 2026)]


def build_field():
    plans = _plans()
    plans, replay = _with_ranges(plans, {p["id"]: _replay(offset) for p, offset in zip(plans, (0, -2, 4))})
    return {
        "field": {"name": f"{_CFG['name']} (MOCK data)", "lat": LAT, "lon": LON,
                  "water_source": _CFG.get("water_source") or "unknown", "sections": _sections()},
        "diary": {"shift_days": 12, "bare_days": 110, "guess": ["rice", "wheat"],
                  "groundwater": {"trend_cm_per_year": -1.2, "direction": "falling", "confidence": 0.7},
                  "months": _months()},
        "plans": plans,
        "replay": replay,
        "future": {"years": [2026, 2040],
                   "nothing_changes": {"harvest": [70, 55], "harvest_low": [62, 41], "harvest_high": [76, 66]},
                   "with_plan": {"harvest": [78, 74], "harvest_low": [72, 63], "harvest_high": [83, 81]}},
        "method": {"season_detection": {
            "chosen": "threshold", "margin": 0.02, "held_out_years": [2018, 2022], "thin_days": 16, "rule_methods_agree": 0.73,
            "methods": [{"id": "threshold", "si": False, "score": 0.96, "by_year": [{"year": 2018, "score": 0.95}, {"year": 2022, "score": 0.97}],
                         "start_diff_days": None, "peak_diff_days": None, "end_diff_days": None},
                        {"id": "changepoint", "si": False, "score": 0.95, "by_year": [{"year": 2018, "score": 0.98}, {"year": 2022, "score": 0.92}],
                         "start_diff_days": 14, "peak_diff_days": 4, "end_diff_days": 6},
                        {"id": "detective", "si": True, "score": 0.97, "by_year": [{"year": 2018, "score": 0.99}, {"year": 2022, "score": 0.95}],
                         "start_diff_days": 4, "peak_diff_days": 0, "end_diff_days": 2}]},
            "rain_correction": {
                "applied": True, "from": "2017-01-01", "reference_years": [2001, 2016],
                "factors": {m: 0.7 for m in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")},
                "held_out": {"months": 48, "error_before_mm": 90.0, "error_after_mm": 30.0, "ratio_before": 1.6, "ratio_after": 1.05},
                "rain_mm_per_year": {"reference": 1840.0, "after_uncorrected": 2730.0, "after_corrected": 1880.0, "station_normal": 1375.0},
                "gauges": {"weight_before_pct": [96, 97], "weight_after_pct": [56, 72], "stations_before": 50, "stations_after": 1},
                "words": {"en": "MOCK: why and how the rain after 2016 was corrected.", "ne": "MOCK: २०१६ पछिको वर्षा किन र कसरी सच्याइयो।"}},
            "choices": [{"id": "mock_choice", "choice": "MOCK: a choice no source fixes", "value": "1",
                         "status": "Claude's choice, owner-approved"}]},
        "sources": [{"name": "MOCK data for building the site", "product": "pipeline/export/mock.py",
                     "resolution": "none (made up)", "years": "none", "type": "model"}],
    }


def build_index():
    return {"fields": [{"id": "demo", "name": _CFG["name"], "country": _CFG["country"],
                        "lat": LAT, "lon": LON, "bbox": list(BBOX), "sample": False, "area": None}]}


def write_all(out_dir, force=False):
    """Write the mock field and index. Refuses to replace a field file that holds real results (any source that is
    not the MOCK one) unless force=True (REVIEW_2 M13: the bare command used to overwrite the real export)."""
    out_dir = Path(out_dir)
    dest = out_dir / "fields" / "demo.json"
    if dest.exists() and not force:
        try:
            real = [x.get("name") for x in json.loads(dest.read_text()).get("sources", []) if "MOCK" not in str(x.get("name"))]
        except (ValueError, AttributeError):
            real = ["an unreadable file"]
        if real:
            raise FileExistsError(f"{dest} holds real results (sources: {real}); the mock will not replace it. "
                                  "Pass --force (or force=True) only if you mean to throw the real export away")
    field, index = build_field(), build_index()
    errors = validate_field(field) + validate_index(index)
    if errors:
        raise ValueError("mock does not meet the contract:\n" + "\n".join(errors))
    (out_dir / "fields").mkdir(parents=True, exist_ok=True)
    (out_dir / "fields" / "demo.json").write_text(json.dumps(field, indent=1, ensure_ascii=False) + "\n")
    (out_dir / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    return out_dir


if __name__ == "__main__":
    _args = [a for a in sys.argv[1:] if a != "--force"]
    print(f"wrote mock to {write_all(Path(_args[0]) if _args else REPO / 'site' / 'data', force='--force' in sys.argv[1:])}")
