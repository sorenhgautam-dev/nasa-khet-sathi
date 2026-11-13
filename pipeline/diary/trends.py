"""Trends for the field diary (CLAUDE.md "Field diary", build step 6c). Pure functions.

Mann-Kendall test (pymannkendall.original_test) for the p-value, Sen's slope with its confidence range
(scipy.stats.theilslopes, Sen 1968) on the actual years. Indices follow ETCCDI's definitions
(etccdi.pacificclimate.org list of 27 indices): CDD (longest run of days with RR < 1 mm, per calendar year),
R20mm (days with RR >= 20 mm) and, as a count of days, TX90p (TX above the calendar-day 90th percentile centred on
a 5-day window; the base period here is the record itself, 2001-2025, not 1961-1990, and the in-base bootstrap is
not applied). Every rain-based trend carries the GPM-break caveat (rules.yaml gpm_series.trend_caveat).
"""
import numpy as np
import pandas as pd


def mk_sen(values_by_year, alpha):
    """{year: value or None} -> {slope_per_year, low, high, p, trend, n} (range at 1 - alpha)."""
    import pymannkendall as mk
    from scipy.stats import theilslopes
    yrs = sorted(int(y) for y, v in values_by_year.items() if v is not None and np.isfinite(v))
    if len(yrs) < 4:
        raise ValueError(f"a trend needs at least 4 years with a value, got {len(yrs)}")
    x = np.array([values_by_year[y] if y in values_by_year else values_by_year[str(y)] for y in yrs], float)
    r = mk.original_test(x, alpha=alpha)
    ts = theilslopes(x, np.array(yrs, float), alpha=1 - alpha)
    return {"slope_per_year": float(ts.slope), "low": float(ts.low_slope), "high": float(ts.high_slope),
            "p": float(r.p), "trend": str(r.trend), "n": len(yrs), "first": yrs[0], "last": yrs[-1]}


def over_record(t, first_year, last_year):
    """(change, low, high) over the record: Sen's slope and its range times (last_year - first_year)."""
    n = last_year - first_year
    return (round(t["slope_per_year"] * n, 1), round(t["low"] * n, 1), round(t["high"] * n, 1))


def pinned_years(doy_by_year, search_from, within_days):
    """How many years' onset falls within within_days of that year's own search start ('MM-DD').

    A fixed date's day-of-year is one higher in a leap year (17 May is day 138, not 137), so each year is compared
    with its own start, never with one year's day number (REVIEW_2 M10)."""
    n = 0
    for y, v in doy_by_year.items():
        if v is None:
            continue
        n += int(v - pd.Timestamp(f"{int(y)}-{search_from}").dayofyear <= within_days)
    return n


def without_years(values_by_year, years):
    """The same {year: value} without the named years (for a trend shown beside the full one, REVIEW_2 H8)."""
    drop = {int(y) for y in years}
    return {y: v for y, v in values_by_year.items() if int(y) not in drop}


def longest_dry_spell(rain, wet_mm):
    """{year: longest run of days with rain < wet_mm inside the calendar year} (ETCCDI CDD)."""
    out = {}
    for y, s in rain.groupby(rain.index.year):
        best = run = 0
        for v in s.to_numpy(float):
            if np.isnan(v):
                raise ValueError(f"missing rain in {y}: dry spells are never computed over gaps")
            run = run + 1 if v < wet_mm else 0
            best = max(best, run)
        out[int(y)] = best
    return out


def heavy_rain_days(rain, mm):
    """{year: days with rain >= mm} (ETCCDI R20mm for mm = 20)."""
    return {int(y): int((s >= mm).sum()) for y, s in rain.groupby(rain.index.year)}


def _calendar_day(index):
    """Day 1-366 of the month-day in a leap year, so 29 Feb is 60 and 1 Mar is 61 in every year."""
    return np.array([pd.Timestamp(2000, d.month, d.day).dayofyear for d in index])


def hot_days(tmax, base_years, pct, window_days):
    """{year: days with Tmax above the calendar-day pct-th percentile of the base years, window centred}."""
    cday = _calendar_day(tmax.index)
    v = tmax.to_numpy(float)
    base = (tmax.index.year >= base_years[0]) & (tmax.index.year <= base_years[1])
    half = window_days // 2
    thr = np.full(367, np.nan)
    for c in range(1, 367):
        dist = np.abs(cday - c)
        dist = np.minimum(dist, 366 - dist)
        sel = base & (dist <= half) & np.isfinite(v)
        thr[c] = np.percentile(v[sel], pct)
    hot = v > thr[cday]
    return {int(y): int(hot[tmax.index.year == y].sum()) for y in sorted(set(tmax.index.year))}
