"""Probe fusion (CLAUDE.md "Probe fusion", build step 10): a scalar Kalman update of the twin's root-zone wetness with a
probe reading, and the numbers it needs. Pure functions; rules in config/rules.yaml probe.kalman (committed before the
first run). Units: wetness in percent (0 = wilting point, 100 = field capacity), variances in percent squared.

    predict:  P = P + Q x days                         (never above `cap`)
    update:   K = P / (P + R);  x = x + K (z - x);  P = (1 - K) P
    sure   =  clamp(1 - sqrt(P) / sqrt(P0), 0, 1)

Where the numbers come from (rules.yaml probe.kalman):
- P0: what the calendar alone tells, the across-year variance of the twin's wetness around this day of year (p0_var).
- prior_var = P0 x (1 - r^2), r the correlation of the daily anomalies of the twin's wetness and SMAP L4 root-zone soil
  moisture (prior_from_smap); 1 - r^2 is the twin's anomaly variance that SMAP leaves unexplained, an upper bound on the
  twin's error if SMAP's errors are independent (so sure_prior is a lower bound). SMAP L4 is itself a model, at 9 km.
- Q = prior_var x (1 - phi^2), phi the lag-1 autocorrelation of the twin-minus-SMAP residual (kalman_numbers).
- R comes from the owner's repeat cups (robot/calibrate.py).
- One session is one measurement (fuse_session): lines 2 s apart from one insertion share their error, so each line
  updates from the twin's prior with the median of the session's last readings, never stacked.
- After the as-of day the prior ages: P = min(prior_var + Q x days, P0) (aged_prior_var).

The twin's state on its as-of day (the predict step's x): plan_through() lists every sowing up to that day, the crop in
the ground included, and state_on_last_day() reads the state from twin/season.simulate's daily table.
"""
import math

import numpy as np
import pandas as pd

from pipeline.plans.generate import season_in_year
from pipeline.twin import soil_water as sw


# ---------- the filter ----------

def _check_var(v, name):
    if not np.isfinite(v) or v < 0:
        raise ValueError(f"{name} must be a variance (finite, 0 or more), not {v}")


def predict(p_var, q_var_per_day, days=1.0, cap=None):
    """P + Q x days, never above cap (when given)."""
    _check_var(p_var, "P")
    _check_var(q_var_per_day, "Q")
    if days < 0:
        raise ValueError(f"days must be 0 or more, not {days}")
    p = p_var + q_var_per_day * days
    return min(p, cap) if cap is not None else p


def update(x, p_var, z, r_var):
    """(x, P, K) after one reading z with error variance R."""
    _check_var(p_var, "P")
    _check_var(r_var, "R")
    if p_var + r_var <= 0:
        raise ValueError("P + R must be above 0 (both zero would mean two perfect, different numbers)")
    k = p_var / (p_var + r_var)
    return x + k * (z - x), (1.0 - k) * p_var, k


def sure(p_var, p0_var):
    """clamp(1 - sqrt(P) / sqrt(P0), 0, 1): 0 = no better than the calendar, 1 = certain."""
    _check_var(p_var, "P")
    if not np.isfinite(p0_var) or p0_var <= 0:
        raise ValueError(f"P0 must be above 0, not {p0_var}")
    return float(min(1.0, max(0.0, 1.0 - math.sqrt(p_var) / math.sqrt(p0_var))))


def aged_prior_var(prior_var, q_var_per_day, p0_var, days):
    """rules.yaml probe.kalman.age_after_as_of: the twin's variance `days` whole days after its as-of day."""
    if days < 0:
        raise ValueError(f"the reading is {-days} day(s) before the twin's as-of day: refresh or check the clock")
    return predict(prior_var, q_var_per_day, days=days, cap=max(p0_var, prior_var))


