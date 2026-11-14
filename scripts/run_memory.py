"""Field memory (CLAUDE.md "Field memory", build step 7b; rules.yaml field_memory; VALIDATION 4.6).

    .venv/bin/python scripts/run_memory.py --field demo

Does a small learned correction predict each season's peak greenness better than the physics twin alone, on years
it has not seen? One row per season the satellite saw in the HLS years (the chosen season method): the twin's water
shortfall and the weather from the season's detected start to its peak, the monsoon's first lasting rain spell, and
the target: the season's peak NDVI minus the usual peak of its slot. Leave one year out; the memory is kept only if
it beats physics alone AND "no anomaly". Writes data/checks/<field>/field_memory.json. Nothing is exported unless it
is kept. Peak NDVI is a stand-in for harvest (green cover, not grain); with about two dozen seasons the test is weak.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.diary import guess as gu  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.ml import memory as fm  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.plans import twin_options as to  # noqa: E402


def dataset(field, rules, lib, data=REPO / "data"):
    clean, checks = data / "clean" / field["id"], data / "checks" / field["id"]
    w = pd.read_parquet(clean / "weather.parquet")
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    cov, by = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by["bare"], **{c: by[cov[c]] for c in cov}}
    rotation, rot_label = sim.rotation_for(field, rules)
    sj = json.loads((checks / "diary_seasons.json").read_text())
    # the rain-fed replay with every switch of rules.yaml (pipeline/plans/twin_options.py: bare_soil, season_dates on the
    # satellite's seasons, paddy_rainfed), as the exported replay
    twin = to.replay(w, rotation, lib, soil, cn, rules, irrigated=False, farmer=True, seasons=to.hls_seasons(sj))["daily"]
    daily = pd.DataFrame({"date": pd.DatetimeIndex(twin["date"]), "eta_mm": twin["eta_mm"].to_numpy(float),
                          "etc_mm": twin["etc_mm"].to_numpy(float)})
    daily = daily.merge(pd.DataFrame({"date": pd.DatetimeIndex(w["date"]), "rain_mm": w["rain_mm"].to_numpy(float),
                                      "tmax_c": w["tmax_c"].to_numpy(float)}), on="date", how="left")
    onset = {int(y): v for y, v in json.loads((checks / "diary_onset.json").read_text())["day_of_year"].items()}
    rows = []
    for ss in sj["chosen"]["seasons_by_year"].values():
        for s in ss:
            if s["source"] != "hls":
                continue
            t = {k: pd.Timestamp(s[k]) for k in ("start", "peak", "end")}
            slot = gu.slot_of(t)
            monsoon_year = t["peak"].year if slot == "monsoon" else t["peak"].year - 1
            if onset.get(monsoon_year) is None:
                continue
            f = fm.window_features(daily, t["start"], t["peak"], rules["trends"]["dry_day_mm"])
            rows.append({"year": int(t["peak"].year), "slot": slot, "start": str(t["start"].date()), "peak": str(t["peak"].date()),
                         "peak_ndvi": float(s["peak_ndvi"]), **f, "onset_doy": float(onset[monsoon_year]),
                         "slot_is_winter": 1.0 if slot == "winter" else 0.0})
    df = pd.DataFrame(rows).sort_values(["year", "slot"]).reset_index(drop=True)
    df["target"] = fm.peak_anomaly(df)
    return df, f"{rotation} ({rot_label})"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    lib = load_crops(field=field)        # the field's country profile (config/countries/)
    F = rules["field_memory"]
    df, rotation = dataset(field, rules, lib)
    res = fm.compare(df, physics="twin_shortfall", features=F["memory_features"], alpha=F["model"]["alpha"])
    out = {"labels": {"field": field["name"], "rotation": rotation, "rain": "the twin's corrected rain",
                      "target": F["target"], "window": F["window"], "physics_only": F["physics_only"],
                      "memory_features": F["memory_features"], "model": F["model"], "validation": F["validation"],
                      "keep_rule": F["keep_rule"],
                      "caveat": "Peak NDVI is a stand-in for harvest: it shows green cover, not grain or tubers. About two dozen "
                                "seasons from one field is a weak test. The twin's placeholder winter crop sits about ten weeks "
                                "before the satellite's winter season (REVIEW_2 H3), so its stress in the winter windows is "
                                "mostly bare-soil evaporation."},
           "result": {k: v for k, v in res.items() if k != "predictions"},
           "seasons": [{**r, **{f"pred_{k}": res["predictions"][k][i] for k in res["predictions"]}}
                       for i, r in enumerate(df.round(4).to_dict("records"))]}
    path = REPO / "data" / "checks" / field["id"] / "field_memory.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    r = res
    print(f"{r['n_seasons']} seasons in {r['n_years']} years; held-out RMSE of the peak-NDVI anomaly: no anomaly {r['rmse']['no_anomaly']}, "
          f"physics only {r['rmse']['physics_only']}, memory {r['rmse']['memory']}; correlation with observed: {r['correlation_with_observed']}")
    print(f"decision: {r['decision']}\n-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
