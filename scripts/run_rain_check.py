"""Rain check B (owner's upgrade list item 1, 2026-11-13): every rain source month by month against DHM's 1991-2020
normals, and Pettitt change-point tests on yearly totals. Writes data/checks/<field>/rain_check_b.json.
Since the owner's decision 1 (2026-11-13) it also reports the break correction (held-out test against the station,
the corrected rain against the station and the normals), the IMERG Late check (2014-2019, pipeline/fetch/gpm_late.py)
and CHIRPS v3 (pipeline/fetch/chirps.py) whenever their files exist.

    .venv/bin/python scripts/run_rain_check.py --field demo
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


def _series(df, col="rain_mm"):
    return pd.Series(df[col].to_numpy(float), index=pd.DatetimeIndex(df["date"]))


def _yearly(s):
    """Totals of years whose every day has a value."""
    g = s.groupby(s.index.year)
    full = g.count() == g.size()
    return g.sum()[full]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    clean = REPO / "data" / "clean" / field["id"]
    gpm = _series(pd.read_parquet(clean / "gpm.parquet"))
    power = _series(pd.read_parquet(clean / "power.parquet"))
    st_df = pd.read_parquet(clean / f"ghcn_{field['validation_station']}.parquet")
    station = _series(st_df).reindex(pd.date_range(st_df["date"].min(), st_df["date"].max()))
    normals = rc.load_normals()
    sources = {"gpm_2001_2016": gpm["2001":"2016"], "gpm_2017_2025": gpm["2017":"2025"],
               "power_2001_2020": power["2001":"2020"], "station_airport_2001_2020": station["2001":"2020"]}
    refs = {k: rc.station_months(normals, k, "precip_mm") for k in ("Bhaktapur", "Kathmandu Airport")}
    table = {}
    for name, s in sources.items():
        c = rc.monthly_climatology(s)
        row = {"mean_mm": {MONTHS[m - 1]: (None if np.isnan(v) else round(float(v), 1)) for m, v in c["mean_mm"].items()},
               "years": {MONTHS[m - 1]: int(v) for m, v in c["years"].items()}}
        tot = float(c["mean_mm"].sum()) if c["mean_mm"].notna().all() else None
        row["annual_mm"] = None if tot is None else round(tot, 1)
        for ref, nm in refs.items():
            row[f"ratio_to_{ref.replace(' ', '_').lower()}"] = {
                MONTHS[m - 1]: (None if np.isnan(c.loc[m, "mean_mm"]) else round(float(c.loc[m, "mean_mm"] / nm[m]), 2)) for m in range(1, 13)}
            row[f"annual_ratio_to_{ref.replace(' ', '_').lower()}"] = None if tot is None else round(tot / sum(nm.values()), 2)
        table[name] = row
    yg, yp, ys = _yearly(gpm), _yearly(power), _yearly(station)
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
    # the break correction (owner's decision 1, 2026-11-13; rules.yaml gpm_series)
    from pipeline.fetch.rules import load_rules
    G = load_rules()["gpm_series"]
    gdf = pd.read_parquet(clean / "gpm.parquet")
    final_only = pd.Series(np.where(gdf["product"].isin(G.get("correction_factor_products", G["correction_products"])), gdf["rain_mm"], np.nan),
                           index=pd.DatetimeIndex(gdf["date"]))
    st_months = rc.complete_month_totals(station)
    hold = rc.holdout_break_correction(rc.complete_month_totals(final_only), st_months,
                                       tuple(G["correction_reference_years"]), int(G["correction_from"][:4]))
    w = pd.read_parquet(clean / "weather.parquet")
    corr = _series(w, "rain_mm")
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
                "twin_rain_2017_2025_annual_mm": round(float(c_clim["mean_mm"].sum()), 1),
                "twin_rain_2017_2025_ratio_to_bhaktapur": round(float(c_clim["mean_mm"].sum() / sum(refs["Bhaktapur"].values())), 2)}
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
    chirps_path = clean / "chirps.parquet"
    chirps = None
    if chirps_path.exists():
        cs = _series(pd.read_parquet(chirps_path))
        cy = _yearly(cs)
        yrs = sorted(set(cy.index) & set(yg.index))
        cy_ = {int(y): round(float(cy[y]), 1) for y in yrs}
        tw = _yearly(corr)
        chirps = {"years": yrs, "chirps_mm": cy_, "gpm_mm": {int(y): round(float(yg[y]), 1) for y in yrs},
                  "twin_mm": {int(y): round(float(tw[y]), 1) for y in yrs if y in tw.index},
                  "gpm_over_chirps": {int(y): round(float(yg[y] / cy[y]), 3) for y in yrs}}
        if len(yrs) >= 8:
            chirps["pettitt_chirps_yearly"] = rc.pettitt(yrs, [cy[y] for y in yrs])
            chirps["pettitt_gpm_over_chirps"] = rc.pettitt(yrs, [yg[y] / cy[y] for y in yrs])
        if any(y < 2017 for y in yrs) and any(y >= 2017 for y in yrs):
            chirps["step_chirps"] = round(rc.step_ratio({y: cy[y] for y in yrs}, 2017), 3)
            chirps["step_gpm"] = round(rc.step_ratio({y: yg[y] for y in yrs}, 2017), 3)
    out = {"labels": {"normals": "DHM 1991-2020 (config/dhm_normals_1991_2020.csv: Kathmandu Airport official table; "
                                 "Bhaktapur from DHM bulletin Annex 1); periods differ from the sources' years",
                      "gpm": "IMERG V07 Final (Late for Oct-Dec 2025), the field's 0.1 deg cell, UTC days",
                      "power": "NASA POWER PRECTOTCORR (model-based, 0.5 x 0.625 deg), cross-checks only",
                      "station": f"GHCN-Daily {field['validation_station']} Kathmandu Airport, complete months only",
                      "pettitt": "Pettitt 1979; change_after = the last year before the change"},
           "normals_mm": {k: {MONTHS[m - 1]: v for m, v in nm.items()} | {"annual": round(sum(nm.values()), 1)} for k, nm in refs.items()},
           "sources": table, "pettitt": tests, "break_correction": out_corr, "late_check": late, "chirps": chirps,
           "yearly_mm": {"gpm": {int(k): round(float(v), 1) for k, v in yg.items()},
                         "power": {int(k): round(float(v), 1) for k, v in yp.items()},
                         "station": {int(k): round(float(v), 1) for k, v in ys.items()}}}
    path = REPO / "data" / "checks" / field["id"] / "rain_check_b.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("normals (mm):", {k: v["annual"] for k, v in out["normals_mm"].items()})
    print(f"{'source':28s} {'annual':>7s} {'/Bhakt':>6s} {'/Airp':>6s}  monthly ratio to Bhaktapur (Jan..Dec)")
    for name, row in table.items():
        rb = row["ratio_to_bhaktapur"]
        print(f"{name:28s} {row['annual_mm'] or float('nan'):7.0f} {row['annual_ratio_to_bhaktapur'] or float('nan'):6.2f} "
              f"{row['annual_ratio_to_kathmandu_airport'] or float('nan'):6.2f}  " + " ".join(f"{(v if v is not None else float('nan')):.2f}" for v in rb.values()))
    for k, v in tests.items():
        if isinstance(v, dict):
            print(f"pettitt {k:20s} change after {v['change_after']}, K {v['k']:.0f}, p {v['p']:.4f} (n {v['n']})")
    print(f"break correction, held out: {out_corr['held_out']}")
    print(f"twin rain vs station from 2017: {out_corr['twin_rain_vs_station_from_2017']}; as published: "
          f"{out_corr['gpm_as_published_vs_station_from_2017']}; all shared months: {out_corr['twin_rain_vs_station_all_shared_months']}")
    print(f"twin rain 2017-2025: {out_corr['twin_rain_2017_2025_annual_mm']} mm/yr ({out_corr['twin_rain_2017_2025_ratio_to_bhaktapur']} x Bhaktapur)")
    if late:
        print(f"IMERG Late check: step Final {late['step_final']}, step Late {late['step_late']}; Final/Late {late['final_over_late']}")
    if chirps:
        print(f"CHIRPS: years {chirps['years']}; GPM/CHIRPS {chirps['gpm_over_chirps']}; steps {chirps.get('step_gpm')} / {chirps.get('step_chirps')}")
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