def fuse_session(prior_x, prior_var, p0_var, z_values, r_var, lo=0.0, hi=100.0):
    """One session = one measurement (rules.yaml probe.kalman.one_session_one_measurement): z = the median of z_values
    (the caller passes the session's last readings, converted to wetness), set to lo..hi for the update
    (z_outside_bucket), and the section updated once from the twin's prior."""
    z = float(np.median(np.asarray(z_values, dtype=float)))
    z_used = min(hi, max(lo, z))
    x, p, k = update(prior_x, prior_var, z_used, r_var)
    return {"z": z, "z_used": z_used, "z_limited": z_used != z, "k": k, "wetness": x, "var": p,
            "sure": sure(p, p0_var), "sure_before": sure(prior_var, p0_var)}


# ---------- P0, anomalies, the SMAP comparison ----------

def doy365(dates):
    """Day of a 365-day year: in a leap year the days after 28 February move back one (29 February shares 1 March's)."""
    d = pd.DatetimeIndex(dates)
    return d.dayofyear.to_numpy() - (d.is_leap_year & (d.month > 2)).astype(int)


def _circular_window_sum(per_day, half_window):
    """per_day: 365 values (index 0 = day 1); sum over the days within half_window either side, around the year."""
    n = len(per_day)
    out = np.zeros(n)
    for k in range(-half_window, half_window + 1):
        out += np.roll(per_day, k)
    return out


def anomalies(series, half_window_days):
    """Each day's value minus the series' own mean over the days within half_window_days either side of its calendar
    day (all years in the series)."""
    s = pd.Series(series).dropna()
    doy = doy365(s.index)
    sums, counts = np.zeros(365), np.zeros(365)
    np.add.at(sums, doy - 1, s.to_numpy(dtype=float))
    np.add.at(counts, doy - 1, 1.0)
    clim = _circular_window_sum(sums, half_window_days) / _circular_window_sum(counts, half_window_days)
    return pd.Series(s.to_numpy(dtype=float) - clim[doy - 1], index=s.index)


def p0_var(series, target_date, years, half_window_days):
    """rules.yaml probe.kalman.p0: the mean over the days within half_window_days of target_date's calendar day of the
    sample variance (n - 1), across `years` (first, last), of the series on that day."""
    t = pd.Timestamp(target_date)
    month, day = t.month, (28 if (t.month, t.day) == (2, 29) else t.day)
    s = pd.Series(series)
    variances = []
    for k in range(-half_window_days, half_window_days + 1):
        vals = []
        for y in range(int(years[0]), int(years[1]) + 1):
            d = pd.Timestamp(year=y, month=month, day=day) + pd.Timedelta(k, unit="D")
            if d not in s.index or not np.isfinite(s[d]):
                raise ValueError(f"no twin wetness on {d.date()}: P0 needs every year of {years[0]}-{years[1]}")
            vals.append(float(s[d]))
        variances.append(float(np.var(vals, ddof=1)))
    return float(np.mean(variances))


def smap_fit(a_t, a_s):
    """r, rho = 1 - r^2, k (least-squares slope of the twin's anomaly on SMAP's) and phi (lag-1 autocorrelation of the
    residual) for two aligned anomaly arrays."""
    t, s = np.asarray(a_t, dtype=float), np.asarray(a_s, dtype=float)
    if len(t) != len(s) or len(t) < 3:
        raise ValueError("two aligned anomaly series of at least 3 days are needed")
    dt, ds = t - t.mean(), s - s.mean()
    sxx, syy, sxy = float(ds @ ds), float(dt @ dt), float(dt @ ds)
    if sxx <= 0 or syy <= 0:
        raise ValueError("an anomaly series does not vary: no correlation")
    r, k = sxy / math.sqrt(sxx * syy), sxy / sxx
    d = dt - k * ds
    dd = float(d @ d)
    phi = float(d[:-1] @ d[1:]) / dd if dd > 1e-12 * syy else None
    return {"r": r, "rho": dd / syy, "k": k, "phi": phi}


