"""Build step 9: the 2040 outlook from NEX-GDDP-CMIP6 (rules.yaml future, committed before the first download).

    .venv/bin/python scripts/run_future.py --field demo

1. Rebuilds data/clean/<field>/nexgddp_daily.parquet and its card from every model complete in the cell's cache
   (pipeline/fetch/nexgddp.py; the download can still be running: only complete models are used, and listed).
2. Per model and scenario, the monthly change 1995-2014 -> 2026-2040 (pipeline/future/deltas.py), applied to the observed
   2001-2025 weather; ET0 rebuilt as weather.py builds it, relative humidity held.
3. Every plan shown (data/checks/<field>/plans.json `shown`) and every current-plan option, replayed rain-fed and
   irrigated as scripts/run_plans.py evaluate() does (pipeline/future/runs.py), with no change (the baseline) and with
   each model-scenario change, for both rain versions (corrected, the default, and uncorrected).
4. The slider grid (rain x 1.0-0.7 by warming +0 to +2 C) on the observed weather: needs no model.
Writes data/checks/<field>/future.json. With fewer complete models than rules.yaml future.min_models the outlook is
'NOT YET' (the slider grid is still written).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch import nexgddp as nx  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.future import deltas as dl  # noqa: E402
from pipeline.future import runs as ru  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.plans import twin_options as to  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402

VERSIONS = ("corrected", "uncorrected", "dhm")   # dhm: owner's decision 4b (2026-11-14), the range's dry edge
ROLES = ("current", "cover_gap", "safest")


def specs_from_id(pid):
    """'rice.w1.middle+potato.w0.middle' -> the plan's season options (plans.generate.plan_id, read back)."""
    out = []
    for part in pid.split("+"):
        crop, w, pos = part.split(".")
        out.append({"crop": crop, "window": int(w.lstrip("w")), "position": pos})
    return out


def plans_to_run(plans_json):
    """{plan id: specs} and {key: plan id} for the three plans shown and every current-plan option."""
    by_id = {r["id"]: r for r in plans_json["plans"]}
    keys = {role: plans_json["shown"][role] for role in ROLES}
    for o in plans_json.get("current_options", []):
        keys[f"option:{o['id']}"] = o["plan"]
    specs = {pid: (by_id[pid]["specs"] if pid in by_id else specs_from_id(pid)) for pid in set(keys.values())}
    return specs, keys


def elevation(field, cards_dir):
    """The elevation weather.py used for ET0: the field's own, else POWER's cell elevation."""
    if field.get("elevation_m") is not None:
        return float(field["elevation_m"]), "field config"
    return float(json.loads((cards_dir / "power.json").read_text())["location"]["elevation_m"]), "POWER cell elevation"


def check_reproduces(w, elev_m, lat):
    """A zero change must give back weather.py's ea_kpa and ET0 (otherwise the rebuild is not 'as weather.py builds it')."""
    z = dl.apply_change(w, dl.uniform_change(0.0, 1.0), elev_m, lat)
    diff = {c: float(np.nanmax(np.abs(z[c].to_numpy(float) - w[c].to_numpy(float))))
            for c in ("ea_kpa", "et0_mm", "et0_rh_held_mm")}
    if max(diff.values()) > 1e-9:
        raise RuntimeError(f"a zero change does not reproduce the weather table: {diff}")
    return diff


def r2(x):
    return None if x is None else round(float(x), 2)


