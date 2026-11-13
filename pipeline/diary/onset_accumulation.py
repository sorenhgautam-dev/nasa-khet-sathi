"""A second monsoon-onset measure: the anomalous accumulation (rules.yaml onset_accumulation). Pure functions.

Noska & Misra 2016 (GRL 43, 4547-4554, p. 4548, eqs. 1-2), building on Liebmann & Marengo 2001 and Liebmann et al. 2007:
    C(i) = sum over n = 1..i of (D(n) - Dbar),   n = 1 is 1 January of the year,
    onset = the day after C reaches its absolute minimum, the minimum searched from 1 January to 30 September
('before the last three months of the year'). No threshold, no smoothing.
Dbar, by variant (both fixed in rules.yaml before the first run):
    climatological  the mean daily rain over every day of the record (the paper exactly);
    own_year        the mean daily rain of that calendar year (Claude's variant: a year's rain times k gives C times
                    k, so the day of the minimum, and the onset, cannot move with the level of rain, e.g. the 2017
                    GPM gauge-loss break).
Ties go to the first day that reaches the minimum; a year whose C is flat over the search has no onset. Every year
must be complete: a missing day or value fails loudly (golden rule 12c), the rain is never filled here.
The kept rule (pipeline/diary/onset.py, rules.yaml monsoon_onset) is not changed by this module.
"""
import numpy as np
import pandas as pd

TIE_MM = 1e-9          # two C values closer than this are the same minimum (floating-point sums)


def calendar_day(day):
    """Day number of the month and day in a non-leap year (15 June = 166 in every year); 29 February = 60."""
    day = pd.Timestamp(day)
    n = day.dayofyear
    return n - 1 if (day.is_leap_year and day.month > 2) else n


def calendar_day_to_text(n):
    """166 -> '15 Jun' (a non-leap year)."""
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(int(round(n)) - 1, unit="D")).strftime("%d %b").lstrip("0")


def _complete_years(rain):
    """The rain sorted, after checking every year in it is complete (no missing date, no missing value)."""
    rain = rain.sort_index()
    if rain.index.has_duplicates:
        raise ValueError("anomalous accumulation: repeated dates in the rain record")
    for y, s in rain.groupby(rain.index.year):
        want = pd.date_range(f"{y}-01-01", f"{y}-12-31")
        if len(s) != len(want) or not s.index.equals(want):
            raise ValueError(f"anomalous accumulation {y}: missing dates ({len(s)} of {len(want)} days); "
                             "the method needs whole calendar years")
        if s.isna().any():
            raise ValueError(f"anomalous accumulation {y}: {int(s.isna().sum())} missing rain value(s), "
                             f"e.g. {s[s.isna()].index[0].date()}")
    return rain


def reference_rates(rain, variant):
    """{year: Dbar in mm per day} for the variant ('climatological' or 'own_year')."""
    rain = _complete_years(rain)
    years = sorted(set(rain.index.year))
    if variant == "climatological":
        dbar = float(rain.mean())
        return {y: dbar for y in years}
    if variant == "own_year":
        return {y: float(s.mean()) for y, s in rain.groupby(rain.index.year)}
    raise ValueError(f"unknown variant '{variant}' (climatological or own_year)")


def accumulation(rain_year, dbar):
    """C(i) for one calendar year: the running sum of (rain - Dbar) from 1 January, mm."""
    return (rain_year.sort_index() - dbar).cumsum()


def at_edge(minimum_on, search_until, edge_days):
    """True when the minimum lies within edge_days of 1 January or of the year's search_until ('MM-DD')."""
    minimum_on = pd.Timestamp(minimum_on)
    first = pd.Timestamp(f"{minimum_on.year}-01-01")
    last = pd.Timestamp(f"{minimum_on.year}-{search_until}")
    return (minimum_on - first).days <= edge_days or (last - minimum_on).days <= edge_days


def onset_in_year(rain_year, dbar, search_until="09-30"):
    """{'onset', 'minimum_on', 'minimum_mm'} for one calendar year; all None when C is flat over the search."""
    rain_year = rain_year.sort_index()
    year = rain_year.index[0].year
    c = accumulation(rain_year, dbar).loc[:pd.Timestamp(f"{year}-{search_until}")]
    v = c.to_numpy(float)
    if v.max() - v.min() <= TIE_MM:
        return {"onset": None, "minimum_on": None, "minimum_mm": None}
    i = int(np.flatnonzero(v <= v.min() + TIE_MM)[0])          # the first day that reaches the minimum
    return {"onset": c.index[i] + pd.Timedelta(1, unit="D"), "minimum_on": c.index[i], "minimum_mm": float(v[i])}


