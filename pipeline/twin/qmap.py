"""Empirical quantile mapping of POWER Tmin onto a nearby station, for cold nights (owner go, 2026-11-12).

A single monthly offset moves every night by the same amount, so it over-corrects the coldest nights
(Jan 2013: -4.2 C corrected vs -1.1 C reported). Quantile mapping moves each night according to where
it sits in POWER's distribution for that month. Fit per month, or per season (Dec-Feb, Mar-May, Jun-Sep,
Oct-Nov) when a month has too few shared days; beyond the fitted range the end-quantile difference is
kept (constant extrapolation). Method: empirical quantile mapping as in Gudmundsson et al. (2012) and
Themessl et al. (2011) (citations in CREDITS.md). Compared with the monthly offset on held-out years by
three numbers (mean absolute error, each January's coldest night, nights below 2 C) and the result is
reported (VALIDATION.md 3.14), but the comparison does not choose the method. Owner, step-4 review item 1
(2026-11-12): quantile mapping is used for frost only (`tmin_frost_c`) whatever the comparison says, and
the monthly offset stays for the twin's temperatures and ET0 (`tmin_c`). On the demo's held-out years
quantile mapping is worse on mean absolute error and better on the other two. Months with no model (too few
shared days even for the season) pass through uncorrected; weather.py reports them. Pure functions.
"""
import numpy as np
import pandas as pd

from pipeline.twin import bias


def _season_of(month, seasons):
    return next(name for name, months in seasons.items() if month in months)


def fit_qmap(shared, years, col, seasons, min_days, n_quantiles):
    d = shared[shared["year"].isin(years)]
    probs = np.linspace(0.01, 0.99, n_quantiles)
    models = {}
    for m in range(1, 13):
        sub, basis = d[d["month"] == m], "month"
        if len(sub) < min_days:
            name = _season_of(m, seasons)
            sub, basis = d[d["month"].isin(seasons[name])], f"season {name}"
        if len(sub) < min_days:
            models[m] = None
            continue
        pq = np.quantile(sub[f"{col}_power"], probs)
        sq = np.quantile(sub[f"{col}_station"], probs)
        pq_u, inv = np.unique(pq, return_inverse=True)                 # np.interp needs rising x
        sq_u = np.array([sq[inv == i].mean() for i in range(len(pq_u))])
        models[m] = {"basis": basis, "n": int(len(sub)), "power_q": pq_u.tolist(), "station_q": sq_u.tolist()}
    return models


def apply_qmap(df, col, models):
    out = df[col].to_numpy(dtype=float).copy()
    months = df["date"].dt.month.to_numpy()
    for m, mod in models.items():
        idx = months == m
        if mod is None or not idx.any():
            continue
        x, pq, sq = out[idx], np.asarray(mod["power_q"]), np.asarray(mod["station_q"])
        y = np.interp(x, pq, sq)
        lo, hi = x < pq[0], x > pq[-1]
        y[lo] = x[lo] + (sq[0] - pq[0])
        y[hi] = x[hi] + (sq[-1] - pq[-1])
        out[idx] = y
    return pd.Series(out, index=df.index)


def cold_night_scores(dates, station, corrected, frost_c):
    dates = pd.DatetimeIndex(dates)
    st, co = np.asarray(station, dtype=float), np.asarray(corrected, dtype=float)
    jan = dates.month == 1
    by_year = {}
    for y in sorted(set(dates[jan].year)):
        sel = jan & (dates.year == y)
        by_year[int(y)] = {"station": float(st[sel].min()), "corrected": float(co[sel].min())}
    errs = [abs(v["corrected"] - v["station"]) for v in by_year.values()]
    ns, nc = int((st < frost_c).sum()), int((co < frost_c).sum())
    return {"n": int(len(st)), "mae": float(np.abs(co - st).mean()),
            "jan_coldest_error": float(np.mean(errs)) if errs else None, "jan_coldest_by_year": by_year,
            "nights_below": {"station": ns, "corrected": nc, "abs_diff": abs(nc - ns)}}


def _flat(s):
    return {"mae": s["mae"], "jan_coldest_error": s["jan_coldest_error"],
            "nights_below_abs_diff": s["nights_below"]["abs_diff"], "detail": s}


def compare_cold_night_methods(power, station, col, seasons, min_days_per_year, min_days, n_quantiles, frost_c):
    """Held-out comparison of quantile mapping with the monthly offset (VALIDATION.md 3.14). Owner, step-4
    review item 1 (2026-11-12): the offset serves the twin's temperatures and ET0, quantile mapping serves
    frost, whatever this comparison says; it is reported, not used to switch methods. The returned
    models are refitted on all qualifying years."""
    shared = bias.shared_days(power, station, col)
    years = bias.qualifying_years(shared, min_days_per_year)
    fit, test = bias.split_years(years)
    if not fit or not test:
        raise ValueError(f"no held-out comparison possible: fit years {fit}, test years {test}")
    offsets = bias.fit_monthly_offsets(shared, fit, min_days)
    qm = fit_qmap(shared, fit, col, seasons, min_days, n_quantiles)
    t = shared[shared["year"].isin(test)]
    tdf = pd.DataFrame({"date": t["date"].to_numpy(), col: t[f"{col}_power"].to_numpy()})
    so = _flat(cold_night_scores(t["date"], t[f"{col}_station"], bias.apply_offsets(tdf, col, offsets), frost_c))
    sq = _flat(cold_night_scores(t["date"], t[f"{col}_station"], apply_qmap(tdf, col, qm), frost_c))
    keys = ("mae", "jan_coldest_error", "nights_below_abs_diff")
    better = [k for k in keys if sq[k] is not None and so[k] is not None and sq[k] < so[k]]
    return {"fit_years": fit, "test_years": test, "offset": so, "qmap": sq, "qmap_better_on": better,
            "qmap_models": fit_qmap(shared, years, col, seasons, min_days, n_quantiles)}
