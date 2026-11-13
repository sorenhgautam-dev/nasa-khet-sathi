"""Plan generation (CLAUDE.md "Plans" step 1, build step 7). Pure functions.

A season option is {crop, window, position}: one of the crop's sowing windows in config/crops.json and the start,
middle or end of it (crops.sow_date; owner's batch decisions item 10). A plan is one season option or several that
fit one year without overlapping, repeated every year: each season is sown after the previous one ends, and the last
ends before the first is sown the next year (the same rule as simulate.rotation_plan: sowing the day after a harvest
is allowed). Only crops the twin can simulate (with stage lengths) take part, and only windows whose own season
lengths include the twin's (window_fits_length). Water source and zone: the demo field's
water is unknown, so no window is excluded; windows noted 'irrigated' are flagged by the scorer, not dropped.
"""
from itertools import combinations

import pandas as pd

from pipeline.twin.crops import season_length, sow_date

REF_YEAR = 2001                     # a non-leap reference year for ordering and fitting


def window_fits_length(crop, window):
    """True when the twin's season length (the crop's stage lengths) lies inside the window's own range of
    season lengths ('days' in crops.json). Otherwise the window describes a different crop length (e.g. a 180-day
    wheat) and the twin would grow the wrong one, so the window is not used (2026-11-13)."""
    days = [int(d) for d in crop["calendar"]["windows"][window]["days"]]
    return bool(min(days) <= season_length(crop["stages_days"]) <= max(days))


def options(lib, crops, positions):
    return [{"crop": c, "window": i, "position": p}
            for c in crops for i in range(len(lib[c]["calendar"]["windows"]))
            if window_fits_length(lib[c], i) for p in positions]


def season_in_year(spec, lib, year):
    """(sow, end) of a season option sown in `year`; end = sow + season length - 1."""
    crop = lib[spec["crop"]]
    s = sow_date(crop["calendar"], year, spec["position"], window=spec["window"])
    return s, s + pd.Timedelta(season_length(crop["stages_days"]) - 1, unit="D")


def ordered(specs, lib):
    return sorted(specs, key=lambda sp: season_in_year(sp, lib, REF_YEAR)[0])


def fits(specs, lib):
    """True when the seasons fit one year without overlapping, also across the turn of the year."""
    specs = ordered(specs, lib)
    spans = [season_in_year(sp, lib, REF_YEAR) for sp in specs]
    nxt = spans[1:] + [tuple(t + pd.DateOffset(years=1) for t in spans[0])]
    return all(n[0] > e for (_, e), n in zip(spans, nxt)) and spans[-1][1] - spans[0][0] < pd.Timedelta(365, unit="D")


def plan_id(specs):
    return "+".join(f"{sp['crop']}.w{sp['window']}.{sp['position']}" for sp in specs)


def generate(lib, crops, positions, max_seasons=3):
    """Every plan of 1 to max_seasons season options that fits, each once, seasons in sowing order."""
    opts = options(lib, crops, positions)
    plans, seen = [], set()
    for k in range(1, max_seasons + 1):
        for combo in combinations(opts, k):
            if k > 1 and not fits(list(combo), lib):
                continue
            specs = ordered(list(combo), lib)
            pid = plan_id(specs)
            if pid not in seen:
                seen.add(pid)
                plans.append(specs)
    return plans


def plan_dates(specs, lib, start, end):
    """[(crop, 'YYYY-MM-DD' sowing day)] for every season of the plan lying wholly inside [start, end], in order."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    for year in range(start.year - 1, end.year + 1):
        for sp in specs:
            s, e = season_in_year(sp, lib, year)
            if s >= start and e <= end:
                out.append((sp["crop"], s))
    out.sort(key=lambda x: x[1])
    return [(c, str(s.date())) for c, s in out]
