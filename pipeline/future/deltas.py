"""Delta change for the 2040 outlook (build step 9; rules.yaml future). Pure functions.

model_change(): per model and scenario, the monthly change at the field's NEX-GDDP-CMIP6 cell between the historical
period (1995-2014) and the future period (2026-2040): Tmax and Tmin as differences of monthly means (deg C), rain as a
ratio of the mean daily rain pooled over the window_months calendar months centred on each month (3: December, January
and February for January). Model days in each model's own calendar (360_day, noleap, standard) are only averaged, never
matched between calendars.

apply_change(): the observed 2001-2025 weather (data/clean/<field>/weather.parquet) with those changes: tasmax's change
added to tmax_c and tmax_c_power, tasmin's to tmin_c, tmin_frost_c and tmin_c_power, rain_mm and rain_uncorrected_mm times
the month's ratio. Humidity (rh_pct), wind and sunshine stay as observed. ea_kpa and ET0 are rebuilt exactly as
pipeline/fetch/weather.py builds them, relative humidity held (rules.yaml future.humidity): ea = POWER's RH2M with
POWER's own (shifted) temperatures (FAO-56 eq. 19), capped at e0 of the shifted corrected Tmin.
"""
import numpy as np
import pandas as pd

from pipeline.fetch import guards as g
from pipeline.twin import inputs
from pipeline.twin.et0 import et0_mm

MONTHS = range(1, 13)
KEYS = ("dtmax_c", "dtmin_c", "rain_ratio")


def window(month, n):
    """The n calendar months centred on `month` (n odd), wrapping over the year's end."""
    if n % 2 != 1:
        raise ValueError("the rain window needs an odd number of months")
    h = n // 2
    return [(month - 1 + k) % 12 + 1 for k in range(-h, h + 1)]


def _period(daily, model, experiment, years):
    d = daily[(daily["model"] == model) & (daily["experiment"] == experiment)
              & daily["year"].between(years[0], years[1])]
    have = set(zip(d["year"], d["month"]))
    lacking = [(y, m) for y in range(years[0], years[1] + 1) for m in MONTHS if (y, m) not in have]
    if lacking:
        raise ValueError(f"{model} {experiment}: no model days for {len(lacking)} month(s) of {years}, e.g. {lacking[:3]}")
    cols = ["pr_mm", "tasmax_c", "tasmin_c"]
    if d[cols].isna().any().any():
        raise ValueError(f"{model} {experiment}: missing values in {years}")
    return d


def model_change(daily, model, scenario, periods, window_months):
    """{'dtmax_c': {month: deg C}, 'dtmin_c': {...}, 'rain_ratio': {...}, 'annual': {...}} for one model and scenario.
    daily: model, experiment, year, month, day, pr_mm, tasmax_c, tasmin_c (pipeline/fetch/nexgddp.py)."""
    h = _period(daily, model, "historical", periods["historical"])
    f = _period(daily, model, scenario, periods["future"])
    hm, fm = h.groupby("month"), f.groupby("month")
    dtx = (fm["tasmax_c"].mean() - hm["tasmax_c"].mean())
    dtn = (fm["tasmin_c"].mean() - hm["tasmin_c"].mean())
    ratio = {}
    for m in MONTHS:
        w = window(m, window_months)
        ph, pf = h.loc[h["month"].isin(w), "pr_mm"].mean(), f.loc[f["month"].isin(w), "pr_mm"].mean()
        if not ph > 0:
            raise ValueError(f"{model}: no historical rain in months {w}, so no rain ratio for month {m}")
        ratio[m] = float(pf / ph)
    tas_h, tas_f = (h["tasmax_c"] + h["tasmin_c"]) / 2, (f["tasmax_c"] + f["tasmin_c"]) / 2
    annual = {"dtmax_c": float(f["tasmax_c"].mean() - h["tasmax_c"].mean()),
              "dtmin_c": float(f["tasmin_c"].mean() - h["tasmin_c"].mean()),
              "dtas_c": float(tas_f.mean() - tas_h.mean()),
              "rain_change_pct": float(100 * (f["pr_mm"].mean() / h["pr_mm"].mean() - 1)),
              "rain_hist_mm_per_day": float(h["pr_mm"].mean()), "calendar": str(h["calendar"].iloc[0])
              if "calendar" in h else None}
    return {"dtmax_c": {m: float(dtx[m]) for m in MONTHS}, "dtmin_c": {m: float(dtn[m]) for m in MONTHS},
            "rain_ratio": ratio, "annual": annual}


