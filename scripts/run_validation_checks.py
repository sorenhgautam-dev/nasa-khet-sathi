"""Independent checks of the twin with NASA (and FAO) data the twin does not use (VALIDATION 4.2, 4.2c, 4.2d, 4.3;
rules.yaml validation_checks, committed before the first run: fe3223a).

    .venv/bin/python scripts/run_validation_checks.py --field demo [--rain both|corrected|uncorrected]
                                                      [--only ecostress hls faostat gldas]

Re-runnable on the final twin: rerun scripts/run_replay.py (both rain versions) and scripts/run_plans.py first. Where
daily values are needed the twin is rerun in memory with the runners' own switches (pipeline/plans/twin_options.py:
bare-soil setting, rain-fed paddy rule, season dates), and the run STOPS unless those reruns reproduce replay.json's
seasons and the rice-then-wheat option's years in plans.json (rules.yaml validation_checks.common.twin_consistency).

Inputs: data/clean/<field>/ecostress.parquet (pipeline.fetch.ecostress), gldas.parquet (pipeline.fetch.gldas),
faostat_yields.parquet and the FAOSTAT bulk file (potato), weather, soil; data/checks/<field>/replay.json, plans.json,
diary_seasons.json and their rain_uncorrected/ twins. Writes data/checks/<field>/ecostress_check.json, twin_vs_hls.json,
faostat_check.json and gldas_check.json. Checks only: nothing here changes an export.
"""
import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks import ecostress_check as ec  # noqa: E402
from pipeline.checks import faostat_check as fc  # noqa: E402
from pipeline.checks import gldas_check as gc  # noqa: E402
from pipeline.checks import twin_vs_greenness as tg  # noqa: E402
from pipeline.fetch import faostat as fs  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import generate as ge  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.plans import twin_options as to  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402

RULE_COMMIT = "fe3223a"
TOL = 1e-6


class TwinMismatch(RuntimeError):
    pass


def _same_seasons(mine, stored, what):
    if len(mine) != len(stored):
        raise TwinMismatch(f"{what}: {len(mine)} seasons in memory, {len(stored)} stored")
    for a, b in zip(mine, stored):
        if (a["crop"], str(a["start"]), str(a["end"])) != (b["crop"], str(b["start"]), str(b["end"])):
            raise TwinMismatch(f"{what}: season {a['crop']} {a['start']} differs from stored {b['crop']} {b['start']}")
        for k in ("sum_eta_mm", "sum_etc_mm", "harvest_pct"):
            if abs(float(a[k]) - float(b[k])) > TOL:
                raise TwinMismatch(f"{what}: {a['crop']} {a['start']} {k} {a[k]} in memory, {b[k]} stored")


