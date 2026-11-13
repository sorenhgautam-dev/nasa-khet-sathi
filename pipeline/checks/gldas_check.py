"""GLDAS-2.1 Noah (model-based, 0.25 degree) against the twin's soil water and evapotranspiration, monthly anomalies
(VALIDATION 4.2d; rules.yaml validation_checks.gldas, written before the first run). Pure. The same method as the SMAP
check (scripts/run_smap_check.py): each calendar month's own mean removed; correlation with a year-block bootstrap.
"""
import pandas as pd

from pipeline.checks import corr_ci as cc


def twin_monthly(daily):
    """daily: date, dr_mm, taw_mm, eta_mm -> monthly wetness (mean of 1 - Dr/TAW) and ETa (sum), complete months only."""
    d = pd.DataFrame(daily).copy()
    d["date"] = pd.DatetimeIndex(d["date"])
    d["wetness"] = 1.0 - d["dr_mm"].astype(float) / d["taw_mm"].astype(float)
    g = d.groupby(d["date"].dt.to_period("M"))
    m = pd.DataFrame({"wetness": g["wetness"].mean(), "eta_mm": g["eta_mm"].sum(), "days": g.size()})
    m = m[m["days"] == m.index.days_in_month]
    m.index = m.index.to_timestamp()
    return m.drop(columns="days")


def compare_monthly(a, b, agree_r):
    """Pearson/Spearman of the monthly anomalies of two series over their shared months (year blocks), June-September and
    October-May apart, the step at 2017 in standard deviations, and the verdict (Pearson interval's lower bound > agree_r)."""
    j = pd.concat([pd.Series(a, dtype=float), pd.Series(b, dtype=float)], axis=1, join="inner").dropna()
    x, y = cc.monthly_anomaly(j.iloc[:, 0]), cc.monthly_anomaly(j.iloc[:, 1])
    r = cc.correlate(x, y, blocks=x.index.year)
    wet = x.index.month.isin([6, 7, 8, 9])
    out = {"months": int(len(j)), **{k: r[k] for k in ("pearson", "spearman", "pearson_ci", "spearman_ci", "detectable_r")},
           "jun_sep": cc.correlate(x[wet], y[wet], blocks=x.index.year[wet]),
           "oct_may": cc.correlate(x[~wet], y[~wet], blocks=x.index.year[~wet]),
           "step_at_2017_sd": {"twin": cc.step_sd(x, 2017), "gldas": cc.step_sd(y, 2017)}}
    out["holds_up"] = bool(r["pearson_ci"] is not None and r["pearson_ci"][0] > agree_r)
    return out
