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


SOW_POSITIONS = {"start": 0.0, "middle": 0.5, "end": 1.0}


def sow_date(calendar, year, position="middle"):
    """A day in the default sowing window (rules.yaml crop_calendar), in `year` (window may cross 1 Jan). The
    middle is the rule for the current plan; step 7's generator may also use the start or end (owner's batch
    decisions item 10, 2026-11-12)."""
    import pandas as pd

    if position not in SOW_POSITIONS:
        raise ValueError(f"sowing position '{position}' is not one of {list(SOW_POSITIONS)}")
    w = calendar["windows"][calendar["default"]]
    a = pd.Timestamp(f"{year}-{w['sow']}")
    b = pd.Timestamp(f"{year}-{w['sow_end']}")
    if b < a:
        b = pd.Timestamp(f"{year + 1}-{w['sow_end']}")
    return (a + (b - a) * SOW_POSITIONS[position]).normalize()


# FAO-56 Chapter 6, eqs. 62, 63 and 65 (REVIEW_NOTES M7). Table 12 Kc mid and Kc end "represent those for a
# sub-humid climate with an average daytime minimum relative humidity (RHmin) of about 45%" and "calm to moderate
# wind speeds averaging 2 m/s". Limits as printed: 1 <= u2 <= 6 m/s, 20 <= RHmin <= 80 %, 0.1 <= h <= 10 m, and
# "The limits expressed for parameters u2, RHmin and h should be observed": an input outside them is held at the
# nearest limit (our reading; FAO-56 gives no clipping rule). Eq. 65 "is only applied when the tabulated values
# for Kc end exceed 0.45". Values and sources: config/rules.yaml kc_climate.
KC_CLIMATE_LIMITS = {"u2_ms": (1.0, 6.0), "rhmin_pct": (20.0, 80.0), "h_m": (0.1, 10.0)}
KC_END_MIN_TO_ADJUST = 0.45


def _held(x, key):
    lo, hi = KC_CLIMATE_LIMITS[key]
    return min(max(float(x), lo), hi)


def kc_climate_adjust(kc_tab, u2_ms, rhmin, h_m):
    """FAO-56 eq. 62 (and the same form, eq. 65): Kc (Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h / 3)^0.3.
    u2: mean daily wind at 2 m over the stage (m/s); rhmin: mean daily minimum RH over the stage (%); h: mean plant
    height in the stage (m). Example 27: maize 1.20, h 2 m, Taipei (1.3 m/s, 75%) -> 1.07."""
    u2, rh, h = _held(u2_ms, "u2_ms"), _held(rhmin, "rhmin_pct"), _held(h_m, "h_m")
    return float(kc_tab + (0.04 * (u2 - 2.0) - 0.004 * (rh - 45.0)) * (h / 3.0) ** 0.3)


def kc_end_climate_adjust(kc_end_tab, u2_ms, rhmin, h_m):
    """FAO-56 eq. 65: as eq. 62 with late-season u2 and RHmin, applied only when Kc end (Tab) exceeds 0.45
    (a crop left to senesce and dry in the field, Kc end < 0.45, needs no adjustment)."""
    if kc_end_tab <= KC_END_MIN_TO_ADJUST:
        return kc_end_tab
    return kc_climate_adjust(kc_end_tab, u2_ms, rhmin, h_m)


def rhmin_pct(ea_kpa, tmax_c):
    """Daily minimum relative humidity, FAO-56 eq. 63: e°(Tdew) / e°(Tmax) x 100, with e°(Tdew) = ea (eq. 14).
    The twin's ea is POWER's, capped at e°(corrected Tmin) (REVIEW_NOTES M6), so this is eq. 63 on our own
    humidity, not eq. 64's Tmin stand-in. Never above 100 %."""
    from pipeline.twin.et0 import e0_kpa

    rh = np.minimum(100.0, 100.0 * np.asarray(ea_kpa, dtype=float) / np.asarray(e0_kpa(tmax_c), dtype=float))
    return float(rh) if np.ndim(rh) == 0 else rh


def season_kc(kc, stages, h_m, u2_ms, rhmin):
    """Kc ini, mid and end for one season, Kc mid and end adjusted for the season's own climate: u2 and RHmin
    averaged over the mid-season days (eq. 62) and over the late-season days (eq. 65). u2_ms and rhmin hold one
    value per season day from sowing; a season cut short keeps the table value for any stage it never reaches."""
    ini, dev, mid, late = (stages[s] for s in STAGE_ORDER)
    u2, rh = np.asarray(u2_ms, dtype=float), np.asarray(rhmin, dtype=float)
    a, b, n = ini + dev, ini + dev + mid, len(u2)
    out = {"ini": kc["ini"], "mid": kc["mid"], "end": kc["end"],
           "u2_mid_ms": None, "rhmin_mid_pct": None, "u2_late_ms": None, "rhmin_late_pct": None}
    if n > a:
        out["u2_mid_ms"], out["rhmin_mid_pct"] = float(u2[a:b].mean()), float(rh[a:b].mean())
        out["mid"] = kc_climate_adjust(kc["mid"], out["u2_mid_ms"], out["rhmin_mid_pct"], h_m)
    if n > b:
        out["u2_late_ms"], out["rhmin_late_pct"] = float(u2[b:].mean()), float(rh[b:].mean())
        out["end"] = kc_end_climate_adjust(kc["end"], out["u2_late_ms"], out["rhmin_late_pct"], h_m)
    return out
