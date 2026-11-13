"""Build step 10: the twin's state "now" and the Kalman numbers -> data/clean/<field>/twin_state.json.

    .venv/bin/python -m pipeline.fetch.now --field demo          # first: the near-real-time weather (weather_now.parquet)
    .venv/bin/python scripts/run_twin_now.py --field demo

The field's current plan (data/checks/<field>/plans.json shown.current) is run in the field's export water case
(pipeline/plans/simulate.export_case: rain-fed while the water source is unknown) from the first weather day through the
as-of day (weather.parquet then weather_now.parquet), with the same functions as scripts/run_plans.py evaluate()
(generate's season dates, twin/season.simulate, Kc climate adjustment, bare-soil Kc), the crop still in the ground on
the as-of day included (kalman.plan_through). The last day's state, P0, the prior from SMAP L4 and Q follow
rules.yaml probe.kalman (committed before the first run). The same run on GPM as published is kept beside it
(`uncorrected_rain`). Keys the sections code reads: field, date, plan, water_case, crop, dr_mm, taw_mm, raw_mm, ks,
wetness_pct, p0_var, prior_var, sure_prior, q_var_per_day, sources, labels.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch import now as fnow  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.twin import evaporation as evap  # noqa: E402
from pipeline.twin import kalman as kf  # noqa: E402
from pipeline.twin import season  # noqa: E402
from pipeline.twin import soil_water as sw  # noqa: E402
from pipeline.twin.crops import rhmin_pct, season_length  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402
from robot.calibrate import depth_theta as root_zone_theta  # noqa: E402


def bare_setting(rules, soil):
    """The twin's bare-soil argument, exactly as scripts/run_plans.py passes it (build step 2a; rules.yaml bare_soil: the
    constant Kc while apply is off, FAO-56's surface layer when it is on), so the state follows the switch."""
    return evap.bare_soil_setting(rules["bare_soil"], soil, rules["bare_soil"].get("force", "rules"))


def run_to_as_of(w, specs, lib, soil, cn, rules, irrigated):
    """twin/season.simulate through the last weather day; (daily table, plan)."""
    plan = kf.plan_through(specs, lib, w["date"].min(), w["date"].max())
    w = w.reset_index(drop=True)
    w = w.assign(u2_ms=w["ws2m_ms"].to_numpy(), rhmin_pct=np.asarray(rhmin_pct(w["ea_kpa"], w["tmax_c"]), dtype=float))
    daily, _ = season.simulate(w[["date", "et0_mm", "rain_mm", "u2_ms", "rhmin_pct"]], plan, lib, soil, cn,
                               bare_setting(rules, soil), irrigated, kc_climate=rules["kc_climate"]["apply"])
    return daily, plan


