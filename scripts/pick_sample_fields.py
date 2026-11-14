"""Local Impact 4b: pick 60 m sample fields across the demo's fetch box by the demo's own rule (rules.yaml
sample_fields, committed before the first run). Writes config/fields/sample-<n>.yaml and
data/checks/<field>/sample_fields.json. It does NOT run the field pipeline for them.

    .venv/bin/python scripts/pick_sample_fields.py --field demo

The candidate rule is imported from pipeline/fetch/placeholder.py (generalised on 2026-11-13; with no
`placeholder_seasons` it uses Nepal's seasons, and this script checks that the demo's recorded search comes out the same).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.area import samples as sm  # noqa: E402
from pipeline.fetch import placeholder as ph  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.fetch.worldcover import distance_km  # noqa: E402

HEADER = """# SAMPLE FIELD {n} (PLACEHOLDER), written by scripts/pick_sample_fields.py on {date}. Not a farmer's field: a 60 m
# square picked by the demo field's own rule (pipeline/fetch/placeholder.py: WorldCover 2021 cropland with a 30 m cropland
# margin, no built-up pixel within 100 m of the margin, HLS greenness above NDVI 0.25 in the monsoon and the winter of
# 2023-2025), one per quadrant of the demo's fetch box, at least 1.5 km from the demo field and from the other samples
# (rules.yaml sample_fields; owner's brief 4b, owner's 8b: labelled a sample and listed in index.json). Nobody has
# checked it on satellite imagery yet (the demo's first square was a construction plot). The rotation, water source and
# elevation are not known: the rotations are the demo's placeholders, elevation_m is filled when the pipeline runs.
# Why picked: {why}
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--no-write-configs", action="store_true")
    a = ap.parse_args(argv)
    import pandas as pd
    import rasterio
    from affine import Affine

    field, rules = load_field(a.field), load_rules()
    R = rules["sample_fields"]
    data = REPO / "data"
    origin = field["origin_point"]
    wc = sorted((data / "raw" / "worldcover" / field["id"]).glob("worldcover_2021_*_box.tif"))[0]
    with rasterio.open(wc) as src:
        classes, wt = src.read(1), src.transform
    z = np.load(data / "clean" / field["id"] / "hls_monthly_ndvi.npz")
    comp, keys = z["ndvi"], [str(k) for k in z["months"]]
    ht, hcrs = Affine(*z["transform"].tolist()), str(z["crs"])
    years, bare = [2023, 2024, 2025], 0.25            # as placeholder.main (the demo's search)
    limit = ph.soil_limit_m(rules)

    cands = ph.cropland_squares(classes, wt, origin["lat"], side_m=60, margin_m=ph.MARGIN_M, clear_of_built_m=ph.CLEAR_OF_BUILT_M)
    print(f"{len(cands)} cropland squares clear of built-up; testing all of them", flush=True)
    scored = []
    for i, c in enumerate(cands):
        s, npx = ph.sample_monthly(comp, keys, ht, hcrs, c["lon"], c["lat"], 30)
        r = ph.season_check(s, years, bare)
        if r["passes"]:
            scored.append({**c, **r, "hls_pixels": npx, "every_third": i % 3 == 0,
                           "distance_km": round(distance_km(origin["lat"], origin["lon"], c["lat"], c["lon"]), 3)})
    for c, d in zip(scored, ph.soil_distances(data / "raw" / "soilgrids" / field["id"] / "wcs", scored)):
        c["soilgrids_nearest_m"] = d
    ranked = ph.rank(scored, limit)

    # the generalised placeholder.py must reproduce the demo's recorded search (every third square, top 3 at 0.5 km)
    rec = json.loads((data / "clean" / field["id"] / "placeholder_candidates.json").read_text())
    third = [c for c in ranked if c["every_third"]]
    top3 = ph.pick(third, 3, 0.5)
    demo_check = {"recorded_passing": rec["passing"], "now_passing_every_third": len(third),
                  "recorded_top3": [[c["lat"], c["lon"]] for c in rec["candidates"]],
                  "now_top3": [[c["lat"], c["lon"]] for c in top3]}
    demo_check["same"] = (demo_check["recorded_passing"] == demo_check["now_passing_every_third"]
                          and demo_check["recorded_top3"] == demo_check["now_top3"])
    print(f"demo defaults: {demo_check}")

    demo_ll = (field["lat"], field["lon"])
    picks = sm.spread_pick(ranked, demo_ll, origin, R["spread"]["min_apart_km"])
    rank_of = {(c["lat"], c["lon"]): i + 1 for i, c in enumerate(ranked)}
    out_picks = []
    for n, c in enumerate(picks, 1):
        built = ph.distance_to_class_m(classes, wt, c["lat"], c["lon"], 30 + ph.MARGIN_M, ph.BUILT)
        info = {"id": f"sample-{n}", "quadrant": c["quadrant"], "lat": c["lat"], "lon": c["lon"],
                "rank_among_passing": rank_of[(c["lat"], c["lon"])], "passing": len(ranked),
                "weaker_season_peak_ndvi": round(c["min_peak"], 3), "peaks_monsoon_winter_2023_2025": c["peaks"],
                "winter_rise": c["winter_rise"], "soilgrids_nearest_m": c["soilgrids_nearest_m"],
                "margin_to_built_up_m": None if built is None else round(built, 1),
                "km_from_demo_field": round(distance_km(c["lat"], c["lon"], *demo_ll), 2),
                "km_from_box_centre": c["distance_km"],
                "km_to_other_samples": {p["id"] if "id" in p else f"sample-{k}": round(distance_km(c["lat"], c["lon"], p["lat"], p["lon"]), 2)
                                        for k, p in enumerate(picks, 1) if p is not c}}
        why = (f"best-ranked passing square in the {c['quadrant']} quadrant (rank {info['rank_among_passing']} of {len(ranked)}; "
               f"weaker season's monthly peak NDVI {info['weaker_season_peak_ndvi']}), {info['km_from_demo_field']} km from the demo field")
        info["why"] = why
        out_picks.append(info)
        if not a.no_write_configs:
            cfg = sm.sample_config(n, c, field, why)
            sm.write_yaml(REPO / "config" / "fields" / f"sample-{n}.yaml", cfg,
                          HEADER.format(n=n, date=pd.Timestamp.now().strftime("%Y-%m-%d"), why=why))
        print(json.dumps(info))
    missing = sorted({"NE", "NW", "SE", "SW"} - {p["quadrant"] for p in out_picks})
    out = {"rule": {"candidate_rule": R["candidate_rule"], "spread": R["spread"], "years": years, "bare_ndvi": bare,
                    "soilgrids_nearest_cell_max_m": limit, "rules_commit": "cb85cc8"},
           "squares_tested": len(cands), "passing": len(ranked), "quadrants_without_a_sample": missing,
           "demo_defaults_check": demo_check, "samples": out_picks,
           "label": "PLACEHOLDER sample fields: squares a rule picked from maps, never visited or checked on imagery; "
                    "their rotations and water sources are the demo's placeholders"}
    path = data / "checks" / field["id"] / "sample_fields.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"-> {path.relative_to(REPO)}")
    return 0 if demo_check["same"] else 1


if __name__ == "__main__":
    sys.exit(main())
