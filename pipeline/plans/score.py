"""Plan scores and the choice of plans to show (CLAUDE.md "Plans" steps 3-4, build step 7). Pure functions.

Scores run 0 to 100, higher is better for the farmer (contract: harvest, water, cover, soil_kept):
- harvest: mean yearly harvest (% of potential) over complete years, in the field's own water case; stability:
  the 10th-percentile year (CLAUDE.md), used to choose plans and in the words, not a contract score.
- water: the share of the crop water use (ETc) that rain covers, from the watered case (1 - irrigation / ETc),
  with irrigation counted `strict` times when the regional groundwater is falling (D7; rules.yaml plans).
- cover: the share of the year inside a crop season.
- soil_kept: 100 x (1 - E_plan / E_bare), E = sum over days of erosive rain P^beta x the day's cover factor C
  (RUSLE: K, LS and P are the same field and cancel; rules.yaml erosion). A comparison between plans, never a
  tonnage (CLAUDE.md "Erosion").
Pest-cycle break (no crop family twice in a row, the next year included) and nitrogen (a legume) are flags.
"""
from collections import Counter

import numpy as np
import pandas as pd


def complete(years, crops):
    want = Counter(crops)
    return [y for y in years if Counter(y["crops"]) == want]


def harvest_metrics(years):
    h = np.array([y["harvest"] for y in years], float)
    return {"harvest": float(h.mean()), "stability": float(np.percentile(h, 10)),
            "dry_days": float(np.mean([y["dry_days"] for y in years]))}


def water_score(irrigation_mm, etc_mm, strict):
    share_irrigated = irrigation_mm / etc_mm if etc_mm > 0 else 1.0
    return float(round(100 * min(1.0, max(0.0, 1 - strict * share_irrigated)), 1))


def cover_score(cover_days):
    return float(min(100.0, 100 * cover_days / 365))


def _families(crops, lib):
    return [lib[c]["family"] for c in crops]


def pest_break(crops, lib):
    """True when no two consecutive seasons share a family, counting the first season of the next year."""
    f = _families(crops, lib)
    return len(f) > 1 and all(a != b for a, b in zip(f, f[1:] + f[:1]))


def has_legume(crops, lib):
    return any(lib[c].get("legume") for c in crops)


def daily_c(days, seasons, c_by_crop, c_bare):
    """Cover factor per day: the crop's C inside each (crop, sow, end) season, c_bare elsewhere."""
    days = pd.DatetimeIndex(days)
    c = np.full(len(days), float(c_bare))
    for crop, s, e in seasons:
        c[(days >= pd.Timestamp(s)) & (days <= pd.Timestamp(e))] = c_by_crop[crop]
    return c


def month_weight(months, amplitude):
    """Seasonal multiplier of the daily erosivity model, 1 + amplitude x cos(pi j / 6 - 7 pi / 6), j = month 1-12
    (Xie et al., in Yin et al. 2015, Table 3): largest in July, smallest in January."""
    j = np.asarray(months, float)
    return 1 + amplitude * np.cos(np.pi * j / 6 - 7 * np.pi / 6)


def erosion_index(rain_mm, c, threshold_mm, beta, weight=None):
    r = np.asarray(rain_mm, float)
    w = 1.0 if weight is None else np.asarray(weight, float)
    return float(np.sum(np.where(r >= threshold_mm, r ** beta, 0.0) * w * np.asarray(c, float)))


def soil_kept_score(e_plan, e_bare):
    return float(round(100 * max(0.0, 1 - e_plan / e_bare), 1)) if e_bare > 0 else 0.0


def pareto(rows, keys):
    """Rows that no other row matches or beats on every key while beating on one (ties are all kept)."""
    out = []
    for r in rows:
        dominated = any(all(o[k] >= r[k] for k in keys) and any(o[k] > r[k] for k in keys) for o in rows if o is not r)
        if not dominated:
            out.append(r)
    return out


def pick_cover_gap(rows, current_id):
    """The highest cover among plans that keep at least the current harvest (ties: higher harvest); if none
    keeps it, the highest cover overall."""
    cur = next(r for r in rows if r["id"] == current_id)
    keep = [r for r in rows if r["id"] != current_id and r["harvest"] >= cur["harvest"]]
    pool = keep or [r for r in rows if r["id"] != current_id]
    return max(pool, key=lambda r: (r["cover"], r["harvest"]))


def same_crops(a, b):
    """True when two plans grow the same crops (the same rotation, whatever the sowing dates)."""
    return sorted(a["crops"]) == sorted(b["crops"])


def pick_safest(rows, exclude, min_cover):
    """'Safest in bad years' (owner's decision 5, 2026-11-13): the best 10th-percentile year (ties: higher mean
    harvest) among the plans keeping at least min_cover (today's cover), other than those excluded."""
    pool = [r for r in rows if r["id"] not in exclude and r["cover"] >= min_cover]
    if not pool:
        raise ValueError(f"NOT READY: no third rotation (other crops than {sorted(exclude)}) keeps at least {min_cover} cover")
    return max(pool, key=lambda r: (r["stability"], r["harvest"]))


def choose_three(rows, current_id, keys, must_include):
    """The plans to show (CLAUDE.md 'Plans' step 4; owner's decisions 4 and 5, 2026-11-13): only plans growing
    `must_include` (rice, in the monsoon) are suggested; among them the Pareto set on `keys` plus the current plan;
    cover the gap = pick_cover_gap; safest = pick_safest with today's cover, excluding the current and the
    cover-the-gap plan, and no plan growing the same crops as either: three different rotations (CLAUDE.md).
    The cover-the-gap plan also grows other crops than the current plan."""
    eligible = [r for r in rows if must_include in r["crops"] or r["id"] == current_id]
    front = pareto(eligible, keys)
    ids = {r["id"] for r in front}
    pool = front + [r for r in eligible if r["id"] == current_id and r["id"] not in ids]
    cur = next(r for r in pool if r["id"] == current_id)
    gap = pick_cover_gap([r for r in pool if r["id"] == current_id or not same_crops(r, cur)], current_id)
    # three different rotations (CLAUDE.md): no plan with the same crops as the current or the cover-the-gap plan
    exclude = {r["id"] for r in eligible if same_crops(r, cur) or same_crops(r, gap)}
    src, min_cover = "Pareto set", cur["cover"]
    if not [r for r in front if r["id"] not in exclude and r["cover"] >= cur["cover"]]:
        src = "all rice plans"                     # no other Pareto plan keeps today's cover: widen to every rice plan
        if not [r for r in eligible if r["id"] not in exclude and r["cover"] >= cur["cover"]]:
            src, min_cover = "all rice plans, any cover", float("-inf")   # rules.yaml plans.third_plan_fallback
    safe = pick_safest(front if src == "Pareto set" else eligible, exclude=exclude, min_cover=min_cover)
    return {"pareto": sorted(ids), "eligible": len(eligible), "current": current_id, "cover_gap": gap["id"],
            "safest": safe["id"], "safest_from": src}
