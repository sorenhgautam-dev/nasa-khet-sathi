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


def _slot(month):
    """rules.yaml rotation_guess slots (pipeline/diary/guess.py SLOTS): monsoon June-November, winter December-May."""
    return "monsoon" if 6 <= month <= 11 else "winter"


def season_date_passes(farmer, seasons, ini_days, tol_days):
    """rules.yaml pulse.farmer_scoring. farmer: [(crop, year, planted, harvested)] (datetime.date; year = the harvest
    year); seasons: the Pulse's [{year, slot, source, greenup, end}] (ISO dates); ini_days: {crop: initial stage, days}.
    Two bools per row, planted then harvested: within tol_days of the matched HLS season's planting (green-up minus the
    crop's initial stage) and end. The slot is the middle day's; no season of that slot and year fails both."""
    from datetime import date, timedelta
    out = []
    for crop, year, planted, harvested in farmer:
        mid = planted + (harvested - planted) / 2
        s = next((x for x in seasons if x["source"] == "hls" and x["slot"] == _slot(mid.month) and x["year"] == year), None)
        ours = (None, None) if s is None else (date.fromisoformat(s["greenup"]) - timedelta(days=ini_days[crop]),
                                               date.fromisoformat(s["end"]))
        out += [o is not None and abs((o - t).days) <= tol_days for o, t in zip(ours, (planted, harvested))]
    return out


FROST_RANK = {"none": 0, "risk": 1, "high": 2}


def frost_order_passes(words, normals, frost_c, risk_c):
    """rules.yaml verification.outputs.frost_month_words: one bool per month. A month fails when a month with a colder
    normal night temperature has a milder frost word, or a warmer one a frostier word (equal normals are not ordered),
    or when its normal is below risk_c and its word is 'none', or below frost_c and its word is not 'high' (a month's
    coldest night is at most about its mean night)."""
    r = [FROST_RANK[w] for w in words]
    out = []
    for i, (ni, ri) in enumerate(zip(normals, r)):
        order = all(not ((nj < ni and rj < ri) or (nj > ni and rj > ri)) for j, (nj, rj) in enumerate(zip(normals, r)) if j != i)
        bound = not (ni < risk_c and ri == 0) and not (ni < frost_c and ri != 2)
        out.append(order and bound)
    return out


def residual_sign_matches(ours, ref):
    """rules.yaml verification.outputs.harvest_years.district: over the years both hold, each series' residual from its
    own least-squares straight line on the year; one bool per year where neither residual is zero: the same sign."""
    import numpy as np
    ys = sorted(set(ours) & set(ref))
    if len(ys) < 3:
        return []
    x = np.asarray(ys, float)

    def resid(d):
        y = np.asarray([d[k] for k in ys], float)
        r = y - np.polyval(np.polyfit(x, y, 1), x)
        r[np.abs(r) < 1e-9 * (1 + np.abs(y).max())] = 0.0
        return np.sign(r)
    a, b = resid(ours), resid(ref)
    return [bool(p == q) for p, q in zip(a, b) if p and q]


def fiscal_year(day, start_mmdd):
    """Nepal's fiscal year holding a date ('2015/16' runs from start_mmdd 2015 to the day before it in 2016)."""
    m, d = map(int, start_mmdd.split("-"))
    a = day.year if (day.month, day.day) >= (m, d) else day.year - 1
    return f"{a}/{(a + 1) % 100:02d}"


def shift_kind(years, days, alpha):
    """rules.yaml verification.outputs.monsoon_shift, a second implementation: the Mann-Kendall p as Kendall's tau of day
    on year (scipy), the 95% range by Theil-Sen (scipy, at 1 - alpha). 'no clear change' when the range holds 0 or
    p >= alpha, else 'earlier' or 'later'."""
    from scipy.stats import kendalltau, theilslopes
    p = kendalltau(years, days).pvalue
    slope, _, low, high = theilslopes(days, years, alpha=1 - alpha)
    if (low > 0 or high < 0) and p < alpha:
        return "earlier" if slope < 0 else "later"
    return "no clear change"
