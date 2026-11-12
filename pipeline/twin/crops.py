"""Crop coefficient curve, FAO-56 eq. 66 (Allen et al. 1998, Chapter 6): Kc is flat in the initial and
mid-season stages and changes linearly through development and late season. Also the crop-library helpers
the twin and the plan generator (build step 7) share: which crops can be simulated, the stage-scaling
rule used in crops.json, and the day span a calendar window's own dates allow. Pure functions."""
import math

import numpy as np

STAGE_ORDER = ("ini", "dev", "mid", "late")
KC_KEYS = ("ini", "mid", "end")


def _positive_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def simulatable_crops(lib):
    """{name: params} for the crops the twin can run: not marked `simulate: false` in crops.json, and with
    all four stage lengths, Kc ini/mid/end, zr_m, p and ky present. Build step 7 draws plans only from these."""
    out = {}
    for name, c in lib.items():
        if c.get("simulate", True) is False:
            continue
        st, kc = c.get("stages_days") or {}, c.get("kc") or {}
        if not all(_positive_number(st.get(s)) for s in STAGE_ORDER):
            continue
        if not all(isinstance(kc.get(k), (int, float)) for k in KC_KEYS):
            continue
        if any(not _positive_number(c.get(k)) for k in ("zr_m", "p", "ky")):
            continue
        out[name] = c
    return out


def require_simulatable(lib, crops):
    """Raise ValueError, naming the crop and the reason, if any crop in `crops` cannot be simulated."""
    ok = simulatable_crops(lib)
    for crop in crops:
        if crop not in lib:
            raise ValueError(f"{crop} is not in the crop library (config/crops.json)")
        if crop not in ok:
            why = (lib[crop].get("sources") or {}).get("simulate") or \
                "its stage lengths, Kc, Zr, p or Ky are missing in crops.json"
            raise ValueError(f"{crop} cannot be simulated: {why}")


def scale_stages(stages, total_days):
    """FAO-56 stage lengths scaled in proportion to a local season of `total_days` days, rounded to whole
    days by largest remainder (ties go in stage order) so they add up exactly. The rule recorded in
    crops.json for every scaled crop (rice, wheat, maize, lentil, finger millet)."""
    total = sum(stages[s] for s in STAGE_ORDER)
    exact = {s: stages[s] * total_days / total for s in STAGE_ORDER}
    out = {s: int(math.floor(exact[s])) for s in STAGE_ORDER}
    short = int(total_days) - sum(out.values())
    for s in sorted(STAGE_ORDER, key=lambda k: -(exact[k] - out[k]))[:short]:   # sorted() is stable
        out[s] += 1
    return out


def window_day_span(window, ref_year=2017):
    """(fewest, most) days from sowing to harvest that a calendar window's own dates allow: earliest harvest
    minus latest sowing, and latest harvest minus earliest sowing. Dates are read in a non-leap year (2017
    sowing, 2018 harvest); a leap February adds one day."""
    import pandas as pd

    def on_or_after(md, t):
        d = pd.Timestamp(f"{t.year}-{md}")
        return d if d >= t else pd.Timestamp(f"{t.year + 1}-{md}")

    s0 = pd.Timestamp(f"{ref_year}-{window['sow']}")
    s1 = on_or_after(window["sow_end"], s0)
    h0 = on_or_after(window["harvest"], s0)
    h1 = on_or_after(window["harvest_end"], h0)
    return int((h0 - s1).days), int((h1 - s0).days)


def kc_on_day(day, stages, kc):
    """Kc on day `day` of the season (1 = first day). stages: days per stage; kc: ini, mid, end."""
    ini, dev, mid, late = (stages[s] for s in STAGE_ORDER)
    if day <= ini:
        return kc["ini"]
    if day <= ini + dev:
        return kc["ini"] + (day - ini) / dev * (kc["mid"] - kc["ini"])
    if day <= ini + dev + mid:
        return kc["mid"]
    return kc["mid"] + (day - ini - dev - mid) / late * (kc["end"] - kc["mid"])


def kc_curve(stages, kc):
    total = sum(stages[s] for s in STAGE_ORDER)
    return np.array([kc_on_day(d, stages, kc) for d in range(1, total + 1)])


def season_length(stages):
    return int(sum(stages[s] for s in STAGE_ORDER))


def sow_date(calendar, year):
    """Middle of the default sowing window (rules.yaml crop_calendar), in `year` (window may cross 1 Jan)."""
    import pandas as pd

    w = calendar["windows"][calendar["default"]]
    a = pd.Timestamp(f"{year}-{w['sow']}")
    b = pd.Timestamp(f"{year}-{w['sow_end']}")
    if b < a:
        b = pd.Timestamp(f"{year + 1}-{w['sow_end']}")
    return (a + (b - a) / 2).normalize()
