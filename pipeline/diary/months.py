"""The twelve-month calendar (CLAUDE.md "Field diary", build step 6c): diary.months[] words. Pure functions.

- rain, soil, heat: terciles of the twelve monthly means of 2001-2025 (CLAUDE.md): the four lowest months take the
  first word, the four highest the last.
- frost: the owner's band (CLAUDE.md "Frost": a frost night is Tmin below 0 C, risk band 0 to 2 C), from the
  coldest night: below 0 C 'high', 0 to under 2 C 'risk', else 'none'. A calendar month takes the band of its median
  coldest night over the years. Frost Tmin overcounts cold nights against the station (CLAUDE.md), so the band
  carries that caveat and is never a count.
- cover: the most common day label of the month in the chosen season method (growing -> crop, harvested ->
  partial, bare -> bare).
"""
import numpy as np
import pandas as pd

COVER = {"growing": "crop", "harvested": "partial", "bare": "bare"}


def tercile_words(values12, words):
    v = np.asarray(values12, float)
    if len(v) != 12 or np.isnan(v).any():
        raise ValueError("terciles need twelve monthly values")
    rank = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    return [words[0] if r < 4 else words[1] if r < 8 else words[2] for r in rank]


def monthly_wetness(dates, dr_mm, taw_mm, years):
    """rules.yaml soil_years: {year: twelve calendar-month means of the daily root-zone share 1 - Dr/TAW, 3 decimals}."""
    s = pd.Series(1 - np.asarray(dr_mm, float) / np.asarray(taw_mm, float), index=pd.DatetimeIndex(dates))
    m = s.groupby([s.index.year, s.index.month]).mean()
    return {y: [round(float(m[(y, k)]), 3) for k in range(1, 13)] for y in years}


def wetness_step(share, edges):
    """The step (0 = driest) of a share between the fixed edges: below edges[0] 0, from edges[-1] up len(edges)."""
    return int(np.searchsorted(edges, share, side="right"))


def frost_band(coldest_c, frost_c, risk_c):
    if coldest_c < frost_c:
        return "high"
    if coldest_c < risk_c:
        return "risk"
    return "none"


def coldest_by_month(tmin):
    """{(year, month): coldest night}"""
    g = tmin.groupby([tmin.index.year, tmin.index.month]).min()
    return {(int(y), int(m)): float(v) for (y, m), v in g.items()}


def frost_by_calendar_month(coldest, frost_c, risk_c):
    """{month: band of the median coldest night of that month over the years}"""
    out = {}
    for m in range(1, 13):
        vals = [v for (y, mm), v in coldest.items() if mm == m]
        out[m] = frost_band(float(np.median(vals)), frost_c, risk_c)
    return out


def cover_sure_by_month(labels_a, labels_b):
    """{month: share of days, 0 to 1, on which two season methods give the same day label}. rules.yaml
    season_detection.cover_sure: the rule (threshold) method against the SI season detective; a low share marks a
    month where the cover word is less sure. Both series must cover the same days."""
    if len(labels_a) != len(labels_b) or not labels_a.index.equals(labels_b.index):
        raise ValueError("the two methods' labels must cover the same days")
    same = pd.Series(labels_a.to_numpy().astype(str) == labels_b.to_numpy().astype(str), index=labels_a.index)
    return {int(m): round(float(s.mean()), 2) for m, s in same.groupby(same.index.month)}


def cover_by_month(labels):
    """{month: cover word of the most common day label}"""
    out = {}
    for m, s in labels.groupby(labels.index.month):
        counts = s.value_counts()
        out[int(m)] = COVER[str(counts.index[0])]
    return out