def summarise_plan(base, runs, scenarios):
    out = {"baseline": {k: r2(v) if k != "years" else v for k, v in base.items()},
           "runs": [{k: (r2(v) if isinstance(v, float) else v) for k, v in r.items() if k != "years"} for r in runs]}
    if not runs:
        return out
    h = ru.spread(runs, "harvest")
    out["outlook"] = {"harvest": r2(h["median"]), "harvest_low": r2(h["low"]), "harvest_high": r2(h["high"]),
                      "low_run": h["low_run"], "high_run": h["high_run"], "n_runs": h["n"],
                      "change_from_baseline": r2(h["median"] - base["harvest"])}
    by = {}
    for s in scenarios:
        rs = [r for r in runs if r["scenario"] == s]
        d = [{"run": r["run"], "v": r["dry_days"] - base["dry_days"]} for r in rs]
        i = [{"run": r["run"], "v": r["irrigation_mm"] - base["irrigation_mm"]} for r in rs]
        by[s] = {"harvest": {k: r2(v) if isinstance(v, float) else v for k, v in ru.spread(rs, "harvest").items()},
                 "dry_days_change": {k: r2(v) if isinstance(v, float) else v for k, v in ru.spread(d, "v").items()},
                 "irrigation_mm_change": {k: r2(v) if isinstance(v, float) else v for k, v in ru.spread(i, "v").items()}}
    out["by_scenario"] = by
    return out


def deltas_summary(changes, scenarios):
    out = {}
    for s in scenarios:
        cs = {m: c for (m, sc), c in changes.items() if sc == s}
        row = {}
        for k in ("dtmax_c", "dtmin_c", "dtas_c", "rain_change_pct"):
            v = [{"run": m, "v": c["annual"][k]} for m, c in cs.items()]
            row[f"annual_{k}"] = {kk: r2(vv) if isinstance(vv, float) else vv for kk, vv in ru.spread(v, "v").items()}
        rr = [(c["rain_ratio"][mo], m, mo) for m, c in cs.items() for mo in range(1, 13)]
        row["largest_rain_ratio"] = dict(zip(("ratio", "model", "month"), (r2(max(rr)[0]), *max(rr)[1:])))
        row["smallest_rain_ratio"] = dict(zip(("ratio", "model", "month"), (r2(min(rr)[0]), *min(rr)[1:])))
        row["median_monthly"] = {k: {mo: r2(np.median([c[k][mo] for c in cs.values()])) for mo in range(1, 13)}
                                 for k in ("dtmax_c", "dtmin_c", "rain_ratio")}
        out[s] = row
    return out


