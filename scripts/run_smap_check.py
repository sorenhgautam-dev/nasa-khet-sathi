"""SMAP against the twin's soil wetness (CLAUDE.md build step 12; VALIDATION 4.2b; REVIEW_2 Phase 3).

    .venv/bin/python scripts/run_smap_check.py --field demo

Compares ANOMALIES, never absolute values: SMAP L4 root-zone soil moisture (0-100 cm, m3/m3, a 9 km cell, model-
assisted) and the twin's root-zone wetness (1 - Dr/TAW, the field's current rotation, rain-fed) measure different
things at different scales. Each series is averaged by month and each calendar month's own mean is removed; the
monthly anomalies are then correlated, for the twin's corrected rain and for GPM as published. A check only:
writes data/checks/<field>/smap_vs_twin.json and changes nothing else.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.fetch.smap import monthly_anomaly  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402


def twin_wetness(weather, field, rules, lib, soil):
    """Daily root-zone wetness 1 - Dr/TAW of the current rotation, rain-fed (the series behind diary.months soil)."""
    cov, by = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by["bare"], **{c: by[cov[c]] for c in cov}}
    rotation, _ = sim.rotation_for(field, rules)
    r = sim.replay(weather, rotation, lib, soil, cn, bare_kc=rules["bare_soil"]["kc"], irrigated=False,
                   kc_climate=rules["kc_climate"]["apply"])
    d = r["daily"]
    return pd.Series(1.0 - d["dr_mm"].to_numpy(float) / d["taw_mm"].to_numpy(float), index=pd.DatetimeIndex(d["date"]))


def compare(a, b):
    """Pearson and Spearman correlation of two monthly anomaly series over their shared months."""
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(j) < 12:
        raise ValueError(f"only {len(j)} shared months: too few to compare")
    x, y = j.iloc[:, 0], j.iloc[:, 1]
    return {"months": int(len(j)), "pearson": round(float(x.corr(y)), 3), "spearman": round(float(x.corr(y, method="spearman")), 3)}


def step(anom, year):
    """Mean anomaly from `year` on minus the mean before it, in units of the series' own standard deviation."""
    before, after = anom[anom.index.year < year], anom[anom.index.year >= year]
    return round(float((after.mean() - before.mean()) / anom.std()), 2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field, rules, lib = load_field(a.field), load_rules(), load_crops()
    clean = REPO / "data" / "clean" / field["id"]
    smap_path = clean / "smap.parquet"
    if not smap_path.exists():
        print(f"NOT YET POSSIBLE: {smap_path.relative_to(REPO)} does not exist (pipeline.fetch.smap)")
        return 2
    smap = pd.read_parquet(smap_path).set_index("date")
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    w = pd.read_parquet(clean / "weather.parquet")
    sm = monthly_anomaly(smap["smap_l4_rootzone_m3m3"])
    out = {"labels": {"field": field["name"], "smap": "SPL4SMGP v008 sm_rootzone (0-100 cm), 9 km cell holding the field, model-assisted",
                      "twin": "root-zone wetness 1 - Dr/TAW, current rotation, rain-fed",
                      "method": "monthly means minus each calendar month's own mean over the shared months; complete months only",
                      "caveat": "Anomalies only. A 9 km model cell is not a 60 m field; SMAP L4's own rain forcing is gauge-corrected "
                                "and may share gauges with IMERG, so this is a consistency check, not ground truth. SMAP L3 has no "
                                "recommended-quality retrieval over this cell and is not used (data card smap.json)."},
           "months_smap": int(len(sm)), "rain": {}}
    years = sorted(set(sm.index.year))
    for version in ("corrected", "uncorrected"):
        tw_daily = twin_wetness(with_rain(w, version), field, rules, lib, soil)
        tw = monthly_anomaly(tw_daily[tw_daily.index >= smap.index.min()])
        sm2, tw2 = sm.align(tw, join="inner")
        sm2, tw2 = sm2 - sm2.groupby(sm2.index.month).transform("mean"), tw2 - tw2.groupby(tw2.index.month).transform("mean")
        res = compare(sm2, tw2)
        wet = sm2.index.month.isin([6, 7, 8, 9])
        res["monsoon_months_jun_sep"] = compare(sm2[wet], tw2[wet])
        res["dry_months_oct_may"] = compare(sm2[~wet], tw2[~wet])
        ya, yb = sm2.groupby(sm2.index.year).mean(), tw2.groupby(tw2.index.year).mean()
        full = [y for y in years if (sm2.index.year == y).sum() == 12]
        res["by_year"] = {"years": full, "spearman": round(float(ya[full].corr(yb[full], method="spearman")), 3),
                          "smap": {int(y): round(float(ya[y]), 4) for y in full}, "twin": {int(y): round(float(yb[y]), 4) for y in full}}
        res["step_at_2017_in_sd"] = {"smap": step(sm2, 2017), "twin": step(tw2, 2017)}
        out["rain"][version] = res
    path = REPO / "data" / "checks" / field["id"] / "smap_vs_twin.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    for v, r in out["rain"].items():
        print(f"{v:12s} months {r['months']}, Pearson {r['pearson']}, Spearman {r['spearman']}; monsoon {r['monsoon_months_jun_sep']['pearson']}, "
              f"dry months {r['dry_months_oct_may']['pearson']}; by year (n {len(r['by_year']['years'])}) Spearman {r['by_year']['spearman']}; "
              f"step at 2017 (sd): SMAP {r['step_at_2017_in_sd']['smap']}, twin {r['step_at_2017_in_sd']['twin']}")
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
