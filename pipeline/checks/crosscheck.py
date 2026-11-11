"""Compare two sources (validation layer 3). Pure functions; the reference comes first."""
import numpy as np
import pandas as pd


def complete_month_totals(df, col):
    """Monthly totals, keeping only months where every day is present and not missing."""
    d = df.dropna(subset=[col])
    month = d["date"].dt.to_period("M")
    grouped = d.groupby(month)[col]
    counts, totals = grouped.count(), grouped.sum()
    full = counts.index.to_timestamp().days_in_month == counts.to_numpy()
    return totals[full]


def compare(ref, other):
    """Agreement of `other` with `ref` over shared periods: n, bias_pct, Pearson r, mean abs error."""
    a, b = ref.align(other, join="inner")
    if len(a) == 0:
        return {"n": 0, "bias_pct": None, "r": None, "mae": None}
    return {"n": int(len(a)),
            "bias_pct": float(100 * (b.sum() - a.sum()) / a.sum()),
            "r": float(np.corrcoef(a, b)[0, 1]) if len(a) > 1 else None,
            "mae": float((b - a).abs().mean())}


def paired_difference(ref, other, col):
    """Mean of (other - ref) on days both have a value."""
    j = ref[["date", col]].merge(other[["date", col]], on="date", suffixes=("_ref", "_other")).dropna()
    diff = j[f"{col}_other"] - j[f"{col}_ref"]
    return {"n": int(len(j)), "mean_diff": float(diff.mean()) if len(j) else None,
            "ref_mean": float(j[f"{col}_ref"].mean()) if len(j) else None,
            "other_mean": float(j[f"{col}_other"].mean()) if len(j) else None}