def onsets(rain, variant, rules):
    """Onset per year for one variant.
    {'dates': {'2001': 'YYYY-MM-DD' | None}, 'calendar_day': {'2001': 166 | None}, 'minimum_on': {...},
     'reference_rate_mm_per_day': {...}, 'at_edge': [years whose minimum is at a window edge]}"""
    search_until = "09-30"
    rain = _complete_years(rain)
    rates = reference_rates(rain, variant)
    out = {"dates": {}, "calendar_day": {}, "minimum_on": {}, "reference_rate_mm_per_day": {}, "at_edge": []}
    for y, s in rain.groupby(rain.index.year):
        r = onset_in_year(s, rates[y], search_until)
        k = str(y)
        out["reference_rate_mm_per_day"][k] = round(rates[y], 4)
        out["dates"][k] = None if r["onset"] is None else r["onset"].strftime("%Y-%m-%d")
        out["calendar_day"][k] = None if r["onset"] is None else calendar_day(r["onset"])
        out["minimum_on"][k] = None if r["minimum_on"] is None else r["minimum_on"].strftime("%Y-%m-%d")
        if r["minimum_on"] is not None and at_edge(r["minimum_on"], search_until, rules["edge_days"]):
            out["at_edge"].append(int(y))
    return out


def trust(median_day, window, edge_years, t_corrected, t_uncorrected, alpha):
    """The pre-declared trust test (rules.yaml onset_accumulation.trust_test) for one variant.
    median_day: the median onset as a calendar day on the corrected rain (None if no year has one); window: the
    sanity window ['MM-DD', 'MM-DD'], inclusive; edge_years: {'corrected': [...], 'uncorrected': [...]};
    t_*: {'slope_per_year', 'low', 'high', 'p'} (pipeline/diary/trends.mk_sen)."""
    lo, hi = (calendar_day(pd.Timestamp(f"2001-{d}")) for d in window)
    sanity = median_day is not None and lo <= median_day <= hi
    not_pinned = not any(edge_years.get(v) for v in ("corrected", "uncorrected"))
    same_sign = t_corrected["slope_per_year"] * t_uncorrected["slope_per_year"] >= 0
    overlap = max(t_corrected["low"], t_uncorrected["low"]) <= min(t_corrected["high"], t_uncorrected["high"])
    robust = bool(same_sign and overlap)
    return {"sanity": bool(sanity), "sanity_window_calendar_days": [lo, hi], "not_pinned": bool(not_pinned),
            "slopes_same_sign": bool(same_sign), "ranges_overlap": bool(overlap), "robust_to_rain": robust,
            "trusted": bool(sanity and not_pinned and robust),
            "clear_shift": bool(t_corrected["p"] < alpha)}


def shift_export(trusted, t):
    """{'shift_days', 'shift_days_low', 'shift_days_high'}: Sen's slope and its range x (last - first year) when the
    measure is trusted, else all None ('can't tell'). Kept when the range includes 0: that is 'no clear shift'."""
    if not trusted:
        return {"shift_days": None, "shift_days_low": None, "shift_days_high": None}
    n = t["last"] - t["first"]
    return {"shift_days": round(t["slope_per_year"] * n, 1), "shift_days_low": round(t["low"] * n, 1),
            "shift_days_high": round(t["high"] * n, 1)}


def agreement(ours, reference):
    """Year-by-year agreement of two {year: calendar day} series over the years both have: n, Spearman's rank
    correlation (None under 3 years) and the median of ours - reference in days."""
    from scipy.stats import spearmanr
    yrs = sorted(int(y) for y, v in ours.items() if v is not None
                 and reference.get(int(y), reference.get(str(y))) is not None)
    a = np.array([ours[y] if y in ours else ours[str(y)] for y in yrs], float)
    b = np.array([reference[y] if y in reference else reference[str(y)] for y in yrs], float)
    rho, p = (float(x) for x in spearmanr(a, b)) if len(yrs) >= 3 else (None, None)
    return {"n": len(yrs), "years": [yrs[0], yrs[-1]] if yrs else None, "spearman": rho, "spearman_p": p,
            "median_difference_days": float(np.median(a - b)) if yrs else None}


def plain_words(trusted, clear_shift, shift_days, median_text):
    """Farmer-facing English, at most 8 words a sentence; always names the 2017 rain-record change."""
    if not trusted:
        return ("We cannot tell if the rains moved. Rain records changed in 2017. "
                "So we do not guess.")
    first = f"The rains usually start around {median_text}."
    if not clear_shift:
        return f"{first} We see no clear change since 2001. Rain records changed in 2017, so be careful."
    way = "earlier" if shift_days < 0 else "later"
    return (f"{first} They now start about {abs(round(shift_days)):.0f} days {way}. "
            "Rain records changed in 2017, so be careful.")