def uniform_change(warming_c, rain_factor):
    """The slider grid's change (CLAUDE.md 'Slider scenarios'): the same warming for Tmax and Tmin and the same rain
    factor in every month."""
    return {"dtmax_c": {m: float(warming_c) for m in MONTHS}, "dtmin_c": {m: float(warming_c) for m in MONTHS},
            "rain_ratio": {m: float(rain_factor) for m in MONTHS}}


def _by_month(dates, table, key):
    if sorted(int(m) for m in table) != list(MONTHS):
        raise ValueError(f"{key}: a change is needed for every month 1-12, got {sorted(table)}")
    t = {int(m): float(v) for m, v in table.items()}
    if not all(np.isfinite(v) for v in t.values()):
        raise ValueError(f"{key}: a change is not a finite number")
    return pd.DatetimeIndex(dates).month.map(t).to_numpy(float)


def apply_change(weather, change, elev_m, lat_deg):
    """The weather table with the change applied and ea_kpa, ea_capped, et0_mm and et0_rh_held_mm rebuilt as in
    pipeline/fetch/weather.py (relative humidity held). Fails loudly (golden rule 12c) if a shifted Tmin lies above the
    shifted Tmax or a temperature or rain value leaves its range; nothing is clipped."""
    for k in KEYS:
        if k not in change:
            raise ValueError(f"change lacks '{k}'")
    w = weather.copy()
    dx, dn, rr = (_by_month(w["date"], change[k], k) for k in KEYS)
    for c in ("tmax_c", "tmax_c_power"):
        w[c] = w[c].to_numpy(float) + dx
    for c in ("tmin_c", "tmin_frost_c", "tmin_c_power"):
        w[c] = w[c].to_numpy(float) + dn
    for c in ("rain_mm", "rain_uncorrected_mm"):
        if c in w:
            w[c] = w[c].to_numpy(float) * rr
            g.assert_in_range(w[c].to_numpy(), "rain_mm", f"{c} (changed)")
    g.check_table(w, {"tmax_c": "temp_c", "tmin_c": "temp_c", "tmin_frost_c": "temp_c"})
    for c in ("tmin_c", "tmin_frost_c"):
        bad = (w[c] > w["tmax_c"]).to_numpy()
        if bad.any():
            raise g.DataGuardError(f"{c} above tmax_c on {int(bad.sum())} day(s) after the change (first "
                                   f"{pd.Timestamp(w.loc[bad, 'date'].iloc[0]).date()}); not clipped")
    ea, capped = inputs.ea_held_from_power_kpa(w["rh_pct"], w["tmax_c_power"], w["tmin_c_power"], w["tmin_c"])
    w["ea_kpa"], w["ea_capped"] = ea, capped
    args = (w["tmax_c"], w["tmin_c"], w["ws2m_ms"], w["rs_mj_m2_day"], elev_m, lat_deg, w["date"].dt.day_of_year)
    w["et0_mm"] = et0_mm(*args, ea=ea)
    w["et0_rh_held_mm"] = et0_mm(*args, rh_mean=w["rh_pct"])
    for c in ("et0_mm", "et0_rh_held_mm"):
        g.assert_nonnegative(w[c].to_numpy(), f"{c} (changed)")
    return w


def compare_published(summary, reference):
    """VALIDATION 4.7 (rules.yaml future.plausibility): our ensemble median of each annual change against a published
    range, per scenario: {scenario: {key: {ours, published, inside}}, all_inside}."""
    out, ok = {}, True
    for s, ref in reference.items():
        out[s] = {}
        for k, rng in ref.items():
            v = summary[s][f"annual_{k}"]["median"]
            inside = bool(rng[0] <= v <= rng[1])
            ok = ok and inside
            out[s][k] = {"ours": v, "published": list(rng), "inside": inside}
    out["all_inside"] = ok
    return out
