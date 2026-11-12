"""One event per replay year (contract: none, drought, flood), from the weather of each crop season.
Rules and sources in rules.yaml `events`. Pure.

- drought: the season's rain is in deciles 1-2 of that crop's seasons over the record (decile =
  ceil(10 x rank / n), average ranks for ties)
- flood: a day in the season with at least `flood_day_mm` (DHM 'very heavy')
A year takes the first of its seasons' events in `precedence` order, else 'none'.

Frost is not a replay event (owner, 2026-11-12, REVIEW_NOTES M1): the frost Tmin is known to overcount cold
nights, so frost is shown only as a risk band in the monthly calendar (diary.months[].frost), never per year.
Nothing here reads a frost rule.
"""
import math

import pandas as pd

EVENTS = ("drought", "flood")


def season_flags(seasons, rules):
    df = pd.DataFrame(seasons)
    ranks = df.groupby("crop")["rain_mm"].rank(method="average")
    n = df.groupby("crop")["crop"].transform("size")
    flags = []
    for i, s in df.iterrows():
        f = set()
        if math.ceil(10 * ranks[i] / n[i]) <= rules["drought_decile_max"]:
            f.add("drought")
        if s["rain_max_day_mm"] >= rules["flood_day_mm"]:
            f.add("flood")
        flags.append(f)
    return flags


def year_events(seasons, rules):
    """{'2001': 'none' | 'drought' | 'flood', ...} for every year that has a season."""
    unknown = [e for e in rules["precedence"] if e not in EVENTS]
    if unknown:
        raise ValueError(f"events.precedence lists {unknown}: replay events are only {list(EVENTS)} "
                         "(frost is a monthly risk band, not a replay event; REVIEW_NOTES M1)")
    out = {}
    for s, f in zip(seasons, season_flags(seasons, rules)):
        out.setdefault(str(s["year"]), set()).update(f)
    return {y: next((e for e in rules["precedence"] if e in f), "none") for y, f in sorted(out.items())}
