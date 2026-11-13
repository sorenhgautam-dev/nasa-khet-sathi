"""Rotation guess from the detected seasons (CLAUDE.md "Seasons and rotation guess", build step 6c). Pure functions.

NDVI shows green cover, not which crop. The guess compares each detected season's timing with each crop's calendar
in config/crops.json and the farmer confirms it on screen. For a crop window (sowing sow..sow_end, harvest
harvest..harvest_end, season length `days`):
- green-up: the detected start (20% up the rise) is compared with sowing + the initial stage (FAO-56: the initial
  stage runs from planting to about 10% ground cover);
- harvest: the detected end with the harvest window;
- length: end - start + 1 with the crop's days minus its initial stage.
Each is the number of days outside its window (0 inside); a season's distance to a crop is the sum, at the crop's
best window and anchor year. Per slot (monsoon: peak in June-November; winter: peak in December-May) the crop with
the smallest median distance over the years is the guess (rules.yaml rotation_guess, fixed before it was run).
"""
import numpy as np
import pandas as pd

SLOTS = {"monsoon": (6, 7, 8, 9, 10, 11), "winter": (12, 1, 2, 3, 4, 5)}


def distance_days(d, lo, hi):
    if lo <= d <= hi:
        return 0
    return int(min(abs((d - lo).days), abs((d - hi).days)))


def _on_or_after(mmdd, after):
    t = pd.Timestamp(f"{after.year}-{mmdd}")
    return t if t >= after else pd.Timestamp(f"{after.year + 1}-{mmdd}")


def season_fit(season, crop):
    """{'start', 'end', 'length', 'total'} days outside the crop's windows, at its best window and anchor year."""
    ini = int(crop["stages_days"]["ini"])
    s, e = season["start"], season["end"]
    length = int((e - s).days) + 1
    best = None
    for w in crop["calendar"]["windows"]:
        for year in (s.year - 1, s.year):
            sow_lo = pd.Timestamp(f"{year}-{w['sow']}")
            sow_hi = _on_or_after(w["sow_end"], sow_lo)
            harv_lo = _on_or_after(w["harvest"], sow_lo)
            harv_hi = _on_or_after(w["harvest_end"], harv_lo)
            days = [int(x) for x in w["days"]]
            d = {"start": distance_days(s, sow_lo + pd.Timedelta(ini, unit="D"), sow_hi + pd.Timedelta(ini, unit="D")),
                 "end": distance_days(e, harv_lo, harv_hi),
                 "length": 0 if min(days) - ini <= length <= max(days) - ini
                 else int(min(abs(length - (min(days) - ini)), abs(length - (max(days) - ini))))}
            d["total"] = d["start"] + d["end"] + d["length"]
            if best is None or d["total"] < best["total"]:
                best = d
    return best


def slot_of(season):
    m = season["peak"].month
    return next(k for k, months in SLOTS.items() if m in months)


def guess(seasons, lib, crops):
    """{'guess': [monsoon crop, winter crop] (or 'bare' for a slot without seasons), 'slots': per-slot fits}."""
    slots = {}
    for slot in SLOTS:
        ss = [s for s in seasons if slot_of(s) == slot]
        fit = {}
        for c in crops:
            totals = [season_fit(s, lib[c]) for s in ss]
            if totals:
                fit[c] = {"median_total": float(np.median([t["total"] for t in totals])),
                          "median_start": float(np.median([t["start"] for t in totals])),
                          "median_end": float(np.median([t["end"] for t in totals])),
                          "median_length": float(np.median([t["length"] for t in totals])),
                          "years": len(totals)}
        best = min(fit, key=lambda c: fit[c]["median_total"]) if fit else "bare"
        slots[slot] = {"seasons": len(ss), "fit": fit, "best": best}
    return {"guess": [slots["monsoon"]["best"], slots["winter"]["best"]], "slots": slots}
