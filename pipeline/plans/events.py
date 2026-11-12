"""One event per replay year (contract: none, drought, flood), from the weather of each crop season.
Rules and sources in rules.yaml `events`. Pure.

- drought: the season's rain is in deciles 1-2 of that crop's seasons over the record (decile =
  ceil(10 x rank / n), average ranks for ties)
- flood: the year's wettest crop-season day (ETCCDI Rx1day over its seasons' days) is in deciles 9-10
  ("much above normal", `flood_decile_min`) of the record's years. Fixed in advance from those sources and
  never tuned on the known floods, which are validation layer 4.1 (owner, 2026-11-12)
A year takes the first of its events in `precedence` order, else 'none'.

Frost is not a replay event (owner, 2026-11-12, REVIEW_NOTES M1): the frost Tmin is known to overcount cold
nights, so frost is shown only as a risk band in the monthly calendar (diary.months[].frost), never per year.
Nothing here reads a frost rule.
"""
import math

import pandas as pd

EVENTS = ("drought", "flood")


def _deciles(values):
    """decile = ceil(10 x rank / n), ranks ascending with average ranks for ties (as for drought)."""
    ranks = values.rank(method="average")
    return (10 * ranks / len(values)).apply(math.ceil)


def season_flags(seasons, rules):
    """Per season: {'drought'} when its rain is in deciles 1..drought_decile_max of that crop's seasons."""
    df = pd.DataFrame(seasons)
    deciles = df.groupby("crop")["rain_mm"].transform(_deciles)
    return [{"drought"} if d <= rules["drought_decile_max"] else set() for d in deciles]


def flood_years(seasons, rules):
    """Years whose wettest crop-season day (Rx1day over all their seasons) is in deciles flood_decile_min..10
    of the record's years."""
    rx1day = pd.DataFrame(seasons).groupby("year")["rain_max_day_mm"].max()
    deciles = _deciles(rx1day)
    return {int(y) for y, d in deciles.items() if d >= rules["flood_decile_min"]}


def year_events(seasons, rules):
    """{'2001': 'none' | 'drought' | 'flood', ...} for every year that has a season."""
    unknown = [e for e in rules["precedence"] if e not in EVENTS]
    if unknown:
        raise ValueError(f"events.precedence lists {unknown}: replay events are only {list(EVENTS)} "
                         "(frost is a monthly risk band, not a replay event; REVIEW_NOTES M1)")
    out = {}
    for s, f in zip(seasons, season_flags(seasons, rules)):
        out.setdefault(str(s["year"]), set()).update(f)
    for y in flood_years(seasons, rules):
        out[str(y)].add("flood")
    return {y: next((e for e in rules["precedence"] if e in f), "none") for y, f in sorted(out.items())}
