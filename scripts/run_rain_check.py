"""Rain check B (owner's upgrade list item 1, 2026-11-13): every rain source month by month against DHM's 1991-2020
normals, and Pettitt change-point tests on yearly totals. Writes data/checks/<field>/rain_check_b.json.
Since the owner's decision 1 (2026-11-13) it also reports the break correction (held-out test against the station,
the corrected rain against the station and the normals), the IMERG Late check (2014-2019, pipeline/fetch/gpm_late.py)
and CHIRPS v3 (pipeline/fetch/chirps.py) whenever their files exist.

Any field (build step 11, REVIEW_2 H6): the station-free parts always run (Pettitt on yearly GPM totals and on the
yearly GPM / POWER ratio, CHIRPS, and the break test of rules.yaml gpm_series.break_test on the IMERG gauge weight,
written to data/checks/<field>/break_test.json). Normals run only when the field config names them (`rain_check:
{normals: [...]}`; the demo's config predates the key, so the demo keeps Bhaktapur and the airport, DEMO_RAIN_CHECK),
the station parts only when the config names a `validation_station` whose table exists, and the break-correction
parts only for a field listed in gpm_series.correction_fields.

    .venv/bin/python scripts/run_rain_check.py --field demo
    .venv/bin/python scripts/run_rain_check.py --field ambohidratrimo [--out-dir DIR]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks import rain_check as rc  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BREAK_TEST_COMMIT = "6d2919c"          # the rule's commit, made before any rain data of the field abroad existed
# The demo's config predates `rain_check` (H6 moves this into config/fields/demo.yaml)
DEMO_RAIN_CHECK = {"normals": ["Bhaktapur", "Kathmandu Airport"], "station_key": "airport", "station_name": "Kathmandu Airport",
                   "normals_label": "DHM 1991-2020 (config/dhm_normals_1991_2020.csv: Kathmandu Airport official table; "
                                    "Bhaktapur from DHM bulletin Annex 1); periods differ from the sources' years"}


def rain_check_config(field):
    """The field's rain-check settings: config `rain_check` ({normals, station_key, station_name, normals_label}), the
    demo's defaults for the demo, and for any other field no normals and the station named by its config."""
    cfg = field.get("rain_check")
    if cfg is None and field["id"] == "demo":
        cfg = DEMO_RAIN_CHECK
    cfg = dict(cfg or {})
    cfg.setdefault("normals", [])
    cfg.setdefault("station_key", str(field.get("validation_station") or "station").lower())
    cfg.setdefault("station_name", field.get("validation_station_name") or field.get("validation_station"))
    cfg.setdefault("normals_label", "normals named in the field config (config/dhm_normals_1991_2020.csv)")
    return cfg


def _series(df, col="rain_mm"):
    return pd.Series(df[col].to_numpy(float), index=pd.DatetimeIndex(df["date"]))


def _yearly(s):
    """Totals of years whose every day has a value."""
    g = s.groupby(s.index.year)
    full = g.count() == g.size()
    return g.sum()[full]


def _key(name):
    return name.replace(" ", "_").lower()