def zr_of_state(state, plan, lib, soil):
    """The root depth behind the last day's TAW (a bare spell uses a neighbouring crop's, as twin/season.py does)."""
    for c in dict.fromkeys(([state["crop"]] if state["crop"] != "bare" else []) + [c for c, _ in reversed(plan)]):
        if abs(sw.taw_from_layers(soil, lib[c]["zr_m"]) - state["taw_mm"]) < 1e-6:
            return float(lib[c]["zr_m"]), c
    raise ValueError(f"no crop of the plan gives the last day's TAW {state['taw_mm']} mm")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field, rules, lib = load_field(a.field), load_rules(), load_crops()
    K = rules["probe"]["kalman"]
    clean, checks = REPO / "data" / "clean" / field["id"], REPO / "data" / "checks" / field["id"]
    now_path = clean / "weather_now.parquet"
    if not now_path.exists():
        print(f"NOT YET POSSIBLE: {now_path.relative_to(REPO)} is missing (run python -m pipeline.fetch.now first)")
        return 2
    w = fnow.join_weather(pd.read_parquet(clean / "weather.parquet"), pd.read_parquet(now_path))
    problems = sim.rain_record_problems(w)
    if problems:
        print("NOT YET POSSIBLE: " + "; ".join(problems))
        return 2
    now_card = json.loads((REPO / "data" / "cards" / field["id"] / "weather_now.json").read_text())
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    cov, by = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by["bare"], **{c: by[cov[c]] for c in cov}}
    plans = json.loads((checks / "plans.json").read_text())
    current_id = plans["shown"]["current"]
    specs = next(r["specs"] for r in plans["plans"] if r["id"] == current_id)
    water_source = field.get("water_source") or "unknown"
    case = sim.export_case(field.get("water_source"))
    runs = {}
    for version in ("corrected", "uncorrected"):
        daily, plan = run_to_as_of(with_rain(w, version), specs, lib, soil, cn, rules, case == "irrigated")
        runs[version] = (daily, plan, kf.state_on_last_day(daily, plan))
    daily, plan, st = runs["corrected"]
    zr, zr_crop = zr_of_state(st, plan, lib, soil)
    fc, wp = root_zone_theta(soil, zr)
    wet = pd.Series(100.0 * (1.0 - daily["dr_mm"].to_numpy(float) / daily["taw_mm"].to_numpy(float)),
                    index=pd.DatetimeIndex(daily["date"]))
    p0 = kf.p0_var(wet, st["date"], K["p0"]["years"], K["p0"]["half_window_days"])
    smap = pd.read_parquet(clean / "smap.parquet").set_index("date")["smap_l4_rootzone_m3m3"]
    fit = kf.prior_from_smap(wet, smap, K["p0"]["half_window_days"], near=st["date"])
    nums = kf.kalman_numbers(p0, fit)
    today = pd.Timestamp(date.today())
    days_old = int((today - pd.Timestamp(st["date"])).days)
    aged = kf.aged_prior_var(nums["prior_var"], nums["q_var_per_day"], p0, days_old)
    sown_len = season_length(lib[st["crop"]]["stages_days"]) if st["crop"] != "bare" else None
    as_of_label = pd.Timestamp(st["date"]).strftime("%-d %B %Y")
    un = runs["uncorrected"][2]
    s = now_card["summary"]
    out = {
        "field": field["id"], "field_name": field["name"], "date": st["date"], "as_of_label": f"as of {as_of_label}",
        "plan": current_id, "plan_role": "current", "rotation": [sp["crop"] for sp in specs],
        "water_case": case, "water_source": water_source,
        "crop": st["crop"], "crop_sown": st["crop_sown"], "crop_day": st["crop_day"], "crop_season_days": sown_len,
        "dr_mm": round(st["dr_mm"], 3), "taw_mm": round(st["taw_mm"], 3), "raw_mm": round(st["raw_mm"], 3),
        "ks": round(st["ks"], 4), "wetness_pct": round(st["wetness_pct"], 2),
        "zr_m": zr, "theta_fc_m3m3": round(fc, 5), "theta_wp_m3m3": round(wp, 5),
        "p0_var": round(nums["p0_var"], 3), "prior_var": round(nums["prior_var"], 3),
        "sure_prior": round(nums["sure_prior"], 3), "q_var_per_day": round(nums["q_var_per_day"], 4),
        "aged_today": {"date": str(today.date()), "days_after_as_of": days_old, "var": round(aged, 3),
                       "sure": round(kf.sure(aged, p0), 3),
                       "rule": "rules.yaml probe.kalman.age_after_as_of: P = min(prior_var + Q x days, P0); x unchanged"},
        "uncorrected_rain": {"wetness_pct": round(un["wetness_pct"], 2), "dr_mm": round(un["dr_mm"], 3), "ks": round(un["ks"], 4)},
        "smap_fit": {"days": fit["n_days"], "first": fit["first"], "last": fit["last"], "r": round(fit["r"], 4),
                     "one_minus_r2": round(fit["rho"], 4), "k_pct_per_m3m3": round(fit["k"], 2),
                     "phi": round(fit["phi"], 4) if fit["phi"] is not None else None,
                     "near_as_of": {k: round(v, 4) if isinstance(v, float) else v for k, v in fit["near_as_of"].items()}},
        "weather": {"as_of_limited_by": s["limited_by"], "last_day_by_power_input": s["last_day_by_power_input"],
                    "imerg_late_last_day": s["imerg_late_last_day"], "weather_now_days": s["days"]},
        "sources": [
            {"name": "NASA POWER", "product": "Daily API (MERRA-2; GEOS-IT and FLASHFlux for the latest weeks); temperatures "
                                              "corrected to Kathmandu Airport", "resolution": "0.5 x 0.625 deg (sunshine 1 x 1 deg)",
             "years": f"2001-{pd.Timestamp(st['date']).year}", "type": "model"},
            {"name": "GPM IMERG", "product": "V07 Final daily to Sep 2025, then Late daily; days from 2017 scaled back to its own "
                                             "2001-2016 level", "resolution": "0.1 deg (about 10 km)",
             "years": f"2001-{pd.Timestamp(st['date']).year}", "type": "satellite"},
            {"name": "ISRIC SoilGrids 2.0", "product": "water held at field capacity and wilting point (nearest cell with values)",
             "resolution": "250 m", "years": "map", "type": "model"},
            {"name": "NASA SMAP L4", "product": "SPL4SMGP v008 root-zone soil moisture, model-assisted (sets how sure the twin is "
                                                "alone, nothing else)", "resolution": "9 km", "years": f"{fit['first'][:4]}-{fit['last'][:4]}",
             "type": "model"},
            {"name": "Field twin", "product": "FAO-56 soil-water bucket, the current plan, " + case, "resolution": "the whole field",
             "years": f"2001-{pd.Timestamp(st['date']).year}", "type": "model"}],
        "labels": {
            "as_of": f"The twin's soil water {('as of ' + as_of_label)}: the last day with both NASA POWER's weather (its sunshine "
                     "comes last) and GPM IMERG Late rain. Nothing after it is guessed.",
            "plan": plans["labels"]["current"], "water_case": f"{case} (water source {water_source})",
            "wetness": "100 x (1 - Dr/TAW): 0 = wilting point, 100 = field capacity, over the root zone (model-based)",
            "ks": "FAO-56 eq. 84 from the end-of-day depletion: 1 = no water stress",
            "p0": f"P0 = what the calendar alone tells: the variance across 2002-2025 of the twin's wetness within "
                  f"{K['p0']['half_window_days']} days of this day of year (percent points squared)",
            "prior": "prior_var = P0 x (1 - r^2), r = correlation of the daily anomalies of the twin and NASA SMAP L4 "
                     f"(r = {fit['r']:.2f} over {fit['n_days']} days). An upper bound on the twin's error only if SMAP's errors are "
                     "independent of the twin's; SMAP L4 is itself a model, at 9 km and 0-100 cm, not this field's root zone",
            "q": "Q = prior_var x (1 - phi^2), phi = lag-1 autocorrelation of the twin-minus-SMAP residual: how fast the twin's "
                 "error grows back after a probe reading",
            "bare_soil": f"bare-soil evaporation as rules.yaml bare_soil says (apply {rules['bare_soil'].get('apply')}), passed as scripts/run_plans.py passes it",
            "rain": "GPM's rain from 2017 is scaled back to its 2001-2016 level (the gauges behind it stopped reporting); "
                    "uncorrected_rain is the same state on GPM as published",
            "placeholder": "PLACEHOLDER field and rotation" if field.get("placeholder") else ""},
        "made_by": "scripts/run_twin_now.py (rules.yaml probe.kalman)",
    }
    path = clean / "twin_state.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{out['as_of_label']}: {st['crop']} (day {st['crop_day']}), Dr {st['dr_mm']:.1f} of TAW {st['taw_mm']:.1f} mm, "
          f"RAW {st['raw_mm']:.1f}, Ks {st['ks']:.3f}, wetness {st['wetness_pct']:.1f}% (GPM as published "
          f"{un['wetness_pct']:.1f}%); Zr {zr} m ({zr_crop}), theta fc {fc:.3f} wp {wp:.3f}")
    print(f"P0 {p0:.2f}; SMAP r {fit['r']:.3f} over {fit['n_days']} days (near as-of r {fit['near_as_of']['r']:.3f}, "
          f"{fit['near_as_of']['n_days']} days); 1 - r^2 {fit['rho']:.3f}; phi {fit['phi']:.4f}")
    print(f"prior_var {nums['prior_var']:.2f}, sure_prior {nums['sure_prior']:.3f}, Q {nums['q_var_per_day']:.3f}/day; "
          f"aged {days_old} days to {today.date()}: var {aged:.2f}, sure {kf.sure(aged, p0):.3f}")
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
