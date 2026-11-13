"""Build step 5: replay the field's current rotation through 2001-2025, rain-fed and irrigated.

    .venv/bin/python scripts/run_replay.py --field demo                          # needs GPM rain (D6)
    .venv/bin/python scripts/run_replay.py --field demo --temporary-station-rain  # dry run, never exported

Normal mode: rain is the twin's weather table (GPM IMERG with POWER fill-in only). Until GPM is fetched
the rain column is empty, so the script stops with NOT YET POSSIBLE and writes nothing.
Dry run: rain is the validation station (GHCN-Daily) for runs of years with enough station days
(rules.yaml replay.dry_run_min_station_coverage); missing days are filled from POWER and flagged. It
exercises the whole replay on real temperatures and ET0 and is labelled TEMPORARY. The export step
refuses it (pipeline/export/build_field_json.py).

Rain versions (owner's decision 1, 2026-11-13): --rain corrected (default; the twin's rain, GPM scaled back from
2017) or --rain uncorrected (GPM as published), which writes to data/checks/<field>/rain_uncorrected/.

Writes data/checks/<field>/replay.json (normal) or replay_station_dryrun.json (dry run). Each water case
(rain-fed, irrigated) carries per season and per year: harvest, dry days, irrigation_mm (including an
irrigated paddy's pond water) and pond_supply_mm (that paddy part), plus the events.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import events as ev  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.twin.inputs import covered_year_runs, with_rain  # noqa: E402


def _case(res):
    return {"years": res["years"], "partial_years": res["partial_years"],
            "seasons": [{k: v for k, v in s.items()} for s in res["seasons"]],
            "max_balance_residual_mm": max(abs(s["balance_residual_mm"]) for s in res["segments"].values())}


def run(weather, rotation, lib, soil, cn, rules):
    out = {}
    # one weather event per year for the field, from its rain alone (owner's answer 9 to REVIEW_2, 2026-11-13)
    fe = ev.field_year_events(pd.Series(weather["rain_mm"].to_numpy(float), index=pd.DatetimeIndex(weather["date"])),
                              rules["events"])
    for case, irrigated in (("rain-fed", False), ("irrigated", True)):
        res = sim.replay(weather, rotation, lib, soil, cn, bare_kc=rules["bare_soil"]["kc"], irrigated=irrigated,
                         kc_climate=rules["kc_climate"]["apply"])
        out[case] = _case(res)
        sens = {}
        for v in [rules["ky_assumed"]["neutral"], *rules["ky_assumed"]["sensitivity"]]:
            sens[str(v)] = sim.yearly(sim.seasons_with_ky(res["seasons"], lib, v))
        out[case]["ky_sensitivity"] = sens
        out[case]["events"], out[case]["event_seasons"] = fe["events"], fe["event_seasons"]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--temporary-station-rain", action="store_true")
    ap.add_argument("--rain", choices=("corrected", "uncorrected"), default="corrected")
    a = ap.parse_args(argv)
    field, rules, lib, data = load_field(a.field), load_rules(), load_crops(), REPO / "data"
    clean = data / "clean" / field["id"]
    w = with_rain(pd.read_parquet(clean / "weather.parquet"), a.rain)
    out_dir = data / "checks" / field["id"] / ("rain_uncorrected" if a.rain == "uncorrected" else "")
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    try:
        rotation, rot_label = sim.rotation_for(field, rules)
    except ValueError as e:
        print(f"STOPPED: {e}")
        return 1
    cover, by_cover = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by_cover["bare"], **{c: by_cover[cover[c]] for c in rotation}}
    water = field.get("water_source") or "unknown"
    export_case = sim.export_case(water)
    labels = {"field": field["name"], "field_lat_lon": [field["lat"], field["lon"]],
              "placeholder_field": bool(field.get("placeholder")),
              "rotation": rotation, "rotation_source": rot_label,
              "water_source": water,
              "water_cases": (f"harvest, dry_days and event are the {export_case} case; 'irrigated' is the watered case"
                              + (" (water source unknown: the site shows both side by side, 'if you can't water' and "
                                 "'if you can water'; owner 2026-11-12)" if water == "unknown" else "")),
              "et0": "FAO-56 Penman-Monteith from the twin's weather table (station-corrected temperatures)",
              "frost": "not a replay event (owner 2026-11-12, REVIEW_NOTES M1): shown only as a risk band in the "
                       "monthly calendar, never per year or as a count",
              "paddy": "rain-fed rice gets no outside water (plain bucket, rice's Zr and p); irrigated rice is ponded and "
                       "its pond water is irrigation: irrigation_mm includes it, pond_supply_mm is that part "
                       "(REVIEW_NOTES H1, 2026-11-12)",
              "soil": "SoilGrids 2.0, the nearest cell with values (distance in data/cards/<field>/soilgrids.json)",
              "kc": ("FAO-56 Table 12 Kc mid and Kc end adjusted per season for the season's own wind and minimum "
                     "humidity (eqs. 62 and 65; rules.yaml kc_climate)" if rules["kc_climate"]["apply"]
                     else "FAO-56 Table 12 Kc, not adjusted for climate"),
              "year_rule": rules["replay"]["year_of_season"] + "; " + rules["replay"]["combine_crops"],
              "ky": "crops with no published Ky use the owner-assumed 1.0; ky_sensitivity re-scores them at "
                    f"{rules['ky_assumed']['sensitivity']}"}

    if not a.temporary_station_rain:
        problems = sim.rain_record_problems(w)
        if problems:
            print("NOT YET POSSIBLE: the rain record is not a GPM record with POWER fill-in only (D6, D): "
                  + "; ".join(problems) + ". Nothing written. Dry run: --temporary-station-rain")
            return 2
        cases = run(w, rotation, lib, soil, cn, rules)
        labels["rain_source"] = "gpm"
        labels["rain_version"] = (f"{a.rain}: " + ("GPM IMERG as published (rain_uncorrected_mm)" if a.rain == "uncorrected" else
                                  "GPM IMERG with Final days from 2017 scaled back to GPM's own 2001-2016 level month by month "
                                  "(owner's decision 1, 2026-11-13; rules.yaml gpm_series.correction)"))
        labels["rain_days"] = {k: int(v) for k, v in w["rain_source"].value_counts().items()}
        labels["partial_years"] = cases[export_case]["partial_years"]
        out = {"labels": labels, **cases,
               "export": {"labels": labels, "years": cases[export_case]["years"],
                          "irrigated_years": cases["irrigated"]["years"],
                          "events": cases[export_case]["events"],
                          "event_seasons": cases[export_case]["event_seasons"]}}
        path = out_dir / "replay.json"
    else:
        st = pd.read_parquet(clean / f"ghcn_{field['validation_station']}.parquet").set_index("date")["rain_mm"]
        pw = pd.read_parquet(clean / "power.parquet").set_index("date")["rain_mm"]
        w = w.copy()
        w["rain_station_mm"] = w["date"].map(st)
        has = w.set_index("date")["rain_station_mm"].notna()
        runs = covered_year_runs(has, rules["replay"]["dry_run_min_station_coverage"])
        w["rain_filled"] = w["rain_station_mm"].isna()
        w["rain_mm"] = w["rain_station_mm"].fillna(w["date"].map(pw))
        labels["rain_source"] = (f"TEMPORARY station rain (GHCN-Daily {field['validation_station']}), years with rain on "
                                 f">= {rules['replay']['dry_run_min_station_coverage']:.0%} of days: {runs}; "
                                 "missing days filled from POWER and flagged. NOT EXPORTED")
        windows = []
        for y0, y1 in runs:
            win = w[(w["date"] >= f"{y0}-01-01") & (w["date"] <= f"{y1}-12-31")].reset_index(drop=True)
            try:
                cases = run(win, rotation, lib, soil, cn, rules)
            except sim.NoSeasonError as e:
                windows.append({"years": [y0, y1], "skipped": str(e)})
                continue
            windows.append({"years": [y0, y1], "filled_days": int(win["rain_filled"].sum()),
                            "filled_mm": float(win.loc[win["rain_filled"], "rain_mm"].sum()), **cases})
        out = {"labels": labels, "windows": windows}
        path = data / "checks" / field["id"] / "replay_station_dryrun.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"rotation: {rotation} ({rot_label})\nrain: {labels['rain_source']}")
    for win in out.get("windows", [{"years": "2001-2025", **out}]):
        if "skipped" in win:
            print(f"  {win['years']}: skipped ({win['skipped']})")
            continue
        for case in ("rain-fed", "irrigated"):
            ev_ = win[case]["events"]
            print(f"  {win['years']} {case} | max balance residual {win[case]['max_balance_residual_mm']:.4f} mm")
            for y in win[case]["years"]:
                print(f"    {y['year']} {'+'.join(y['crops']):14s} harvest {y['harvest']:5.1f}%  dry days {y['dry_days']:3d}  "
                      f"irrigation {y['irrigation_mm']:6.1f} mm (pond {y['pond_supply_mm']:6.1f} mm)  "
                      f"event {ev_[str(y['year'])]}")
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