def break_test_report(field, G, gauge, yg, cy, gpm_over_power, data_dir):
    """rules.yaml gpm_series.break_test on this field's own evidence, with what is reported beside it."""
    bt = rc.break_test(gauge, {int(k): float(v) for k, v in yg.items()},
                       None if cy is None else {int(k): float(v) for k, v in cy.items()}, G["break_test"])
    rep = {"gpm_over_power_pettitt": gpm_over_power}
    if gauge is not None and "gpcc_stations" in gauge:
        n = gauge.dropna(subset=["gpcc_stations"])
        rep["gpcc_stations_yearly_mean"] = {int(y): round(float(v), 1) for y, v in
                                            n.groupby(n["month"].str[:4].astype(int))["gpcc_stations"].mean().items()}
    corrected = rc.break_corrected(field, G, bt)          # the demo, or a sample whose own test found it (810b3c8)
    out = {"field": field["id"], "rule": f"rules.yaml gpm_series.break_test (committed {BREAK_TEST_COMMIT} before any run on a field abroad)",
           "rule_values": {k: v for k, v in G["break_test"].items() if k != "rule"},
           "inputs": {"gauge_weight": str((data_dir / "clean" / field["id"] / "gauge_evidence.parquet").relative_to(REPO))
                      if gauge is not None else None,
                      "chirps": str((data_dir / "clean" / field["id"] / "chirps.parquet").relative_to(REPO)) if cy is not None else None,
                      "gpm": str((data_dir / "clean" / field["id"] / "gpm.parquet").relative_to(REPO))},
           **bt, "reported_not_required": rep, "field_in_correction_fields": corrected,
           "what_follows": ("the field is corrected (gpm_series.correction_fields or correction_for_samples)" if corrected else
                            (f"break found from {bt.get('year')}: put to the owner for gpm_series.correction_fields; "
                             "nothing is corrected until the owner's go") if bt["found"] else
                            "no break found: the field's GPM rain is used as published (no correction)")}
    return json.loads(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--out-dir", default=None, help="write the two JSON files here instead of data/checks/<field>/")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    fid, data_dir = field["id"], REPO / "data"
    rcfg = rain_check_config(field)
    clean = data_dir / "clean" / fid
    gpm = _series(pd.read_parquet(clean / "gpm.parquet"))
    power = _series(pd.read_parquet(clean / "power.parquet"))
    st_id = field.get("validation_station")
    station = None
    if st_id and (clean / f"ghcn_{st_id}.parquet").exists():
        st_df = pd.read_parquet(clean / f"ghcn_{st_id}.parquet")
        station = _series(st_df).reindex(pd.date_range(st_df["date"].min(), st_df["date"].max()))
    normals = rc.load_normals() if rcfg["normals"] else None
    sources = {"gpm_2001_2016": gpm["2001":"2016"], "gpm_2017_2025": gpm["2017":"2025"],
               "power_2001_2020": power["2001":"2020"]}
    if station is not None:
        sources[f"station_{rcfg['station_key']}_2001_2020"] = station["2001":"2020"]
    refs = {k: rc.station_months(normals, k, "precip_mm") for k in rcfg["normals"]}
    table = {}
    for name, s in sources.items():
        c = rc.monthly_climatology(s)
        row = {"mean_mm": {MONTHS[m - 1]: (None if np.isnan(v) else round(float(v), 1)) for m, v in c["mean_mm"].items()},
               "years": {MONTHS[m - 1]: int(v) for m, v in c["years"].items()}}
        tot = float(c["mean_mm"].sum()) if c["mean_mm"].notna().all() else None
        row["annual_mm"] = None if tot is None else round(tot, 1)
        for ref, nm in refs.items():
            row[f"ratio_to_{_key(ref)}"] = {
                MONTHS[m - 1]: (None if np.isnan(c.loc[m, "mean_mm"]) else round(float(c.loc[m, "mean_mm"] / nm[m]), 2)) for m in range(1, 13)}
            row[f"annual_ratio_to_{_key(ref)}"] = None if tot is None else round(tot / sum(nm.values()), 2)
        table[name] = row
    yg, yp = _yearly(gpm), _yearly(power)
    ys = _yearly(station) if station is not None else pd.Series(dtype=float)
    both = yg.index.intersection(yp.index)
    ratio = (yg[both] / yp[both])
    tests = {"gpm_yearly_mm": rc.pettitt(list(yg.index), yg.values), "power_yearly_mm": rc.pettitt(list(yp.index), yp.values),
             "gpm_over_power": rc.pettitt(list(ratio.index), ratio.values)}
    if len(ys) >= 8:
        tests["station_yearly_mm"] = rc.pettitt(list(ys.index), ys.values)
        common = yg.index.intersection(ys.index)
        r2 = yg[common] / ys[common]
        tests["gpm_over_station"] = rc.pettitt(list(r2.index), r2.values)
        tests["station_years"] = [int(y) for y in ys.index]
    from pipeline.fetch.rules import load_rules
    G = load_rules()["gpm_series"]
    gdf = pd.read_parquet(clean / "gpm.parquet")
    final_only = pd.Series(np.where(gdf["product"].isin(G.get("correction_factor_products", G["correction_products"])), gdf["rain_mm"], np.nan),
                           index=pd.DatetimeIndex(gdf["date"]))
    weather = clean / "weather.parquet"
    corr = _series(pd.read_parquet(weather), "rain_mm") if weather.exists() else None
    out_corr = None
    chirps_path = clean / "chirps.parquet"
    cy = _yearly(_series(pd.read_parquet(chirps_path))) if chirps_path.exists() else None
    gpath = clean / "gauge_evidence.parquet"
    bt = break_test_report(field, G, pd.read_parquet(gpath) if gpath.exists() else None, yg, cy, tests["gpm_over_power"], data_dir)
    if bt["field_in_correction_fields"] and station is not None and corr is not None:
        # the break correction (owner's decision 1, 2026-11-13; rules.yaml gpm_series), for corrected fields only
        st_months = rc.complete_month_totals(station)
        hold = rc.holdout_break_correction(rc.complete_month_totals(final_only), st_months,
                                           tuple(G["correction_reference_years"]), int(G["correction_from"][:4]))
        cm = rc.complete_month_totals(corr)
        shared = [i for i in cm.index.intersection(st_months.index)]
        after = [i for i in shared if i[0] >= int(G["correction_from"][:4])]

        def _vs_station(idx, s):
            a, b = np.array([s[i] for i in idx]), np.array([st_months[i] for i in idx])
            return {"months": len(idx), "ratio": round(float(a.sum() / b.sum()), 3), "mae_mm": round(float(np.mean(np.abs(a - b))), 1)}
        gm = rc.complete_month_totals(gpm)
        c_clim = rc.monthly_climatology(corr["2017":"2025"])
        out_corr = {"rule": G["correction"], "held_out": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hold.items()},
                    "held_out_design": "factors fitted on the odd years from 2017 and tested on the even ones against the station's "
                                       "complete months, then the reverse; pooled",
                    "twin_rain_vs_station_all_shared_months": _vs_station(shared, cm),
                    "twin_rain_vs_station_from_2017": _vs_station(after, cm),
                    "gpm_as_published_vs_station_from_2017": _vs_station(after, gm),
                    "twin_rain_2017_2025_annual_mm": round(float(c_clim["mean_mm"].sum()), 1)}
        if refs:
            first = next(iter(refs))
            out_corr[f"twin_rain_2017_2025_ratio_to_{_key(first)}"] = round(float(c_clim["mean_mm"].sum() / sum(refs[first].values())), 2)
    late_path = clean / "gpm_late_check.parquet"
    late = None
    if late_path.exists():
        lt = _series(pd.read_parquet(late_path))
        ly = _yearly(lt)
        fy = _yearly(final_only["2014":"2019"])
        years = sorted(set(ly.index) & set(fy.index))
        late = {"years": years, "final_mm": {int(y): round(float(fy[y]), 1) for y in years},
                "late_mm": {int(y): round(float(ly[y]), 1) for y in years},
                "final_over_late": {int(y): round(float(fy[y] / ly[y]), 3) for y in years},
                "step_final": round(rc.step_ratio({y: fy[y] for y in years}, 2017), 3),
                "step_late": round(rc.step_ratio({y: ly[y] for y in years}, 2017), 3),
                "read": "step = mean yearly total 2017-2019 / 2014-2016; the gauge loss shows as a step in Final only"}
    chirps = None
    if chirps_path.exists():
        yrs = sorted(set(cy.index) & set(yg.index))
        cy_ = {int(y): round(float(cy[y]), 1) for y in yrs}
        chirps = {"years": yrs, "chirps_mm": cy_, "gpm_mm": {int(y): round(float(yg[y]), 1) for y in yrs}}
        if corr is not None:
            tw = _yearly(corr)
            chirps["twin_mm"] = {int(y): round(float(tw[y]), 1) for y in yrs if y in tw.index}
        chirps["gpm_over_chirps"] = {int(y): round(float(yg[y] / cy[y]), 3) for y in yrs}
        if len(yrs) >= 8:
            chirps["pettitt_chirps_yearly"] = rc.pettitt(yrs, [cy[y] for y in yrs])
            chirps["pettitt_gpm_over_chirps"] = rc.pettitt(yrs, [yg[y] / cy[y] for y in yrs])
        if any(y < 2017 for y in yrs) and any(y >= 2017 for y in yrs):
            chirps["step_chirps"] = round(rc.step_ratio({y: cy[y] for y in yrs}, 2017), 3)
            chirps["step_gpm"] = round(rc.step_ratio({y: yg[y] for y in yrs}, 2017), 3)
    labels = {}
    if refs:
        labels["normals"] = rcfg["normals_label"]
    labels.update({"gpm": "IMERG V07 Final (Late for Oct-Dec 2025), the field's 0.1 deg cell, UTC days",
                   "power": "NASA POWER PRECTOTCORR (model-based, 0.5 x 0.625 deg), cross-checks only"})
    if station is not None:
        labels["station"] = f"GHCN-Daily {st_id} {rcfg['station_name']}, complete months only"
    labels["pettitt"] = "Pettitt 1979; change_after = the last year before the change"
    yearly = {"gpm": {int(k): round(float(v), 1) for k, v in yg.items()},
              "power": {int(k): round(float(v), 1) for k, v in yp.items()}}
    if station is not None:
        yearly["station"] = {int(k): round(float(v), 1) for k, v in ys.items()}
    out = {"labels": labels,
           "normals_mm": {k: {MONTHS[m - 1]: v for m, v in nm.items()} | {"annual": round(sum(nm.values()), 1)} for k, nm in refs.items()},
           "sources": table, "pettitt": tests, "break_correction": out_corr, "late_check": late, "chirps": chirps,
           "yearly_mm": yearly}
    out_dir = Path(a.out_dir) if a.out_dir else data_dir / "checks" / fid
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "rain_check_b.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    bpath = out_dir / "break_test.json"
    bpath.write_text(json.dumps(bt, indent=1) + "\n")
    if refs:
        print("normals (mm):", {k: v["annual"] for k, v in out["normals_mm"].items()})
    for name, row in table.items():
        rats = " ".join(f"/{k[16:]} {v if v is not None else float('nan'):.2f}" for k, v in row.items() if k.startswith("annual_ratio_to_"))
        print(f"{name:28s} annual {row['annual_mm'] or float('nan'):7.0f} {rats}")
    for k, v in tests.items():
        if isinstance(v, dict):
            print(f"pettitt {k:20s} change after {v['change_after']}, K {v['k']:.0f}, p {v['p']:.4f} (n {v['n']})")
    if out_corr:
        print(f"break correction, held out: {out_corr['held_out']}")
        print(f"twin rain vs station from 2017: {out_corr['twin_rain_vs_station_from_2017']}; as published: "
              f"{out_corr['gpm_as_published_vs_station_from_2017']}; all shared months: {out_corr['twin_rain_vs_station_all_shared_months']}")
    if late:
        print(f"IMERG Late check: step Final {late['step_final']}, step Late {late['step_late']}; Final/Late {late['final_over_late']}")
    if chirps:
        print(f"CHIRPS: years {chirps['years'][0]}-{chirps['years'][-1]}; GPM/CHIRPS {chirps['gpm_over_chirps']}; "
              f"steps {chirps.get('step_gpm')} / {chirps.get('step_chirps')}")
    print(f"break test: found {bt['found']}" + (f" (from {bt.get('year')})" if bt["found"] else f"; why not: {bt['why_not']}")
          + f"; checks {bt.get('checks')}; {bt['what_follows']}")
    print(f"-> {path.relative_to(REPO) if path.is_relative_to(REPO) else path}\n-> {bpath.relative_to(REPO) if bpath.is_relative_to(REPO) else bpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
