"""Owner decision A (2026-11-11): monthly additive correction of a POWER temperature column from days
shared with a nearby station. The model cell cannot resolve valley cold-air pooling (POWER's January
minimum was 3.8 C warmer than Kathmandu Airport on shared days).

Method: offset(month) = mean(POWER - station) over shared days of that month. Validate by fitting on
alternate qualifying years and testing on the others; the correction actually applied is refitted on
all qualifying years, and only if it lowered the error on the held-out years. Pure functions.
"""
import numpy as np
import pandas as pd


def shared_days(power, station, col):
    j = power[["date", col]].merge(station[["date", col]], on="date", suffixes=("_power", "_station")).dropna()
    j["year"], j["month"] = j["date"].dt.year, j["date"].dt.month
    return j


def qualifying_years(shared, min_days):
    counts = shared.groupby("year").size()
    return sorted(int(y) for y, n in counts.items() if n >= min_days)


def split_years(years):
    years = sorted(years)
    return years[0::2], years[1::2]


def fit_monthly_offsets(shared, years, min_days_per_month):
    col_p, col_s = [c for c in shared.columns if c.endswith("_power")][0], [c for c in shared.columns if c.endswith("_station")][0]
    d = shared[shared["year"].isin(years)]
    out = {}
    for m in range(1, 13):
        sub = d[d["month"] == m]
        n = int(len(sub))
        out[m] = {"offset": float((sub[col_p] - sub[col_s]).mean()) if n >= min_days_per_month else None, "n": n}
    return out


def months_without_offset(offsets):
    """Months (1-12) that have no fitted offset. apply_offsets() leaves them uncorrected, so callers must
    report them loudly (REVIEW_NOTES M8): pipeline/fetch/weather.py prints a warning and records them in the card."""
    return sorted(int(m) for m, o in offsets.items() if o.get("offset") is None)


def apply_offsets(df, col, offsets):
    """Return corrected values (a new Series); months without an offset are left as they are (list them with
    months_without_offset() and report them)."""
    off = df["date"].dt.month.map(lambda m: offsets.get(m, {}).get("offset"))
    off = pd.to_numeric(off, errors="coerce").fillna(0.0)
    return df[col] - off.to_numpy()


def evaluate(shared, years, offsets, col):
    d = shared[shared["year"].isin(years)]
    before = d[f"{col}_power"] - d[f"{col}_station"]
    corrected = apply_offsets(d.rename(columns={f"{col}_power": col}), col, offsets)
    after = corrected.to_numpy() - d[f"{col}_station"].to_numpy()
    return {"n": int(len(d)),
            "mae_before": float(np.abs(before).mean()) if len(d) else None,
            "mae_after": float(np.abs(after).mean()) if len(d) else None,
            "bias_before": float(before.mean()) if len(d) else None,
            "bias_after": float(after.mean()) if len(d) else None}


def build_correction(power, station, col, min_days_per_year, min_days_per_month):
    shared = shared_days(power, station, col)
    years = qualifying_years(shared, min_days_per_year)
    fit, test = split_years(years)
    split_offsets = fit_monthly_offsets(shared, fit, min_days_per_month)
    result = evaluate(shared, test, split_offsets, col)
    helps = bool(result["n"] and result["mae_after"] < result["mae_before"])
    return {"column": col, "qualifying_years": years, "fit_years": fit, "test_years": test,
            "split_offsets": split_offsets, "test": result,
            "offsets": fit_monthly_offsets(shared, years, min_days_per_month), "apply": helps}
