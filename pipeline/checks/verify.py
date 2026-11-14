"""Verification yardsticks (rules.yaml verification): the share of test cases within tolerance, its 95% Wilson
interval, and the three statuses VERIFIED, ESTIMATE and NOT YET VERIFIABLE. Pure functions; the runner is
scripts/run_verification.py."""
from math import sqrt

Z95 = 1.959963984540054


def wilson(k, n, z=Z95):
    """95% Wilson score interval for k of n (Newcombe 1998 method 3; Brown, Cai & DasGupta 2001)."""
    if n <= 0:
        return None
    p, z2 = k / n, z * z
    d = 1 + z2 / n
    c, h = (p + z2 / (2 * n)) / d, z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def grade(k, n, independent, rules):
    """A consistency check only (or a projection): ESTIMATE. No data or too few cases: NOT YET VERIFIABLE. Else the point
    estimate decides."""
    if not independent:
        return "ESTIMATE"
    if n < rules["n_min"]:
        return "NOT YET VERIFIABLE"
    return "VERIFIED" if k / n >= rules["threshold"] else "ESTIMATE"


def score(passes, independent, rules):
    k, n = sum(map(bool, passes)), len(passes)
    return {"k": k, "n": n, "share": round(k / n, 4) if n else None, "ci95": wilson(k, n),
            "status": grade(k, n, independent, rules)}


def within(ours, ref, rel=None, abs_=None):
    """One bool per pair with a reference: |ours - ref| <= rel * |ref|, or <= abs_."""
    out = []
    for o, r in zip(ours, ref):
        if r is None or o is None:
            continue
        lim = rel * abs(r) if rel is not None else abs_
        out.append(abs(o - r) <= lim + 1e-9)
    return out


def events_skill(flags, events, listed, controls):
    """flags {year: (kind, season or None = both)}; events [(year, kind, season)] the valley's sourced events; listed
    {(year, kind)} every sourced event, any place; controls [(year, kind, season)] seasons DHM's gauges show were not
    that event. Hits: one bool per valley event. False alarms: one bool per flagged season (a both-season drought is
    two), True when no listed event backs it or a control contradicts it."""
    def covers(flag, season):
        return flag is not None and (flag[1] is None or season is None or flag[1] == season)
    hits = [flags.get(y) is not None and flags[y][0] == kind and covers(flags[y], s) for y, kind, s in events]
    alarms = []
    for y, (kind, season) in sorted(flags.items()):
        for s in ([season] if season or kind == "flood" else ["winter", "monsoon"]):
            alarms.append((y, kind) not in listed or (y, kind, s) in controls)
    return hits, alarms


def beats(plan, current):
    """One bool per run both hold: the plan's harvest above the current plan's."""
    return [plan[k] > current[k] for k in plan if k in current]


def year_matches(harvest, worst, best):
    """A worst year matches when its harvest ranks in the lowest third of the years, a best year in the highest third
    (average ranks for ties). One bool per year named, worst first."""
    vals = sorted(harvest.values())
    n = len(vals)

    def rank(y):
        h = harvest.get(y)
        if h is None:
            return None
        below, equal = sum(x < h for x in vals), sum(x == h for x in vals)
        return below + (equal + 1) / 2
    third = n / 3
    out = [r is not None and r <= third for r in map(rank, worst)]
    return out + [r is not None and r > n - third for r in map(rank, best)]


def same_direction(a, b):
    """First differences over consecutive years both hold; one bool per year where both change."""
    ys = sorted(set(a) & set(b))
    out = []
    for y0, y1 in zip(ys, ys[1:]):
        if y1 != y0 + 1:
            continue
        da, db = a[y1] - a[y0], b[y1] - b[y0]
        if da and db:
            out.append((da > 0) == (db > 0))
    return out
