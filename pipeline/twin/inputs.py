"""Assembling the twin's inputs. Pure functions.

Rain (decisions D6 and D, 2026-11-11): GPM IMERG is the twin's rain. POWER fills only days GPM lacks,
never from 2001-2003 (POWER's rain then is about half of later years), and every filled day is flagged.
Without any GPM record, rain is missing: POWER never stands in for the whole series. POWER may fill at
most rules.yaml power_rain.max_filled_fraction_per_year of any year's days inside GPM's own record
(REVIEW_NOTES M2): fill_by_year() counts, fill_cap_breaches() lists the years over the cap.

Humidity for ET0 (owner decision, 2026-11-12, REVIEW_NOTES M6): POWER's RH2M belongs to POWER's own,
uncorrected temperatures, so the actual vapour pressure is held from POWER, ea = RH2M / 100 x
(e0(Tmax_POWER) + e0(Tmin_POWER)) / 2 (FAO-56 eq. 19 with POWER's temperatures), capped at e0 of the
corrected Tmin (the dew point cannot exceed the night's minimum), and passed to ET0 with the corrected
temperatures. Holding RH instead (eq. 19 with the corrected temperatures) lowers ea wherever the correction
cools the night; that choice is kept as a second column for comparison (et0_choice_summary).
"""
import numpy as np
import pandas as pd

from pipeline.twin.et0 import e0_kpa, es_kpa


def merge_rain(dates, primary, fallback, never_years, primary_name="gpm", fallback_name="power"):
    dates = pd.DatetimeIndex(dates)
    nan = pd.Series(np.nan, index=dates)
    p = nan if primary is None else primary.reindex(dates)
    f = nan if (fallback is None or primary is None) else fallback.reindex(dates)
    allowed = ~dates.year.isin(list(never_years))
    use_p = p.notna().to_numpy()
    use_f = (~use_p) & f.notna().to_numpy() & allowed
    rain = np.where(use_p, p.to_numpy(), np.where(use_f, f.to_numpy(), np.nan))
    source = np.where(use_p, primary_name, np.where(use_f, f"{fallback_name}_fill", "missing"))
    return pd.DataFrame({"date": dates, "rain_mm": rain, "rain_source": source, "rain_filled": use_f})


def covered_year_runs(has_value, min_fraction):
    """Runs of consecutive calendar years in which at least `min_fraction` of days have a value.
    has_value: boolean Series indexed by date. Returns [(first_year, last_year), ...]."""
    s = has_value.groupby(has_value.index.year).agg(lambda v: v.sum() / (366 if v.index[0].is_leap_year else 365))
    good = [int(y) for y, f in s.items() if f >= min_fraction]
    runs = []
    for y in good:
        if runs and runs[-1][1] == y - 1:
            runs[-1] = (runs[-1][0], y)
        else:
            runs.append((y, y))
    return runs


def fill_by_year(merged, primary_name="gpm"):
    """merged: merge_rain() output. Days of each calendar year inside the primary's own record (its first to
    last day with a value), and how many of them were filled or stay missing. Filled days outside that record
    are only counted: the replay already refuses them (pipeline/plans/simulate.py rain_record_problems)."""
    d = pd.DatetimeIndex(merged["date"])
    src = merged["rain_source"].astype(str).to_numpy()
    filled = merged["rain_filled"].to_numpy(dtype=bool)
    has = src == primary_name
    if not has.any():
        return {"primary_record": None, "by_year": {}, "filled_outside_primary_record": 0}
    first, last = d[has].min(), d[has].max()
    inside = ((d >= first) & (d <= last))
    by_year = {}
    for y in sorted(set(d[inside].year)):
        sel = inside & (d.year == y)
        n, k = int(sel.sum()), int((sel & filled).sum())
        by_year[int(y)] = {"days": n, "filled": k, "missing": int((sel & (src == "missing")).sum()),
                           "fraction_filled": k / n}
    return {"primary_record": [str(first.date()), str(last.date())], "by_year": by_year,
            "filled_outside_primary_record": int((filled & ~inside).sum())}


def fill_cap_breaches(by_year, max_fraction):
    """Years whose filled fraction is above max_fraction: [{year, filled, days, fraction_filled}, ...]."""
    return [{"year": y, "filled": v["filled"], "days": v["days"], "fraction_filled": v["fraction_filled"]}
            for y, v in sorted(by_year.items()) if v["fraction_filled"] > max_fraction]


def ea_held_from_power_kpa(rh_pct, tmax_power_c, tmin_power_c, tmin_c):
    """Actual vapour pressure (kPa) held from POWER, capped at e0 of the corrected Tmin (see top).
    Returns (ea, capped): numpy arrays, capped True where the cap binds."""
    ea = np.asarray(rh_pct, dtype=float) / 100.0 * np.asarray(es_kpa(tmax_power_c, tmin_power_c), dtype=float)
    cap = np.asarray(e0_kpa(tmin_c), dtype=float)
    capped = ea > cap
    return np.where(capped, cap, ea), capped


def et0_choice_summary(dates, et0_used, et0_rh_held, capped):
    """Compare the ET0 the twin uses (ea held from POWER, capped) with the RH-held alternative.
    Mean annual totals over complete calendar years; mean daily difference (used minus RH-held) by month;
    the largest daily difference; the days the cap binds, in all and by month."""
    d = pd.DatetimeIndex(dates)
    a, b = np.asarray(et0_used, dtype=float), np.asarray(et0_rh_held, dtype=float)
    cap = np.asarray(capped, dtype=bool)
    t = pd.DataFrame({"year": d.year, "month": d.month, "a": a, "b": b, "diff": a - b})
    size = t.groupby("year").size()
    full = [int(y) for y, n in size.items() if n == (366 if pd.Timestamp(year=int(y), month=1, day=1).is_leap_year else 365)]
    annual = t[t["year"].isin(full)].groupby("year")[["a", "b"]].sum().mean()
    i = int(np.nanargmax(np.abs(t["diff"].to_numpy())))
    by_month_cap = pd.Series(cap).groupby(d.month).sum()
    return {"years": full,
            "mean_annual_mm": {"et0_mm": float(annual["a"]), "et0_rh_held_mm": float(annual["b"])},
            "mean_daily_diff_mm_by_month": {int(m): float(v) for m, v in t.groupby("month")["diff"].mean().items()},
            "largest_daily_diff": {"date": str(d[i].date()), "diff_mm": float(t["diff"].iloc[i]),
                                   "et0_mm": float(a[i]), "et0_rh_held_mm": float(b[i])},
            "cap_days": int(cap.sum()),
            "cap_days_by_month": {int(m): int(v) for m, v in by_month_cap.items() if v > 0}}