def prior_from_smap(twin, smap, half_window_days, near=None):
    """rules.yaml probe.kalman.prior: align the twin's daily wetness and SMAP's daily soil moisture on the days both
    have, take each one's anomalies over those days, and fit (smap_fit). With `near` (a date), the same fit over the
    days within half_window_days of its calendar day is added (reported, not used)."""
    j = pd.concat([pd.Series(twin, dtype=float), pd.Series(smap, dtype=float)], axis=1, join="inner").dropna()
    if len(j) < 365:
        raise ValueError(f"only {len(j)} days shared with SMAP: too few for the prior")
    a_t, a_s = anomalies(j.iloc[:, 0], half_window_days), anomalies(j.iloc[:, 1], half_window_days)
    out = {"n_days": int(len(j)), "first": str(j.index.min().date()), "last": str(j.index.max().date()),
           **smap_fit(a_t.to_numpy(), a_s.to_numpy())}
    if near is not None:
        t = doy365([pd.Timestamp(near)])[0]
        dist = np.abs(doy365(j.index) - t)
        sel = np.minimum(dist, 365 - dist) <= half_window_days
        f = smap_fit(a_t.to_numpy()[sel], a_s.to_numpy()[sel])
        out["near_as_of"] = {"n_days": int(sel.sum()), "r": f["r"], "rho": f["rho"]}
    return out


def kalman_numbers(p0, fit):
    """P0 and the SMAP fit -> prior_var, sure_prior and Q (rules.yaml probe.kalman.prior and .q)."""
    prior = p0 * fit["rho"]
    phi = fit["phi"] if fit["phi"] is not None else 1.0
    return {"p0_var": p0, "prior_var": prior, "sure_prior": sure(prior, p0), "q_var_per_day": prior * (1.0 - phi ** 2)}


# ---------- the twin's state on its as-of day ----------

def plan_through(specs, lib, start, end):
    """[(crop, 'YYYY-MM-DD')] for every season of the plan sown inside [start, end], the one still in the ground on
    `end` included (generate.plan_dates keeps whole seasons only); twin/season.simulate runs it to the record's end and
    marks it complete False."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    for year in range(start.year - 1, end.year + 1):
        for sp in specs:
            s, _ = season_in_year(sp, lib, year)
            if start <= s <= end:
                out.append((sp["crop"], s))
    out.sort(key=lambda x: x[1])
    return [(c, str(s.date())) for c, s in out]


def state_on_last_day(daily, plan=None):
    """The state at the end of the last day of twin/season.simulate's daily table: crop (or 'bare'), its sowing day and
    day of season, Dr, TAW, RAW (that day's p x TAW), Ks at the end of the day (eq. 84 from that day's Dr) and wetness
    100 x (1 - Dr/TAW). With `plan`, the sowing day is the plan's; otherwise the start of the last run of the crop."""
    d = daily.reset_index(drop=True)
    last = d.iloc[-1]
    date = pd.Timestamp(last["date"])
    crop = last["crop"] if isinstance(last["crop"], str) and last["crop"] else None
    dr, taw, raw = float(last["dr_mm"]), float(last["taw_mm"]), float(last["raw_mm"])
    sown = None
    if crop and plan:
        sown = max(pd.Timestamp(s) for c, s in plan if c == crop and pd.Timestamp(s) <= date)
    elif crop:
        i = len(d) - 1
        while i > 0 and d.loc[i - 1, "crop"] == crop and d.loc[i - 1, "segment"] == last["segment"]:
            i -= 1
        sown = pd.Timestamp(d.loc[i, "date"])
    return {"date": str(date.date()), "crop": crop or "bare", "crop_sown": str(sown.date()) if sown is not None else None,
            "crop_day": int((date - sown).days) + 1 if sown is not None else None,
            "dr_mm": dr, "taw_mm": taw, "raw_mm": raw, "ks": sw.ks(dr, taw, raw), "wetness_pct": 100.0 * (1.0 - dr / taw)}
