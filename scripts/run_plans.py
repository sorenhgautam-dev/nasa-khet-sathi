"""Build step 7 (first part): generate every plan, replay each through 2001-2025 in both water cases, score them,
keep the Pareto set and pick the three to show. Writes data/checks/<field>/plans.json.

    .venv/bin/python scripts/run_plans.py --field demo

Rules in config/rules.yaml (plans, erosion, ky_assumed). Pure functions in pipeline/plans/.
--rain uncorrected (owner's decision 1, 2026-11-13) reruns everything on GPM as published and writes to
data/checks/<field>/rain_uncorrected/plans.json; the default is the twin's corrected rain.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import events as ev  # noqa: E402
from pipeline.diary import guess as gu  # noqa: E402
from pipeline.plans import generate as ge  # noqa: E402
from pipeline.plans import options as po  # noqa: E402
from pipeline.plans import score as sc  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.plans import twin_options as to  # noqa: E402
from pipeline.twin.crops import season_length, simulatable_crops  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402
from scripts.common import RAIN_DIRS, SOIL_DIRS, add_switches, rain_kw, set_switches, soil_for, switch_labels, write_json  # noqa: E402


def _by_slot(sj):
    """The satellite's seasons (HLS) by slot, for the current-plan options (pipeline/plans/options.py)."""
    by_slot = {k: [] for k in gu.SLOTS}
    for rows_y in sj["chosen"]["seasons_by_year"].values():
        for s in rows_y:
            if s["source"] == "hls":
                t_ = {k: pd.Timestamp(s[k]) for k in ("start", "peak", "end")}
                by_slot[gu.slot_of(t_)].append(t_)
    return by_slot


def _mmdd(t):
    return pd.Timestamp(t).strftime("%m-%d")


def evaluate(specs, w, lib, soil, cn, rules, strict, erosion=None, years_max=None):
    crops = [sp["crop"] for sp in specs]
    plan = ge.plan_dates(specs, lib, w["date"].min(), w["date"].max())
    farmer = to.is_farmer(specs, rules)        # item 4a: only the farmer's plans take the satellite's dates
    rf = to.replay(w, crops, lib, soil, cn, rules, irrigated=False, plan=plan, farmer=farmer)
    ir = to.replay(w, crops, lib, soil, cn, rules, irrigated=True, plan=plan, farmer=farmer)
    ok = {y["year"] for y in sc.complete(rf["years"], crops)}
    if years_max:
        ok = {y for y in ok if y <= years_max}
    rf_years = [y for y in rf["years"] if y["year"] in ok]
    ir_years = [y for y in ir["years"] if y["year"] in ok]
    etc = {}
    for s in ir["seasons"]:
        if s["year"] in ok:
            etc[s["year"]] = etc.get(s["year"], 0.0) + float(s["sum_etc_mm"])
    irr = float(np.mean([y["irrigation_mm"] for y in ir_years]))
    losses = to.irrigation_losses(ir_years, rules)  # rules.yaml paddy_losses.water_score: None while the losses are off
    etc_mm = float(np.mean(list(etc.values())))
    cover_days = sum(season_length(lib[c]["stages_days"]) for c in crops)
    row = {"id": ge.plan_id(specs), "specs": specs, "crops": crops,
           "spans": [{"crop": sp["crop"], "start": _mmdd(a), "end": _mmdd(b)}
                     for sp in specs for a, b in [ge.season_in_year(sp, lib, ge.REF_YEAR)]],
           "years": sorted(ok), **sc.harvest_metrics(rf_years), "irrigation_mm": round(irr, 1), "etc_mm": round(etc_mm, 1),
           "water": sc.water_score(irr if losses is None else irr - losses, etc_mm, strict),
           **({} if losses is None else {"irrigation_losses_mm": round(losses, 1)}), "cover": round(sc.cover_score(cover_days), 1),
           "pest_break": int(sc.pest_break(crops, lib)), "nitrogen": int(sc.has_legume(crops, lib)),
           "needs_water_window": any("irrigat" in str(lib[sp["crop"]]["calendar"]["windows"][sp["window"]].get("note", "")).lower()
                                     and "rainfed" not in str(lib[sp["crop"]]["calendar"]["windows"][sp["window"]].get("note", "")).lower()
                                     for sp in specs),
           "ky_assumed": any(lib[c].get("ky_assumed") for c in crops)}
    for v in rules["ky_assumed"]["sensitivity"]:
        ys = [y for y in sim.yearly(sim.seasons_with_ky(rf["seasons"], lib, v)) if y["year"] in ok]
        m = sc.harvest_metrics(ys)
        row[f"harvest_ky{v}"], row[f"stability_ky{v}"] = m["harvest"], m["stability"]
    if erosion:
        rain = w.set_index("date")["rain_mm"]
        seasons = [(c, s, str((pd.Timestamp(s) + pd.Timedelta(season_length(lib[c]["stages_days"]) - 1, unit="D")).date()))
                   for c, s in rf["plan"]]                    # the dates the rain-fed twin ran (items 4a, 4c)
        c = sc.daily_c(rain.index, seasons, erosion["c_by_crop"], erosion["c_bare"])
        wt = sc.month_weight(rain.index.month, erosion["month_amplitude"])
        for key, beta in (("soil_kept", erosion["beta"]), ("soil_kept_beta_1_81", 1.81)):
            e_plan = sc.erosion_index(rain.to_numpy(), c, erosion["threshold_mm"], beta, weight=wt)
            e_bare = sc.erosion_index(rain.to_numpy(), np.full(len(rain), erosion["c_bare"]), erosion["threshold_mm"], beta, weight=wt)
            row[key] = sc.soil_kept_score(e_plan, e_bare)
    return row


