"""Feature 3, Field Pulse (खेतको नाडी; rules.yaml pulse): the field's greenness history as a heartbeat line ->
site/data/pulse/<field>.json. Nothing new is computed: the diary's own observations, smoothed curve and seasons, the
typical dates as medians of those seasons, and the area map's totals.

    .venv/bin/python -m pipeline.export.build_pulse --field demo
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.diary.guess import SLOTS
from pipeline.export.build_labels import label_for, load_scorecard
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules

REPO = Path(__file__).resolve().parents[2]
LABELS = ("pulse_hls", "pulse_modis", "pulse_curve", "pulse_seasons", "pulse_typical")


def observations(g, hls_from):
    """The diary's own points (scripts/run_diary.py run_greenness): HLS from its first clear day (not before hls_from),
    MODIS before it."""
    g = g.dropna(subset=["ndvi"]).assign(date=lambda d: pd.to_datetime(d["date"]))
    hls = g[g["source"].str.startswith("hls")]
    first = max(hls["date"].min(), pd.Timestamp(hls_from))
    pts = lambda d: [[str(t.date()), round(float(v), 3)] for t, v in zip(d["date"], d["ndvi"])]  # noqa: E731
    return {"hls": pts(hls[hls["date"] >= first]), "modis": pts(g[(g["source"] == "modis") & (g["date"] < first)])}


def curve(daily, step):
    d = daily.dropna(subset=["ndvi_smooth"]).iloc[::step]
    return [[str(pd.Timestamp(t).date()), round(float(v), 3), s] for t, v, s in zip(d["date"], d["ndvi_smooth"], d["source"])]


def slot_of(peak):
    return next(k for k, months in SLOTS.items() if pd.Timestamp(peak).month in months)


def seasons(chosen):
    return [{"year": int(y), "slot": slot_of(s["peak"]), "source": s["source"], "greenup": s["start"], "peak": s["peak"],
             "end": s["end"], "peak_ndvi": s["peak_ndvi"]} for y, rows in sorted(chosen.items(), key=lambda x: int(x[0]))
            for s in rows]


def _days(date, year):
    return (pd.Timestamp(date) - pd.Timestamp(f"{year}-01-01")).days


def _mmdd(days):
    t = pd.Timestamp("2001-01-01") + pd.Timedelta(int(round(days)), unit="D")
    return f"{t.month:02d}-{t.day:02d}"


def typical(ss, guess, lib):
    """rules.yaml pulse.typical: per slot over the HLS seasons, the median of each date in days from 1 January of the
    season's year; planting = green-up minus the guessed crop's initial stage."""
    out = []
    for i, slot in enumerate(SLOTS):
        rows = [s for s in ss if s["slot"] == slot and s["source"] == "hls"]
        if not rows:
            continue
        med = {k: float(np.median([_days(s[k], s["year"]) for s in rows])) for k in ("greenup", "peak", "end")}
        crop = guess[i] if i < len(guess) and guess[i] in lib else None
        out.append({"slot": slot, "crop": crop,
                    "planting": _mmdd(med["greenup"] - lib[crop]["stages_days"]["ini"]) if crop else None,
                    "greenup": _mmdd(med["greenup"]), "peak": _mmdd(med["peak"]), "harvest": _mmdd(med["end"]),
                    "years": [min(s["year"] for s in rows), max(s["year"] for s in rows)], "n": len(rows)})
    return out


def nearby(fid, data, site):
    """rules.yaml pulse.nearby: totals copied from the field's own area map, or None."""
    path, area = data / "checks" / fid / "area_map.json", site / "area" / f"{fid}.json"
    if not (path.exists() and area.exists()):
        return None
    a = json.loads(path.read_text())
    num = {k: {"value": round(v["value"], 3), "low": round(v["low"], 3), "high": round(v["high"], 3), "unit": v["unit"]}
           for k, v in a["numbers"].items()}
    own = (a.get("fields", {}).get(fid) or {}).get("diary_way", {})
    years = a["hls"]["years"]
    return {"cropland_ha": a["cropland"]["area_ha"], "years": f"{min(years)}-{max(years)}",
            "area": "the cropland of this field's fetch box (about 10 x 10 km)", **num,
            "this_field": {"mean_bare_days": own.get("mean_bare_days"), "mean_seasons_a_year": own.get("mean_seasons_a_year")},
            "map": f"data/area/{fid}.json"}


def build(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules = load_field(fid), load_rules()
    lib = load_crops(field=field)        # the field's country profile: Nepal's crops.json, else its FAO zone calendar
    clean, checks = data / "clean" / fid, data / "checks" / fid
    doc = json.loads((site / "fields" / f"{fid}.json").read_text())
    pts = observations(pd.read_parquet(clean / "greenness_field.parquet"), rules["greenness"]["hls_from"])
    ss = seasons(json.loads((checks / "diary_seasons.json").read_text())["chosen"]["seasons_by_year"])
    card = load_scorecard(fid, field, data)
    near = nearby(fid, data, site)
    if near:
        near["label"] = label_for("nearby_fields", field, rules, card)
    yr = lambda p: f"{p[0][0][:4]}-{p[-1][0][:4]}" if p else "none"  # noqa: E731
    srcs = [{"name": "Harmonized Landsat Sentinel-2", "product": "HLS-VI v2.0 greenness (NDVI), cloud-masked with Fmask",
             "resolution": "30 m", "years": yr(pts["hls"]), "type": "satellite"},
            {"name": "MODIS Terra", "product": "MOD13Q1 v061 greenness (NDVI), 16-day composites, before HLS",
             "resolution": "250 m", "years": yr(pts["modis"]), "type": "satellite"}]
    if near:
        srcs += [x for x in json.loads((site / "area" / f"{fid}.json").read_text()).get("sources", []) if x not in srcs]
    sc = rules["labels"]["source_scales"]
    return {"field": fid, "placeholder": bool(field.get("placeholder")),
            "made_by": "pipeline/export/build_pulse.py (rules.yaml pulse)",
            "points": pts, "point_scale": {"hls": sc["hls"], "modis": sc["modis"]},
            "curve": {"step_days": rules["pulse"]["curve"]["step_days"],
                      "points": curve(pd.read_parquet(clean / "seasons_daily.parquet"), rules["pulse"]["curve"]["step_days"])},
            "seasons": ss, "bare_threshold": rules["bare_days"]["ndvi_max"],
            "typical": typical(ss, doc["diary"].get("guess") or [], lib),
            "nearby": near,
            "labels": {k: label_for(k, field, rules, card) for k in LABELS},
            "sources": srcs}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    doc = build(a.field)
    out = REPO / "site" / "data" / "pulse" / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(doc['points']['hls'])} HLS and {len(doc['points']['modis'])} "
          f"MODIS points, {len(doc['curve']['points'])} curve points, {len(doc['seasons'])} seasons; typical {doc['typical']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