def twin_runs(field, rules, lib, soil, w, checks_dir, data):
    """The rain-fed twin in memory for the current rotation and the rice-then-wheat option, checked against the stored
    outputs. Returns {'current': replay result, 'wheat': replay result or None, 'wheat_plan': id}."""
    rotation, _ = sim.rotation_for(field, rules)
    cov, by = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by["bare"], **{c: by[cov[c]] for c in cov}}
    # every switch of rules.yaml as the runners apply them (pipeline/plans/twin_options.py): bare_soil, season_dates (the
    # farmer's plans on the satellite's seasons), paddy_rainfed (rain-fed paddy on a calendar day waits for its rain)
    sj_path = Path(data) / "checks" / field["id"] / "diary_seasons.json"    # rain-free: one file for every rain version
    hls = to.hls_seasons(json.loads(sj_path.read_text())) if sj_path.exists() else None
    cur = to.replay(w, rotation, lib, soil, cn, rules, irrigated=False, farmer=True, seasons=hls)
    stored = json.loads((checks_dir / "replay.json").read_text())
    _same_seasons(cur["seasons"], stored["rain-fed"]["seasons"], f"{checks_dir.name}/replay.json")
    out = {"current": cur, "rotation": rotation, "wheat": None, "wheat_plan": None}
    plans_path = checks_dir / "plans.json"
    if plans_path.exists():
        pj = json.loads(plans_path.read_text())
        opt = next((o for o in pj.get("current_options", []) if o["id"] == "rice_wheat"), None)
        if opt:
            specs = next(p["specs"] for p in pj["plans"] if p["id"] == opt["plan"]) if any(p["id"] == opt["plan"] for p in pj["plans"]) \
                else [{"crop": c, "window": int(wd[1:]), "position": pos} for c, wd, pos in (x.split(".") for x in opt["plan"].split("+"))]
            crops = [s["crop"] for s in specs]
            wr = to.replay(w, crops, lib, soil, cn, rules, irrigated=False, plan=ge.plan_dates(specs, lib, w["date"].min(),
                           w["date"].max()), farmer=True, seasons=hls)      # a current-plan option: the farmer's plan
            mine = {y["year"]: y["harvest"] for y in wr["years"]}
            for y in opt["replay"]["years"]:
                if abs(mine.get(y["year"], np.nan) - y["harvest"]) > TOL:
                    raise TwinMismatch(f"{plans_path.name} rice_wheat {y['year']}: {mine.get(y['year'])} in memory, {y['harvest']} stored")
            out["wheat"], out["wheat_plan"] = wr, opt["plan"]
    return out


def seasons_of(res, crop=None):
    return [{"crop": s["crop"], "start": str(s["start"]), "end": str(s["end"]), "year": int(s["year"]),
             "eta_over_etc": float(s["eta_over_etc"]), "dry_days": float(s["dry_days"]), "harvest_pct": float(s["harvest_pct"])}
            for s in res["seasons"] if s.get("complete", True) and (crop is None or s["crop"] == crop)]


def check_ecostress(twin, eco, R):
    E = R["ecostress"]
    ss = seasons_of(twin["current"])
    out = {}
    for col in ("esi", "esi_touching"):
        ov = eco[["local_date", col]].rename(columns={col: "esi"})
        se = ec.season_esi(ov, ss)
        out[col] = {slot: ec.slot_result(se[se["slot"] == slot], E["min_overpasses_per_season"], E["min_seasons"])
                    for slot in ("monsoon", "winter")}
    d = twin["current"]["daily"]
    ks = pd.Series(d["ks"].to_numpy(float), index=pd.DatetimeIndex(d["date"]))
    out["overpass_days"] = ec.overpass_day_result(ec.overpass_pairs(eco[["local_date", "esi"]], ks))
    out["holds_up_any_slot"] = any(out["esi"][s]["holds_up"] for s in ("monsoon", "winter"))
    return out


def check_hls(twin, seasons_json, R):
    H = R["twin_vs_hls"]
    hls = seasons_json["chosen"]["seasons_by_year"]
    df = tg.pair(seasons_of(twin["current"]), hls)
    out = {"pairs": df.round(4).to_dict("records")}
    for slot in ("monsoon", "winter"):
        d = df[df["slot"] == slot]
        out[slot] = {"primary": tg.metric_result(d, "eta_over_etc", +1, H["min_seasons"]),
                     "dry_days": tg.metric_result(d, "dry_days", -1, H["min_seasons"]),
                     "harvest_pct": tg.metric_result(d, "harvest_pct", +1, H["min_seasons"])}
    if twin["wheat"] is not None:
        dw = tg.pair(seasons_of(twin["wheat"], "wheat"), hls)
        dw = dw[dw["slot"] == "winter"]
        out["winter_rice_then_wheat"] = {"plan": twin["wheat_plan"], "pairs": dw.round(4).to_dict("records"),
                                         "eta_over_etc": tg.metric_result(dw, "eta_over_etc", +1, H["min_seasons"]),
                                         "dry_days": tg.metric_result(dw, "dry_days", -1, H["min_seasons"])}
    return out