def plan_export(specs, w, lib, soil, cn, rules, labels):
    """One plan replayed for the field file, in the shape of run_replay's export (build_field_json.apply_replay):
    rain-fed years with their events, the watered years beside them, and per crop the month it is most often
    thirsty (rain-fed: days with Ks < 1), for the tips."""
    crops = [sp["crop"] for sp in specs]
    plan = ge.plan_dates(specs, lib, w["date"].min(), w["date"].max())
    farmer = to.is_farmer(specs, rules)        # item 4a: only the farmer's plans take the satellite's dates
    rf = to.replay(w, crops, lib, soil, cn, rules, irrigated=False, plan=plan, farmer=farmer)
    ir = to.replay(w, crops, lib, soil, cn, rules, irrigated=True, plan=plan, farmer=farmer)
    daily = rf["daily"]
    n_years = len({y["year"] for y in sc.complete(rf["years"], crops)})
    thirsty = {}
    for c in dict.fromkeys(crops):
        d = daily[(daily["crop"] == c) & daily["dry_day"]]
        if len(d):
            by_month = d.groupby(pd.DatetimeIndex(d["date"]).month).size()
            thirsty[c] = {"month": int(by_month.idxmax()), "dry_days_per_year": round(float(by_month.max()) / n_years, 1)}
    # one weather event per year for the field, the same on every plan (owner's answer 9 to REVIEW_2, 2026-11-13)
    fe = ev.field_year_events(pd.Series(w["rain_mm"].to_numpy(float), index=pd.DatetimeIndex(w["date"])), rules["events"])
    return {"labels": {**labels, "rotation": crops, "plan": ge.plan_id(specs)},
            "years": rf["years"], "irrigated_years": ir["years"], "events": fe["events"],
            "event_seasons": fe["event_seasons"], "event_detail": fe["detail"], "thirsty": thirsty}