def contract_proposal(plans_out, keys, version="corrected"):
    """One way to fill the field file's `future` ({years, nothing_changes, with_plan}): years [2040] standing for
    2026-2040; nothing_changes = the current plan, with_plan = the cover-the-gap plan; per plan and option the same three
    numbers and the baseline (today's climate, the 2002-2025 replay). Integers, so low <= harvest <= high holds."""
    def three(pid):
        o = plans_out[pid][version]["outlook"]
        return {"harvest": [int(round(o["harvest"]))], "harvest_low": [int(round(o["harvest_low"]))],
                "harvest_high": [int(round(o["harvest_high"]))]}
    prop = {"years": [2040], "nothing_changes": three(keys["current"]), "with_plan": three(keys["cover_gap"])}
    per = {k: {**{kk: vv[0] for kk, vv in three(pid).items()},
               "today": int(round(plans_out[pid][version]["baseline"]["harvest"]))} for k, pid in keys.items()}
    return {"future": prop, "per_plan": per}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--models", default=None, help="comma-separated subset of the complete models (checks only)")
    ap.add_argument("--no-build", action="store_true", help="use the existing nexgddp_daily.parquet")
    a = ap.parse_args(argv)
    t0 = time.time()
    field, rules, lib = load_field(a.field), load_rules(), load_crops()
    F = rules["future"]
    clean, cards, out_dir = (REPO / "data" / d / field["id"] for d in ("clean", "cards", "checks"))
    w = pd.read_parquet(clean / "weather.parquet")
    problems = sim.rain_record_problems(w)
    if problems:
        print("NOT YET POSSIBLE: " + "; ".join(problems))
        return 2
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    cov, byc = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": byc["bare"], **{c: byc[cov[c]] for c in cov}}
    pj = json.loads((out_dir / "plans.json").read_text())
    specs, keys = plans_to_run(pj)
    # items 4a and 4c as run_plans: the farmer's plans (the current plan and its options) take the satellite's seasons
    sj_path = out_dir / "diary_seasons.json"
    to.attach(rules, to.hls_seasons(json.loads(sj_path.read_text())) if sj_path.exists() else None,
              {pj["shown"]["current"], *(o["plan"] for o in pj.get("current_options", []))})
    elev_m, elev_src = elevation(field, cards)
    lat = float(field["lat"])
    repro = check_reproduces(w, elev_m, lat)

    # the models complete now
    models, card, daily = [], None, None
    try:
        if not a.no_build:
            nx.build(field, REPO / "data", REPO / "data" / "raw" / "nexgddp")
        daily = pd.read_parquet(clean / "nexgddp_daily.parquet")
        card = json.loads((cards / "nexgddp.json").read_text())
        models = [m for m in card["summary"]["fetch_order"] if m in set(daily["model"])]
        if a.models:
            models = [m for m in models if m in a.models.split(",")]
    except (RuntimeError, FileNotFoundError) as e:
        print(f"no NEX-GDDP-CMIP6 model ready: {e}")
    ready = len(models) >= F["min_models"]
    changes = {}
    if ready:
        for m in models:
            for s in F["scenarios"]:
                changes[(m, s)] = dl.model_change(daily, m, s, F["periods"], F["rain_ratio_window_months"])

    plans_out, grid = {pid: {} for pid in specs}, {}
    for v in VERSIONS:
        if v == "dhm":
            sys.path.insert(0, str(REPO / "scripts"))
            from run_plans import dhm_rain
            wv = with_rain(w, v, dhm=dhm_rain(rules))
        else:
            wv = with_rain(w, v)
        base = {pid: ru.plan_run(sp, wv, lib, soil, cn, rules) for pid, sp in specs.items()}
        runs = {pid: [] for pid in specs}
        for (m, s), ch in changes.items():
            wc = dl.apply_change(wv, ch, elev_m, lat)
            for pid, sp in specs.items():
                r = ru.plan_run(sp, wc, lib, soil, cn, rules)
                runs[pid].append({"run": f"{m} {s}", "model": m, "scenario": s, **r})
        for pid in specs:
            if base[pid]["years"] != (runs[pid][0]["years"] if runs[pid] else base[pid]["years"]):
                raise RuntimeError(f"{pid}: the changed runs cover other years than the baseline")
            plans_out[pid][v] = summarise_plan(base[pid], runs[pid], F["scenarios"])
        g = {pid: {"harvest": [], "dry_days": [], "irrigation_mm": []} for pid in specs}
        for rf in F["slider_grid"]["rain_factor"]:
            rows = {pid: {"harvest": [], "dry_days": [], "irrigation_mm": []} for pid in specs}
            for wm in F["slider_grid"]["warming_c"]:
                wc = dl.apply_change(wv, dl.uniform_change(wm, rf), elev_m, lat)
                for pid, sp in specs.items():
                    r = ru.plan_run(sp, wc, lib, soil, cn, rules)
                    for k in rows[pid]:
                        rows[pid][k].append(r2(r[k]))
            for pid in specs:
                for k in g[pid]:
                    g[pid][k].append(rows[pid][k])
        grid[v] = g
        print(f"{v}: {len(changes)} model-scenario runs, slider grid done, {time.time() - t0:.0f} s", flush=True)

    # plans.json reproduced? (same code, same weather: the baseline should equal its harvest)
    by_id = {r["id"]: r for r in pj["plans"]}
    reproduce = {pid: {"plans_json": r2(by_id[pid]["harvest"]) if pid in by_id else None,
                       "baseline": r2(plans_out[pid]["corrected"]["baseline"]["harvest"])} for pid in specs}
    commit = subprocess.run(["git", "log", "-1", "--format=%h", "--", "config/rules.yaml"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    out = {
        "labels": {"field": field["name"], "placeholder": bool(field.get("placeholder")),
                   "status": "computed" if ready else f"NOT YET: {len(models)} complete model(s), the rule needs "
                                                     f"{F['min_models']} (rules.yaml future.min_models)",
                   "rules": "config/rules.yaml future", "rules_commit_at_run": commit,
                   "method": F["method"], "humidity": F["humidity"], "rain_window_months": F["rain_ratio_window_months"],
                   "periods": F["periods"], "scenarios": F["scenarios"], "water_case": "rain-fed harvest; irrigation_mm "
                   "from the irrigated run", "rain_caveat": rules["gpm_series"]["trend_caveat"],
                   "elevation_m": elev_m, "elevation_source": elev_src, "zero_change_max_diff": repro,
                   "years": plans_out[next(iter(specs))]["corrected"]["baseline"]["years"]},
        "models": models, "n_models": len(models),
        "models_not_used": (card or {}).get("summary", {}).get("left_out_or_incomplete", {}),
        "cell": (card or {}).get("location"), "keys": keys,
        "deltas": {f"{m} {s}": {k: ({str(mo): r2(x) for mo, x in v.items()} if k != "annual" else
                                    {kk: (r2(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()})
                                for k, v in c.items()} for (m, s), c in changes.items()},
        "deltas_summary": (ds := deltas_summary(changes, F["scenarios"]) if ready else None),
        "plausibility": ({"rule": "rules.yaml future.plausibility", **dl.compare_published(ds, F["plausibility"])}
                         if ready and "plausibility" in F else None),
        "plans": {pid: {"specs": specs[pid], **plans_out[pid]} for pid in specs},
        "slider_grid": {"rain_factor": F["slider_grid"]["rain_factor"], "warming_c": F["slider_grid"]["warming_c"],
                        "layout": "values[plan][key][i_rain_factor][i_warming]", "values": grid},
        "reproduces_plans_json": reproduce,
        "contract_proposal": contract_proposal(plans_out, keys) if ready else None,
        "words_proposed": {
            "range_en": ["Computers guessed the weather in 2040.", "Each one guessed a little differently.",
                         "Your harvest will likely land in between."],
            "method_en": (f"2040 outlook: for each of {len(models)} climate models (NEX-GDDP-CMIP6; scenarios SSP2-4.5 "
                          "and SSP5-8.5), the change in monthly rain and temperature from 1995-2014 to 2026-2040 at the "
                          "field's 25 km cell is applied to the field's own 2001-2025 weather and every plan is replayed; "
                          "the mark is the median run and the band runs from the lowest to the highest. Humidity, wind "
                          "and sunshine stay as observed."),
            "source_entry": {"name": "NEX-GDDP-CMIP6", "product": "daily, bias-corrected and downscaled (BCSD), v2.0",
                             "resolution": "0.25 deg", "years": "1995-2014 and 2026-2040", "type": "model"}},
    }
    path = out_dir / "future.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"{len(models)} model(s) {'(outlook computed)' if ready else '(outlook NOT YET)'}: {models}")
    for k, pid in keys.items():
        o = plans_out[pid]["corrected"]
        line = f"{k:22s} {pid:34s} today {o['baseline']['harvest']:5.1f}"
        if ready:
            oo = o["outlook"]
            line += f"  2026-2040 median {oo['harvest']:5.1f} [{oo['harvest_low']:5.1f}, {oo['harvest_high']:5.1f}]"
            for s in F["scenarios"]:
                b = o["by_scenario"][s]
                line += (f" | {s} {b['harvest']['median']:5.1f} dry {b['dry_days_change']['median']:+5.1f} d "
                         f"irr {b['irrigation_mm_change']['median']:+6.1f} mm")
        print(line)
    if ready:
        for s, row in out["deltas_summary"].items():
            print(f"{s}: dTmax {row['annual_dtmax_c']['median']:+.2f} C [{row['annual_dtmax_c']['low']:+.2f}, "
                  f"{row['annual_dtmax_c']['high']:+.2f}], dTmin {row['annual_dtmin_c']['median']:+.2f} C, rain "
                  f"{row['annual_rain_change_pct']['median']:+.1f}% [{row['annual_rain_change_pct']['low']:+.1f}, "
                  f"{row['annual_rain_change_pct']['high']:+.1f}]; largest monthly ratio {row['largest_rain_ratio']}")
    if out["plausibility"]:
        print(f"plausibility (VALIDATION 4.7): {out['plausibility']}")
    print(f"-> {path.relative_to(REPO)} ({time.time() - t0:.0f} s)")
    return 0 if ready else 3


if __name__ == "__main__":
    sys.exit(main())
