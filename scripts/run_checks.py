"""Run the validation layer-3 checks that today's data allows, for one field.

    .venv/bin/python scripts/run_checks.py --field demo

Writes data/checks/<field>/layer3_power.json. Thin runner; the statistics live in
pipeline/checks/climate.py (tested in tests/test_checks_climate.py).
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks import climate as c  # noqa: E402

SOURCE = "NASA POWER Daily API (model-based), one grid cell at the field point, 2001-2025"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    field = ap.parse_args(argv).field
    df = pd.read_parquet(REPO / "data" / "clean" / field / "power.parquet")
    total, years = c.mean_annual_total(df, "rain_mm")
    rows = [
        ("annual_rain_mm", total, f"PRECTOTCORR, mean of {len(years)} complete years {years[0]}-{years[-1]}"),
        ("monsoon_share", c.share_in_months(df, "rain_mm", [6, 7, 8, 9]), "PRECTOTCORR, Jun-Sep share of all rain"),
        ("jan_tmin_c", c.month_mean(df, "tmin_c", [1]), "T2M_MIN, mean of all January days"),
        ("early_summer_tmax_c", c.month_mean(df, "tmax_c", [5, 6]), "T2M_MAX, mean of all May and June days"),
    ]
    weather_path = REPO / "data" / "clean" / field / "weather.parquet"
    if weather_path.exists():                       # decision A: the corrected temperatures the twin uses
        w = pd.read_parquet(weather_path)
        rows += [("jan_tmin_c", c.month_mean(w, "tmin_c", [1]), "twin input: corrected Tmin, mean of all January days"),
                 ("early_summer_tmax_c", c.month_mean(w, "tmax_c", [5, 6]), "twin input: corrected Tmax, May and June")]
    results = []
    for name, value, how in rows:
        e = c.EXPECT[name]
        results.append({"check": name, "value": round(float(value), 3), "how": how, "expected": e["said"],
                        "band": list(e["band"]), "tolerance": e["tolerance"], "result": c.judge(value, e["band"]),
                        "source": SOURCE if how.startswith(("PRECTOTCORR", "T2M")) else
                        "data/clean/<field>/weather.parquet (POWER corrected from the station)"})
    d = df.assign(year=df["date"].dt.year, month=df["date"].dt.month)
    extra = {
        "annual_rain_mm_by_year": {int(y): round(float(v), 1) for y, v in d.groupby("year")["rain_mm"].sum().items()},
        "monthly_mean_rain_mm": {int(m): round(float(v), 1) for m, v in
                                 (d.groupby(["year", "month"])["rain_mm"].sum().groupby("month").mean()).items()},
        "monthly_mean_tmin_c": {int(m): round(float(v), 2) for m, v in d.groupby("month")["tmin_c"].mean().items()},
        "monthly_mean_tmax_c": {int(m): round(float(v), 2) for m, v in d.groupby("month")["tmax_c"].mean().items()},
    }
    out = REPO / "data" / "checks" / field / "layer3_power.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "detail": extra}, indent=1) + "\n")
    for r in results:
        print(f"{r['result']:4}  {r['check']:20} {r['value']:>9}  band {r['band']}  ({r['expected']})")
    print(json.dumps(extra, indent=None))
    print(f"-> {out}")

    stations = sorted((REPO / "data" / "clean" / field).glob("ghcn_*.parquet"))
    for st_path in stations:
        crosscheck_station(field, df, pd.read_parquet(st_path), st_path.stem)
    gpm_path = REPO / "data" / "clean" / field / "gpm.parquet"
    if gpm_path.exists():                           # D6: the twin's rain
        g = pd.read_parquet(gpm_path)
        gtotal, gyears = c.mean_annual_total(g, "rain_mm")
        grows = [("annual_rain_mm", gtotal, f"GPM IMERG V07 daily, field cell, mean of {len(gyears)} complete years {gyears[0]}-{gyears[-1]}"),
                 ("monsoon_share", c.share_in_months(g, "rain_mm", [6, 7, 8, 9]), "GPM IMERG V07, Jun-Sep share of all rain")]
        gres = [{"check": n, "value": round(float(v), 3), "how": h, "expected": c.EXPECT[n]["said"], "band": list(c.EXPECT[n]["band"]),
                 "tolerance": c.EXPECT[n]["tolerance"], "result": c.judge(v, c.EXPECT[n]["band"]),
                 "source": "NASA GPM IMERG V07 daily (Final to 2025-09-30, then Late), 0.1 deg cell holding the field; UTC days"}
                for n, v, h in grows]
        gd = g.assign(year=g["date"].dt.year)
        (out.parent / "layer3_gpm.json").write_text(json.dumps({"results": gres, "annual_rain_mm_by_year": {
            int(y): round(float(v), 1) for y, v in gd.groupby("year")["rain_mm"].sum().items()}}, indent=1) + "\n")
        for r in gres:
            print(f"GPM {r['result']:4}  {r['check']:20} {r['value']:>9}  band {r['band']}")
        for st_path in stations:
            crosscheck_station(field, g, pd.read_parquet(st_path), st_path.stem, other="gpm")
    return 0


def crosscheck_station(field, power, st, name, other="power"):
    """A gridded source (POWER, or GPM) vs a GHCN station. Owner's rule: monthly totals, only years with
    >= 330 rain records. Temperature parts only for POWER (GPM has no temperature)."""
    from pipeline.checks import crosscheck as x
    from pipeline.fetch import ghcn

    per_year = ghcn.records_per_year(st, "rain_mm")
    good_years = sorted(y for y, n in per_year.items() if n >= 330)
    st_good = st[st["date"].dt.year.isin(good_years)]
    st_months = x.complete_month_totals(st_good, "rain_mm")
    pw_months = x.complete_month_totals(power, "rain_mm")
    rain = x.compare(st_months, pw_months)
    full_years = {}
    for y in good_years:
        m = st_months[st_months.index.year == y]
        if len(m) == 12:
            full_years[y] = {"station_mm": round(float(m.sum()), 1),
                             f"{other}_mm": round(float(pw_months[pw_months.index.year == y].sum()), 1)}
    has_t = "tmin_c" in power.columns
    jan = x.paired_difference(st[st["date"].dt.month == 1], power[power["date"].dt.month == 1], "tmin_c") if has_t else None
    summer = x.paired_difference(st[st["date"].dt.month.isin([5, 6])], power[power["date"].dt.month.isin([5, 6])], "tmax_c") if has_t else None
    from pipeline.fetch.rules import load_rules
    lags = x.lag_correlation(st, power, "rain_mm", load_rules()["day_alignment"]["lags_days"])
    res = {
        "station": name, "rule": "monthly totals; only years with >= 330 rain records; only complete months",
        "day_alignment": {"convention": f"lag k pairs station day d with {other} day d + k", "by_lag": lags,
                          "best_lag_pearson": x.best_lag(lags, "pearson"),
                          "best_lag_spearman": x.best_lag(lags, "spearman")},
        "years_used": good_years, "records_per_year": per_year,
        f"rain_monthly_{other}_vs_station": rain,
        "rain_full_years": full_years,
        "jan_tmin_c_same_days": jan, "may_jun_tmax_c_same_days": summer,
        "day_boundaries": ("POWER = local solar day" if other == "power" else "GPM = UTC day (05:45 to 05:45 Nepal time)")
                          + "; station = GSOD GMT day (05:45 to 05:45 Nepal time; rain may include part of the previous day); "
                          "compare monthly to soften this",
    }
    out = REPO / "data" / "checks" / field / f"crosscheck_{other}_{name}.json"
    out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(f"\n{name}: years used {good_years}")
    print(f"  rain, {rain['n']} complete months: {other} bias {rain['bias_pct']:+.1f}% vs station, r = {rain['r']:.3f}, "
          f"mean abs error {rain['mae']:.1f} mm/month")
    print(f"  rain, years with 12 complete months: {full_years}")
    if has_t:
        print(f"  Jan Tmin, {jan['n']} shared days: station {jan['ref_mean']:.2f} C, POWER {jan['other_mean']:.2f} C, "
              f"POWER - station = {jan['mean_diff']:+.2f} C")
        print(f"  May-Jun Tmax, {summer['n']} shared days: station {summer['ref_mean']:.2f} C, POWER {summer['other_mean']:.2f} C, "
              f"POWER - station = {summer['mean_diff']:+.2f} C")
    for k, v in lags.items():
        print(f"  day alignment lag {k:+d}: pearson {v['pearson']:.3f}, spearman {v['spearman']:.3f}, n {v['n']}")
    print(f"  best lag: pearson {res['day_alignment']['best_lag_pearson']:+d}, spearman {res['day_alignment']['best_lag_spearman']:+d}")
    print(f"-> {out}")


if __name__ == "__main__":
    sys.exit(main())