def gain_range(specs_plan, specs_current, w, lib, soil, cn, rules):
    """Owner's answer 4 to REVIEW_2 (2026-11-13; rules.yaml plans.gain_range): the plan's mean harvest minus the current
    plan's, with each of their crops at the smaller and at the larger root depth of its FAO-56 Table 22 range (every
    combination, a crop having the same depth in both plans). Returns {low, high, runs}."""
    import copy
    import itertools
    crops = sorted({sp["crop"] for sp in list(specs_plan) + list(specs_current)})
    runs = []
    for combo in itertools.product(*[lib[c]["zr_range_m"] for c in crops]):
        lib2 = copy.deepcopy(lib)
        for c, z in zip(crops, combo):
            lib2[c]["zr_m"] = z
        hp = evaluate(specs_plan, w, lib2, soil, cn, rules, 1.0)["harvest"]
        hc = evaluate(specs_current, w, lib2, soil, cn, rules, 1.0)["harvest"]
        runs.append({"zr_m": dict(zip(crops, combo)), "plan": round(hp, 2), "current": round(hc, 2), "gain": round(hp - hc, 2)})
    return {"low": min(r["gain"] for r in runs), "high": max(r["gain"] for r in runs), "runs": runs}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--rain", choices=tuple(RAIN_DIRS), default="corrected")
    ap.add_argument("--out-dir", default=None,
                    help="write plans.json here instead of data/checks/<field>/ (a check run; the diary is still read there)")
    add_switches(ap)
    a = ap.parse_args(argv)
    field, rules, lib = load_field(a.field), load_rules(), load_crops()
    set_switches(rules, a)
    clean = REPO / "data" / "clean" / field["id"]
    out_dir = REPO / "data" / "checks" / field["id"]                 # inputs (diary) are always read here
    dest = (REPO / a.out_dir) if a.out_dir else out_dir
    w = with_rain(pd.read_parquet(clean / "weather.parquet"), a.rain, **rain_kw(rules, a.rain, field["id"]))
    problems = sim.rain_record_problems(w)
    if problems:
        print("NOT YET POSSIBLE: " + "; ".join(problems))
        return 2
    soil = soil_for(a.soil, rules, field["id"], pd.read_parquet(clean / "soilgrids.parquet"), REPO / "data")
    if soil is None:
        print("NOTHING TO RUN: --soil measured needs rules.yaml field_capacity_measured.apply and "
              f"data/field_visit/{field['id']}/field_capacity.csv")
        return 0
    cov, by = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by["bare"], **{c: by[cov[c]] for c in cov}}
    diary = json.loads((out_dir / "diary.json").read_text())
    falling = diary["export"]["groundwater"]["direction"] == "falling"
    P = rules["plans"]
    strict = P["water_strict_when_falling"] if falling else 1.0
    erosion = rules.get("erosion")
    crops = sorted(simulatable_crops(lib))
    plans = ge.generate(lib, crops, tuple(P["sow_positions"]), P["max_seasons"])
    rotation, rot_label = sim.rotation_for(field, rules)
    current_specs = ge.ordered([{"crop": c, "window": lib[c]["calendar"]["default"], "position": "middle"} for c in rotation], lib)
    current_id = ge.plan_id(current_specs)
    if current_id not in {ge.plan_id(p) for p in plans}:
        plans.append(current_specs)
    # item 4a (rules.yaml season_dates): the farmer's plans (the current plan and the current-plan options) take the
    # satellite's dates; every other plan keeps its calendar (season_dates.suggested_plans)
    sj_path = out_dir / "diary_seasons.json"
    sj_early = json.loads(sj_path.read_text()) if sj_path.exists() else None
    farmer_ids = {current_id}
    for i_, rot_ in enumerate(field.get("current_rotation_options") or []):
        if i_ and sj_early:
            farmer_ids.add(ge.plan_id(po.option_specs(list(rot_), current_specs, _by_slot(sj_early), lib, tuple(P["sow_positions"]))[0]))
    to.attach(rules, to.hls_seasons(sj_early) if sj_early else None, farmer_ids)
    keys = [k for k in P["pareto_keys"] if k != "soil_kept" or erosion]
    t0 = time.time()
    rows, rows_pre = [], []
    for i, specs in enumerate(plans):
        rows.append(evaluate(specs, w, lib, soil, cn, rules, strict, erosion))
        rows_pre.append(evaluate(specs, w, lib, soil, cn, rules, strict, erosion, years_max=2016))
        if i % 50 == 0:
            print(f"  {i}/{len(plans)} plans, {time.time() - t0:.0f} s", file=sys.stderr)
    must = P["suggested_must_include"]
    picks = sc.choose_three(rows, current_id, keys, must)
    checks = {"pre_2017_only": sc.choose_three(rows_pre, current_id, keys, must)}
    for v in rules["ky_assumed"]["sensitivity"]:
        alt = [{**r, "harvest": r[f"harvest_ky{v}"], "stability": r[f"stability_ky{v}"]} for r in rows]
        checks[f"ky_{v}"] = sc.choose_three(alt, current_id, keys, must)
    by_id = {r["id"]: r for r in rows}
    corrected_path = dest / "plans.json"                         # the corrected run of the same destination
    if (a.rain != "corrected" or a.soil != "map") and corrected_path.exists():   # chosen on the corrected rain, map soil
        shown = json.loads(corrected_path.read_text())["picks"]
    else:
        shown = picks
    water = field.get("water_source") or "unknown"
    exports = {}
    for role in ("current", "cover_gap", "safest"):
        r = by_id[shown[role]]
        lab = {"field": field["name"], "rain_source": "gpm", "rain_version": a.rain, "water_source": water,
               "rotation_source": rot_label if role == "current" else
               f"suggested plan '{P['plan_names'][role]}' ({rules['plans']['third_plan_rule'] if role == 'safest' else rules['plans']['cover_gap_rule']}); "
               + ("PLACEHOLDER field" if field.get("placeholder") else "")}
        exports[role] = {"id": role, "plan": r["id"], "name": P["plan_names"][role], "spans": r["spans"],
                         "score": {k: r[k] for k in ("harvest", "water", "cover", "soil_kept")},
                         "stability": r["stability"], "pest_break": r["pest_break"], "nitrogen": r["nitrogen"],
                         "needs_water_window": r["needs_water_window"], "ky_assumed": r["ky_assumed"],
                         "replay": plan_export(r["specs"], w, lib, soil, cn, rules, lab)}
        if role != "current":
            exports[role]["gain_range"] = gain_range(r["specs"], by_id[shown["current"]]["specs"], w, lib, soil, cn, rules)
    # owner's answer 6 to REVIEW_2 (2026-11-13; rules.yaml plans.current_options): the current plan once for each
    # rotation the farmer may confirm, each compared with the suggested plans (which stay as chosen)
    current_options = []
    rot_options = [list(r) for r in (field.get("current_rotation_options") or [])]
    if rot_options:
        if rot_options[0] != list(rotation):
            raise ValueError("config: the first entry of current_rotation_options must be the field's current_rotation")
        by_slot = _by_slot(json.loads((out_dir / "diary_seasons.json").read_text()))
        for i, rot in enumerate(rot_options):
            specs, why = (current_specs, {}) if i == 0 else po.option_specs(rot, current_specs, by_slot, lib, tuple(P["sow_positions"]))
            r = by_id.get(ge.plan_id(specs)) or evaluate(specs, w, lib, soil, cn, rules, strict, erosion)
            lab = {"field": field["name"], "rain_source": "gpm", "rain_version": a.rain, "water_source": water,
                   "rotation_source": f"current-plan option {'_'.join(rot)} (owner's answer 6, 2026-11-13: the farmer confirms the "
                                      "winter crop); " + ("PLACEHOLDER field" if field.get("placeholder") else "")}
            current_options.append({
                "id": "_".join(rot), "plan": r["id"], "rotation": rot, "spans": r["spans"],
                "score": {k: r[k] for k in ("harvest", "water", "cover", "soil_kept")}, "stability": r["stability"],
                "pest_break": r["pest_break"], "nitrogen": r["nitrogen"], "needs_water_window": r["needs_water_window"],
                "ky_assumed": r["ky_assumed"], "date_fit": why,
                "replay": plan_export(r["specs"], w, lib, soil, cn, rules, lab),
                "gain_range": {role: gain_range(by_id[shown[role]]["specs"], r["specs"], w, lib, soil, cn, rules)
                               for role in ("cover_gap", "safest")}})
            print(f"current option {current_options[-1]['id']:14s} {r['id']:36s} harvest {r['harvest']:5.1f} stability {r['stability']:5.1f} "
                  f"gains {[(k, v['low'], v['high']) for k, v in current_options[-1]['gain_range'].items()]} fit {why}")
    out = {"labels": {"field": field["name"], "current": f"{rotation} ({rot_label})", "water_case": "rain-fed (water source unknown)",
                      "water_strict": strict, "soil_kept": "computed" if erosion else "NOT YET: rules.yaml erosion (C factors) pending",
                      "rain_version": a.rain, "rain_caveat": rules["gpm_series"]["trend_caveat"],
                      "pareto_keys": keys},
           "picks": picks, "shown": shown, "export": exports, "current_options": current_options, "robustness": checks,
           "n_plans": len(rows), "plans": rows,
           "plans_2002_2016": rows_pre}
    out["labels"].update(switch_labels(rules, soil, season_dates=to.season_dates_on(rules) and (       # 2a, 4a and 4c
        f"rules.yaml season_dates: the farmer's plans {sorted(farmer_ids)} sown from the satellite's seasons in the HLS "
        "years; suggested plans keep their calendar")))
    if a.soil == "measured":                                   # owner's item 4
        out["labels"]["soil"] = "field capacity measured by the field team; SoilGrids' wilting point (rules.yaml field_capacity_measured)"
    path = write_json(dest / RAIN_DIRS[a.rain] / SOIL_DIRS[a.soil] / "plans.json", out)
    print(f"{len(rows)} plans, {picks['eligible']} with rice, Pareto {len(picks['pareto'])}; safest from the "
          f"{picks['safest_from']}; {time.time() - t0:.0f} s")
    for role in ("current", "cover_gap", "safest"):
        r = by_id[shown[role]]
        print(f"{role:10s} {r['id']:45s} harvest {r['harvest']:5.1f} stability {r['stability']:5.1f} water {r['water']:5.1f} "
              f"cover {r['cover']:5.1f} soil {r.get('soil_kept', '-')} pest {r['pest_break']} N {r['nitrogen']} spans {r['spans']}")
    for k, v in checks.items():
        print(f"check {k}: cover_gap {v['cover_gap']}, safest {v['safest']}")
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
