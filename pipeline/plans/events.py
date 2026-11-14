"""One weather event per calendar year for the field (contract: none, drought, flood). Pure.

Owner's answer 9 to REVIEW_2 (2026-11-13; rules.yaml `events`, committed before its first run): the event is about
the field's weather, so it is the same on every plan. Until then it was computed from each plan's own crop seasons,
and the same year could differ between plans (7 of 24 years in the demo export).

- drought: the rain of a season is in deciles 1..drought_decile_max of that season over the record (decile =
  ceil(10 x rank / n), average ranks for ties). Seasons are DHM's (rules `seasons`): monsoon June to September;
  winter December to February, counted in the year of its January and February. A season with a month outside the
  record is left out. Where a year's drought comes from one season only, `event_seasons` says which.
- flood: the calendar year's wettest day (ETCCDI Rx1day) is in deciles flood_decile_min..10 of the record's years.
The seasons come from the field's country profile (pipeline/fetch/profiles.events_rules; Nepal's are DHM's above). With
no profile (config/countries/default.yaml) there is one season, the calendar year, summed over wet days only
(`wet_day_mm`: ETCCDI PRCPTOT), and no event season is exported.
A year takes the first of its events in `precedence` order, else 'none'. Both rules are relative: about one season
and one year in five is flagged whatever the amounts.

Frost is not a replay event (owner, 2026-11-12, REVIEW_NOTES M1): it is shown only as a risk band in the monthly
calendar (diary.months[].frost), never per year.
"""
import math

import pandas as pd

EVENTS = ("drought", "flood")


def _deciles(values):
    """decile = ceil(10 x rank / n), ranks ascending with average ranks for ties."""
    ranks = values.rank(method="average")
    return (10 * ranks / len(values)).apply(math.ceil)


def season_totals(rain, months):
    """{season year: rain total} for the seasons whose every day is in the record. A season that crosses the new
    year (December to February) is counted in the year of its January."""
    idx = rain.index
    wraps = 12 in months and 1 in months and len(months) < 12      # the whole year (default profile) does not wrap
    year = pd.Series(idx.year + ((idx.month >= 7) & wraps), index=idx)
    sel = idx.month.isin(months)
    tot, have = rain[sel].groupby(year[sel]).sum(), rain[sel].groupby(year[sel]).count()
    out = {}
    for y in tot.index:
        need = sum(pd.Period(f"{y - 1 if (wraps and m >= 7) else y}-{m:02d}").days_in_month for m in months)
        if have[y] == need:
            out[int(y)] = float(tot[y])
    return out


def field_year_events(rain, rules):
    """rain: daily Series by date, no gaps. Returns {'events': {'2001': 'none' | 'drought' | 'flood', ...},
    'event_seasons': {year: season} for droughts that come from exactly one season, 'detail': per-year numbers}."""
    unknown = [e for e in rules["precedence"] if e not in EVENTS]
    if unknown:
        raise ValueError(f"events.precedence lists {unknown}: replay events are only {list(EVENTS)} "
                         "(frost is a monthly risk band, not a replay event; REVIEW_NOTES M1)")
    rain = pd.Series(rain).astype(float)
    if rain.isna().any():
        raise ValueError(f"missing rain on {int(rain.isna().sum())} day(s): events are never computed over gaps")
    years = sorted(set(rain.index.year))
    dry = {y: [] for y in years}
    detail = {str(y): {} for y in years}
    wet = rules.get("wet_day_mm")             # default profile: PRCPTOT counts only wet days (RR >= 1 mm)
    season_rain = rain if wet is None else rain.where(rain >= float(wet), 0.0)
    for name, months in rules["seasons"].items():
        tot = pd.Series(season_totals(season_rain, list(months)))
        dec = _deciles(tot)
        for y in years:
            detail[str(y)][f"{name}_mm"] = round(float(tot[y]), 1) if y in tot.index else None
            detail[str(y)][f"{name}_decile"] = int(dec[y]) if y in tot.index else None
            if y in tot.index and dec[y] <= rules["drought_decile_max"]:
                dry[y].append(name)
    rx = rain.groupby(rain.index.year).max()
    rx_dec = _deciles(rx)
    events, seasons = {}, {}
    for y in years:
        flags = set()
        if dry[y]:
            flags.add("drought")
        if rx_dec[y] >= rules["flood_decile_min"]:
            flags.add("flood")
        e = next((k for k in rules["precedence"] if k in flags), "none")
        events[str(y)] = e
        if e == "drought" and len(dry[y]) == 1 and len(rules["seasons"]) > 1:
            seasons[str(y)] = dry[y][0]
        detail[str(y)].update(wettest_day_mm=round(float(rx[y]), 1), wettest_day=str(rain[rain.index.year == y].idxmax().date()),
                              flood_class=bool(rx_dec[y] >= rules["flood_decile_min"]), dry_seasons=list(dry[y]))
    return {"events": events, "event_seasons": seasons, "detail": detail}
