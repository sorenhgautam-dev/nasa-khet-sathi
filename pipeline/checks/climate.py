"""Validation layer 3 ("data sensible"): small pure summaries, plus pass/fail bands.

Bands come from the owner's layer-3 expectations (VALIDATION.md, 2026-11-11). Where the owner wrote
"roughly" or "near", the tolerance is Claude's choice and marked TODO-CONFIRM.
"""
import pandas as pd

EXPECT = {
    "annual_rain_mm": {"band": (1260.0, 1650.0), "said": "Kathmandu yearly rain roughly 1,400 to 1,500 mm",
                       "tolerance": "10% beyond the stated band (TODO-CONFIRM)"},
    "monsoon_share": {"band": (0.5, 1.0), "said": "mostly June to September",
                      "tolerance": "'mostly' read as more than half of the year's rain (TODO-CONFIRM)"},
    "jan_tmin_c": {"band": (-3.0, 3.0), "said": "January nights near freezing",
                   "tolerance": "mean January minimum within 3 C of 0 C (TODO-CONFIRM)"},
    "early_summer_tmax_c": {"band": (27.0, 33.0), "said": "early-summer days near 30 C",
                            "tolerance": "mean May-June maximum within 3 C of 30 C (TODO-CONFIRM)"},
}


def mean_annual_total(df, col):
    """Mean of yearly totals over complete years only (every day present, none missing)."""
    d = df.assign(year=df["date"].dt.year)
    totals, years = [], []
    for year, grp in d.groupby("year"):
        n_days = 366 if pd.Timestamp(year, 12, 31).day_of_year == 366 else 365
        if len(grp) == n_days and grp[col].notna().all():
            totals.append(grp[col].sum())
            years.append(int(year))
    return (sum(totals) / len(totals) if totals else float("nan")), years


def share_in_months(df, col, months):
    return df.loc[df["date"].dt.month.isin(months), col].sum() / df[col].sum()


def month_mean(df, col, months):
    return df.loc[df["date"].dt.month.isin(months), col].mean()


def judge(value, band):
    return "PASS" if band[0] <= value <= band[1] else "FAIL"
