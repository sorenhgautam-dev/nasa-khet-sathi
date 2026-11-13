"""The plan runs of the 2040 outlook (build step 9; rules.yaml future.outputs). Pure functions.

plan_run() is the core of scripts/run_plans.py evaluate(), with the same functions and years: the plan's sowing dates
(plans.generate.plan_dates), the replay rain-fed and irrigated (plans.simulate.replay with the bare-soil setting of
twin/evaporation.bare_soil_setting, which follows rules.yaml bare_soil.apply, and kc_climate.apply), and the complete
years (plans.score.complete). tests/test_future.py checks that both give the same
numbers. spread() is the exported range: the median over the model-scenario runs and the lowest and highest run.
"""
import numpy as np

from pipeline.plans import generate as ge
from pipeline.plans import score as sc
from pipeline.plans import simulate as sim
from pipeline.twin import evaporation as evap


def plan_run(specs, weather, lib, soil, cn, rules):
    """{harvest, stability, dry_days (rain-fed, means over the complete years), irrigation_mm (the irrigated run's mean
    yearly water), irrigated_harvest, years}."""
    crops = [sp["crop"] for sp in specs]
    plan = ge.plan_dates(specs, lib, weather["date"].min(), weather["date"].max())
    bare = evap.bare_soil_setting(rules["bare_soil"], soil, rules["bare_soil"].get("force", "rules"))   # as run_plans
    kw = dict(bare_kc=bare, kc_climate=rules["kc_climate"]["apply"], plan=plan)
    rf = sim.replay(weather, crops, lib, soil, cn, irrigated=False, **kw)
    ir = sim.replay(weather, crops, lib, soil, cn, irrigated=True, **kw)
    ok = {y["year"] for y in sc.complete(rf["years"], crops)}
    rf_years = [y for y in rf["years"] if y["year"] in ok]
    ir_years = [y for y in ir["years"] if y["year"] in ok]
    m = sc.harvest_metrics(rf_years)
    return {"harvest": m["harvest"], "stability": m["stability"], "dry_days": m["dry_days"],
            "irrigation_mm": float(np.mean([y["irrigation_mm"] for y in ir_years])),
            "irrigated_harvest": float(np.mean([y["harvest"] for y in ir_years])), "years": sorted(ok)}


def spread(runs, key):
    """{median, low, high, n, low_run, high_run} of runs[i][key] (each run a dict with 'run' naming it)."""
    if not runs:
        raise ValueError("no runs")
    v = np.array([r[key] for r in runs], float)
    lo, hi = int(np.argmin(v)), int(np.argmax(v))
    return {"median": float(np.median(v)), "low": float(v[lo]), "high": float(v[hi]), "n": len(v),
            "low_run": runs[lo].get("run"), "high_run": runs[hi].get("run")}
