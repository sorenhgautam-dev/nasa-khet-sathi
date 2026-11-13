"""Regional water storage trend from GRACE/GRACE-FO (CLAUDE.md D7, build step 6c). Pure functions on the monthly series
that pipeline/fetch/grace.py cleans (data/clean/<field>/grace.parquet, unscaled; owner M4).

JPL mascon CRI RL06.3 v04: lwe_thickness (cm of equivalent water) on a 0.5 deg grid of about 3 deg mascons, so it
is regional context (the whole Kathmandu Valley and far beyond), not the field. It is total water storage
(groundwater, soil water, surface water, snow), labelled "groundwater" in the contract.

Trend: the seasonal Mann-Kendall test (Hirsch & Slack 1984, as pymannkendall.seasonal_test) on a regular monthly
series (missing months NaN, including the 2017-2018 gap between the missions), with the seasonal Sen slope in cm
per year. Direction (rules.yaml groundwater): 'steady' unless p < alpha; then 'falling' or 'rising' by the slope's
sign. Confidence = 1 - p, how strongly the record shows a change (not a probability that the direction is right).
"""
import numpy as np
import pandas as pd


def monthly_series(times, values):
    """Series on a regular monthly PeriodIndex from the first to the last record: two solutions in one month are
    averaged, a month without one is NaN."""
    s = pd.Series(np.asarray(values, float), index=pd.DatetimeIndex(times).to_period("M")).groupby(level=0).mean()
    return s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))


def trend(monthly, alpha):
    """Seasonal Mann-Kendall test and seasonal Sen slope (cm per year) of a monthly series."""
    import pymannkendall as mk
    full = pd.period_range(f"{monthly.index.min().year}-01", f"{monthly.index.max().year}-12", freq="M")
    x = monthly.reindex(full).to_numpy(float)
    r = mk.seasonal_test(x, period=12, alpha=alpha)
    return {"trend_cm_per_year": float(r.slope), "p": float(r.p), "mk_trend": str(r.trend),
            "n_months": int(np.isfinite(x).sum()), "first": str(monthly.index.min()), "last": str(monthly.index.max())}


def direction(slope, p, alpha):
    if p < alpha and slope < 0:
        return "falling"
    if p < alpha and slope > 0:
        return "rising"
    return "steady"


def confidence(p):
    return round(float(min(1.0, max(0.0, 1.0 - p))), 2)