def faostat_potato(data):
    z = data / "raw" / "faostat" / "QCL_All_Data_Normalized.zip"
    with zipfile.ZipFile(z) as zz, zz.open(fs.MEMBER) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        print(f"[faostat raw attrs] columns: {reader.fieldnames}")
        df = fc.parse_items(reader, {"116": "potato"})
    print(f"[faostat] potato (item 116) {len(df)} rows, units kg/ha, flags {df['flag'].value_counts().to_dict()}")
    return df


def check_faostat(twin, fao):
    out = {}
    pairs = {"rice": (twin["current"], "rice"), "potato": (twin["current"], "potato"), "wheat": (twin["wheat"], "wheat")}
    for crop, (res, c) in pairs.items():
        if res is None:
            out[crop] = {"status": "not run: no rice-then-wheat option in plans.json"}
            continue
        t = pd.Series({s["year"]: s["harvest_pct"] for s in seasons_of(res, c)})
        f = fao[fao["crop"] == crop].set_index("year")["yield_kg_ha"]
        yrs = [y for y in t.index if y in f.index and y >= 2002]
        out[crop] = fc.first_difference_check(f.reindex(yrs), t.reindex(yrs))
        out[crop]["twin_harvest_pct"] = {int(y): round(float(t[y]), 2) for y in yrs}
        out[crop]["fao_yield_kg_ha"] = {int(y): float(f[y]) for y in yrs}
    return out


