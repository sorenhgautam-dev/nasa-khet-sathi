"""Three small checks of a plan's crops (owner's brief, 2026-11-14; rules.yaml rain_risk, fertiliser_saver, heat_clock).
Pure: no file or network I/O.

- Rain risk: in how many past years a heavy-rain day (DHM: 50 mm or more) fell in a crop's harvest weeks (its FAO-56
  late-season stage); and the longest run of dry days (DHM's CDD, under 1 mm) from sowing to the crop's last day.
- Heat and cold clock: days too hot or too cold (FAO-66; FAO's Bread Wheat for floret heat and flowering frost) in a
  crop's sensitive weeks, in our weather and in the NEX-GDDP climate models' past and 2026-2040.
- Fertiliser saver: the urea the next crop after a legume may not need, from a published carry-over range.

A window is two MM-DD dates, the same every year; when it crosses 1 January it belongs to the year it ends.
"""
import math
from statistics import median

import numpy as np
import pandas as pd


def window_mmdd(crop, lib, stage):
    """(first, last) MM-DD of a plan crop ({crop, start, end}): its whole season, its FAO-56 late stage (the last
    stages_days.late days, ending on the crop's last day), or days (a, b) after the sowing day (day 0), counted in a
    365-day year."""
    if stage == "season":
        return crop["start"], crop["end"]
    if isinstance(stage, tuple):
        sow = pd.Timestamp(f"2002-{crop['start']}")
        return tuple(_mmdd(sow + pd.Timedelta(int(d), unit="D")) for d in stage)
    end = pd.Timestamp(f"2002-{crop['end']}")
    return _mmdd(end - pd.Timedelta(int(lib[crop["crop"]]["stages_days"]["late"]) - 1, unit="D")), crop["end"]


def _mmdd(t):
    return f"{t.month:02d}-{t.day:02d}"


def _md(s):
    return int(s.replace("-", ""))


def window_days(first, last):
    """Days in an MM-DD window, both ends counted, in a 365-day year."""
    return (pd.Timestamp(f"2002-{last}") - pd.Timestamp(f"{2001 if _md(first) > _md(last) else 2002}-{first}")).days + 1


def season_of(years, months, days, first, last):
    """The season (the year its window ends) of each day, NaN outside the window. Works in any model calendar."""
    md = np.asarray(months, int) * 100 + np.asarray(days, int)
    f, t = _md(first), _md(last)
    inside = (md >= f) & (md <= t) if f <= t else (md >= f) | (md <= t)
    year = np.asarray(years, int) + ((md >= f) & (f > t))
    return np.where(inside, year, np.nan)


def complete_seasons(first_year, last_year, first, last):
    """The seasons whose whole window lies in a record of whole years first_year..last_year."""
    return list(range(first_year + (1 if _md(first) > _md(last) else 0), last_year + 1))


def heavy_rain_years(dates, rain_mm, first, last, seasons, threshold_mm):
    """[{year, days, max_mm}]: per season, the days of threshold_mm or more (inclusive) in the window and its largest day."""
    d = pd.DatetimeIndex(dates)
    s = season_of(d.year, d.month, d.day, first, last)
    r = np.asarray(rain_mm, float)
    out = []
    for y in seasons:
        x = r[s == y]
        out.append({"year": int(y), "days": int((x >= threshold_mm).sum()), "max_mm": round(float(x.max()), 1)})
    return out


def longest_dry_runs(dates, rain_mm, first, last, seasons, dry_mm):
    """{season: the longest run of consecutive days with rain under dry_mm inside its window} (DHM's CDD, counted per
    season: a run is cut at both ends of the window). The days must follow each other with no gap."""
    d, r = pd.DatetimeIndex(dates), np.asarray(rain_mm, float)
    if (np.diff(d.values) != np.timedelta64(1, "D")).any() or np.isnan(r).any():
        raise ValueError("a gap, a missing day or days out of order: dry runs are never counted over gaps")
    s, dry = season_of(d.year, d.month, d.day, first, last), r < dry_mm
    out = {}
    for y in seasons:
        best = run = 0
        for v in dry[s == y]:
            run = run + 1 if v else 0
            best = max(best, run)
        out[int(y)] = best
    return out


def typical_worst(by_year, worst=3):
    """The typical year (the median, rounded half up to whole days) and the `worst` longest with their years (ties: the
    later year first)."""
    return {"typical": math.floor(median(by_year.values()) + 0.5),
            "worst": [{"year": int(y), "days": int(v)} for y, v in sorted(by_year.items(), key=lambda kv: (-kv[1], -kv[0]))[:worst]]}


def risky(values, rule):
    """The rule's test, day by day: above_c (strictly above), at_or_above_c, below_c (strictly below), at_or_below_c."""
    v = np.asarray(values, float)
    if "above_c" in rule:
        return v > rule["above_c"]
    if "at_or_above_c" in rule:
        return v >= rule["at_or_above_c"]
    if "below_c" in rule:
        return v < rule["below_c"]
    return v <= rule["at_or_below_c"]


def days_by_season(years, months, days, values, rule, first, last, seasons):
    """{season: risky days in its window}."""
    s = season_of(years, months, days, first, last)
    hit = risky(values, rule)
    return {int(y): int(hit[s == y].sum()) for y in seasons}


def model_means(df, column, rule, first, last, periods):
    """{model: {experiment: mean risky days per complete season}}, each model in its own calendar.
    df: NEX-GDDP rows (model, experiment, year, month, day, <column>); periods: {experiment: (first_year, last_year)}."""
    out = {}
    for (model, exp), g in df[df["experiment"].isin(list(periods))].groupby(["model", "experiment"], sort=True):
        seasons = complete_seasons(*periods[exp], first, last)
        n = days_by_season(g["year"], g["month"], g["day"], g[column], rule, first, last, seasons)
        out.setdefault(model, {})[exp] = round(sum(n.values()) / len(seasons), 2)
    return out


def scenario_summary(means, scenario, past="historical"):
    """Across models: the median of the scenario's means, the lowest and highest, the median of the models' own past
    means, and every model's own pair."""
    models = sorted(m for m in means if scenario in means[m] and past in means[m])
    fut, old = [means[m][scenario] for m in models], [means[m][past] for m in models]
    return {"median": round(median(fut), 2), "low": min(fut), "high": max(fut), "past_median": round(median(old), 2),
            "models": [{"model": m, "past": means[m][past], "future": means[m][scenario]} for m in models]}


def urea_n_share(weights):
    """Nitrogen's mass share of urea, CO(NH2)2 = CH4N2O, from atomic weights {H, C, N, O}."""
    n = 2 * weights["N"]
    return n / (weights["C"] + weights["O"] + n + 4 * weights["H"])


def urea_saved(n_kg_ha, share, bag_kg):
    """The urea (kg and bags per hectare) that holds the given nitrogen range."""
    urea = [n / share for n in n_kg_ha]
    return {"n_kg_ha": list(n_kg_ha), "urea_kg_ha": [round(u) for u in urea],
            "bags_ha": [round(u / bag_kg, 1) for u in urea], "bags_ha_whole": [round(u / bag_kg) for u in urea]}
