"""Feature 1, two labels on every number (rules.yaml labels): how sure (verified or estimate, from this run's scorecard)
and at what scale (field, neighbourhood, valley, region) -> site/data/labels/<field>.json. Also refreshes the `label`
blocks inside site/data/{replay,pulse,checkup}/<field>.json, so every file shows the same scorecard.

    .venv/bin/python -m pipeline.export.build_labels --field demo

Runs after scripts/run_verification.py (a sample field takes its source field's scorecard, as its checks are its).
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules

REPO = Path(__file__).resolve().parents[2]
SCALES = ("field", "neighbourhood", "valley", "region")            # finest to coarsest
RANK = {"NOT YET VERIFIABLE": 0, "ESTIMATE": 1, "VERIFIED": 2}
TWIN = ("gpm", "power", "soilgrids")                               # rules.yaml labels.rule: the twin's three inputs
SOURCES = {   # key: (name, resolution) as the site's sources name them
    "gpm": ("GPM IMERG", "0.1 deg (about 10 km)"), "power": ("NASA POWER", "0.5 x 0.625 deg (about 55 km)"),
    "ghcn": ("Kathmandu Airport station", "one point, 7 km west"), "hls": ("Harmonized Landsat Sentinel-2", "30 m"),
    "modis": ("MODIS Terra", "250 m"), "soilgrids": ("ISRIC SoilGrids", "250 m"), "grace": ("GRACE and GRACE-FO", "about 300 km"),
    "nasadem": ("NASADEM", "30 m"), "smap": ("NASA SMAP L4", "9 km"), "nexgddp": ("NEX-GDDP-CMIP6", "0.25 deg"),
    "dhm_normals": ("DHM 1991-2020 normals, Bhaktapur", "one gauge, 2.3 km away"),
    "dhm_onset": ("DHM monsoon onset dates", "one date a year for eastern Nepal"),
    "dhm_bulletins": ("DHM monthly bulletins", "valley gauges within 10 km"), "chirps": ("CHIRPS v3.0", "0.05 deg (about 5 km)"),
    "gpcc": ("GPCC Full Data Monthly V2022", "1 deg box"), "crop_calendar": ("FAO Crop Calendar, Nepal Hill zone", "a zone of Nepal"),
    "worldcover": ("ESA WorldCover 2021", "10 m"), "probe": ("Khet Sathi probe", "a few cm of one part"),
    "oni": ("NOAA CPC Oceanic Nino Index", "Nino-3.4 region of the Pacific"),
    "area_box": ("Area map of the fetch box", "about 10 x 10 km"),
}


def load_scorecard(fid, field, data=REPO / "data"):
    """(scorecard dict, the field whose scorecard it is), or ({}, None) when there is none."""
    src = field.get("sample_of") or fid
    path = data / "checks" / src / "scorecard.json"
    return (json.loads(path.read_text()), src) if path.exists() else ({}, None)


def _source_scale(key, field, rules):
    sc = rules["labels"]["source_scales"]
    if key == "power":
        return sc["power_corrected" if field.get("correction_label") else "power"]
    return sc[key]


def _keys(inputs):
    return [k for i in inputs for k in (TWIN if i == "twin" else (i,))]


def label_for(output_id, field, rules, card):
    """One labels.outputs entry: sure, status, k, n, scale, rain_corrected, sources, scorecard."""
    o = rules["labels"]["outputs"][output_id]
    card, _ = card if isinstance(card, tuple) else (card, None)
    rows = []
    for key in o["scorecard"] or []:
        row, sub = (key.split(".", 1) + [None])[:2]
        r = (card.get(row) or {})
        rows.append((r.get(sub) if sub else r) or {})
    statuses = [r.get("status", "NOT YET VERIFIABLE") for r in rows] or ["NOT YET VERIFIABLE"]
    status = min(statuses, key=RANK.get)
    scale = max((_source_scale(k, field, rules) for k in _keys(o["inputs"])), key=SCALES.index)
    return {"sure": "verified" if status == "VERIFIED" else "estimate", "status": status,
            "k": sum(int(r.get("k") or 0) for r in rows), "n": sum(int(r.get("n") or 0) for r in rows),
            "scale": scale, "rain_corrected": bool(o["rain_corrected"]),
            "sources": list(dict.fromkeys(_keys(o["inputs"]) + list(o["also"]))),
            "scorecard": "+".join(o["scorecard"]) if o["scorecard"] else None}


def build(fid, data=REPO / "data"):
    field, rules = load_field(fid), load_rules()
    card, src = load_scorecard(fid, field, data)
    L = rules["labels"]
    outputs = {k: label_for(k, field, rules, card) for k in L["outputs"]}
    used = sorted({s for o in outputs.values() for s in o["sources"]})
    return {"field": fid, "placeholder": bool(field.get("placeholder")),
            "made_by": "pipeline/export/build_labels.py (rules.yaml labels)",
            "scorecard_of": src,
            "scales": {k: {x: v[x] for x in ("en", "ne", "about")} for k, v in L["scales"].items()},
            "outputs": outputs,
            "sources": {k: {"name": SOURCES[k][0], "resolution": SOURCES[k][1], "scale": _source_scale(k, field, rules)}
                        for k in used}}


def refresh_blocks(fid, doc, site=REPO / "site" / "data"):
    """Put this run's label into the replay, pulse and check-up files (their `label`, and the pulse's `labels`)."""
    out = []
    for kind, single in (("replay", "replay_window"), ("checkup", "checkup_rain"), ("pulse", None)):
        path = site / kind / f"{fid}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        if single:
            d["label"] = doc["outputs"][single]
        else:
            d["labels"] = {k: doc["outputs"][k] for k in d.get("labels", {})}
            if d.get("nearby"):
                d["nearby"]["label"] = doc["outputs"]["nearby_fields"]
        path.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False) + "\n")
        out.append(kind)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    doc = build(a.field)
    out = REPO / "site" / "data" / "labels" / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    done = refresh_blocks(a.field, doc)
    n = sum(o["sure"] == "verified" for o in doc["outputs"].values())
    print(f"wrote {out}: {len(doc['outputs'])} outputs, {n} verified (scorecard of {doc['scorecard_of']}); refreshed {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