def check_gldas(twin, w, gl, R, with_pet):
    agree = R["common"]["agree_band_r"]
    m = gc.twin_monthly(pd.DataFrame(twin["current"]["daily"])[["date", "dr_mm", "taw_mm", "eta_mm"]])
    g = gl.set_index("month")
    out = {"soil": gc.compare_monthly(m["wetness"], g["theta_0_100cm_m3m3"], agree),
           "et": gc.compare_monthly(m["eta_mm"], g["et_mm"], agree)}
    wd = w.set_index(pd.DatetimeIndex(w["date"]))
    per = wd.index.to_period("M")
    full = wd.groupby(per).size() == per.unique().days_in_month
    rain_m = wd["rain_mm"].groupby(per).sum()[full]
    rain_m.index = rain_m.index.to_timestamp()
    out["rain_context"] = gc.compare_monthly(rain_m, g["rain_mm_day"] * g["days"], agree)
    out["rain_context"]["note"] = "context, not a pre-declared pair: GLDAS's own rain forcing (GPCP v1.3) against the twin's rain"
    if with_pet:
        et0 = wd["et0_mm"].groupby(per).sum()[full]
        et0.index = et0.index.to_timestamp()
        out["pet"] = gc.compare_monthly(et0, g["pet_mm"], agree)
        out["levels"] = {"twin_et0_mm_yr": round(float(et0.mean() * 12), 0), "gldas_pet_mm_yr": round(float(g["pet_mm"].mean() * 12), 0)}
    out["levels_mm_yr"] = {"twin_eta": round(float(m["eta_mm"].mean() * 12), 0), "gldas_et": round(float(g["et_mm"].mean() * 12), 0),
                           "twin_rain": round(float(rain_m.mean() * 12), 0),
                           "gldas_rain": round(float((g["rain_mm_day"] * g["days"]).mean() * 12), 0)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--rain", choices=("both", "corrected", "uncorrected"), default="both")
    ap.add_argument("--only", nargs="+", choices=("ecostress", "hls", "faostat", "gldas"), default=["ecostress", "hls", "faostat", "gldas"])
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    lib = load_crops(field=field)        # the field's country profile (config/countries/)
    R = rules["validation_checks"]
    data = REPO / "data"
    clean, checks = data / "clean" / field["id"], data / "checks" / field["id"]
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    weather = pd.read_parquet(clean / "weather.parquet")
    versions = ["corrected", "uncorrected"] if a.rain == "both" else [a.rain]
    eco = pd.read_parquet(clean / "ecostress.parquet") if "ecostress" in a.only else None
    gl = pd.read_parquet(clean / "gldas.parquet") if "gldas" in a.only else None
    fao = None
    if "faostat" in a.only:
        fao = pd.concat([pd.read_parquet(clean / "faostat_yields.parquet"), faostat_potato(data)], ignore_index=True)
    res = {k: {} for k in a.only}
    for v in versions:
        cdir = checks / ("rain_uncorrected" if v == "uncorrected" else "")
        w = with_rain(weather, v)
        try:
            twin = twin_runs(field, rules, lib, soil, w, cdir, data)
        except TwinMismatch as e:
            print(f"STOPPED: the twin in memory does not reproduce the stored outputs ({e}). Rerun scripts/run_replay.py "
                  f"--rain {v} and scripts/run_plans.py --rain {v} first, or update this script's twin calls.")
            return 3
        print(f"[{v}] twin reproduces the stored replay ({len(twin['current']['seasons'])} seasons) and the rice-then-wheat option")
        if "ecostress" in a.only:
            res["ecostress"][v] = check_ecostress(twin, eco, R)
        if "hls" in a.only:
            res["hls"][v] = check_hls(twin, json.loads((checks / "diary_seasons.json").read_text()), R)
        if "faostat" in a.only:
            res["faostat"][v] = check_faostat(twin, fao)
        if "gldas" in a.only:
            res["gldas"][v] = check_gldas(twin, w, gl, R, with_pet=(v == versions[0]))
    base = {"field": field["name"], "rule": "rules.yaml validation_checks (committed before the first run)", "rule_commit": RULE_COMMIT,
            "rain_versions": versions, "rotation": "current rotation (PLACEHOLDER) rain-fed; the rice-then-wheat option where named",
            "bare_soil": str(to.bare_setting(rules, soil))[:200]}
    files = {"ecostress": "ecostress_check.json", "hls": "twin_vs_hls.json", "faostat": "faostat_check.json", "gldas": "gldas_check.json"}
    notes = {"ecostress": "ESI (actual / potential ET, PT-JPL, model-based from the overpass's LST) at the one 70 m pixel whose centre lies "
                          "in the field (37% of it is field); esi_touching = the field-area-weighted mean of the 4 touching pixels. "
                          "Season = the twin's own crop season of the current rotation.",
             "hls": "Peak NDVI is green cover, not harvest. The placeholder potato (30 Oct - 21 Feb) sits about ten weeks before the "
                    "satellite's winter season (about 7 Jan - 18 May; METHOD_NOTES 40).",
             "faostat": "National yields (Nepal, FAOSTAT QCL) against one 60 m placeholder field: first differences. Potato read from the "
                        "same bulk file (item 116) for this check only.",
             "gldas": "GLDAS-2.1 Noah monthly, the 0.25-degree cell holding the field, model-based (forced with GPCP v1.3 rain). Monthly "
                      "anomalies 2001-2025; year-block bootstrap."}
    for k in a.only:
        verdict = {}
        if k == "ecostress":
            verdict = {v: res[k][v]["holds_up_any_slot"] for v in versions}
        elif k == "hls":
            verdict = {v: {s: res[k][v][s]["primary"]["agrees"] for s in ("monsoon", "winter")} for v in versions}
        elif k == "faostat":
            verdict = {v: {c: res[k][v][c].get("holds_up", False) for c in ("rice", "potato", "wheat")} for v in versions}
        elif k == "gldas":
            verdict = {v: {p: res[k][v][p]["holds_up"] for p in ("soil", "et", "pet") if p in res[k][v]} for v in versions}
        out = {"labels": {**base, "note": notes[k]}, "verdict": verdict, "rain": res[k]}
        path = checks / files[k]
        path.write_text(json.dumps(out, indent=1, default=str) + "\n")
        print(f"{k}: verdict {json.dumps(verdict)} -> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
