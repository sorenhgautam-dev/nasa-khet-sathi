"""ECOSTRESS ESI against the twin's crop water stress, by season (VALIDATION 4.2c; rules.yaml validation_checks.ecostress,
written before the first run). Pure: the runner (scripts/run_validation_checks.py) reads the files.

Per crop season of the current rotation (the twin's own dates), the mean ESI of the kept overpasses inside it is compared
with the twin's ETa/ETc for that season (both are water used over water needed), per slot. ESI is model-based (PT-JPL,
driven by the overpass's land surface temperature) and comes from one 70 m pixel, 37% of it the field.
"""
import numpy as np
import pandas as pd

from pipeline.checks import corr_ci as cc


def slot_of_crop_season(start, end):
    """monsoon when the season's middle day falls in June-November (diary/guess.SLOTS), else winter."""
    mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
    return "monsoon" if mid.month in (6, 7, 8, 9, 10, 11) else "winter"


def season_esi(overpasses, seasons):
    """One row per twin season: crop, year, slot, start, end, n_overpasses, esi_mean (NaN without overpasses), and the
    season's twin values passed in (eta_over_etc, ...)."""
    d = pd.DataFrame(overpasses).dropna(subset=["esi"])
    rows = []
    for s in seasons:
        a, b = pd.Timestamp(s["start"]), pd.Timestamp(s["end"])
        inside = d[(d["local_date"] >= a) & (d["local_date"] <= b)]
        rows.append({**s, "slot": slot_of_crop_season(a, b), "n_overpasses": int(len(inside)),
                     "esi_mean": float(inside["esi"].mean()) if len(inside) else np.nan})
    return pd.DataFrame(rows)


def slot_result(df, min_overpasses, min_seasons, twin_col="eta_over_etc"):
    """The slot's verdict under the pre-declared rule: enough seasons with enough overpasses, twin not degenerate, Spearman
    interval above 0. Correlates the ESI anomaly (slot mean removed) with the twin's ETa/ETc anomaly."""
    q = df[df["n_overpasses"] >= min_overpasses].copy()
    out = {"seasons_with_esi": int((df["n_overpasses"] > 0).sum()), "qualifying_seasons": int(len(q)),
           "overpasses_per_season": {int(y): int(n) for y, n in zip(df["year"], df["n_overpasses"])},
           "holds_up": False, "correlation": None}
    if len(q) < min_seasons:
        out["status"] = f"not testable: {len(q)} season(s) with at least {min_overpasses} clear overpasses, fewer than {min_seasons}"
        return out
    if cc.is_degenerate(q[twin_col]):
        out["status"] = "not testable: the twin's series is degenerate (more than half the seasons share one value)"
        return out
    q["esi_anomaly"] = q["esi_mean"] - q["esi_mean"].mean()
    q["twin_anomaly"] = q[twin_col] - q[twin_col].mean()
    r = cc.correlate(q["twin_anomaly"], q["esi_anomaly"])
    out["correlation"] = r
    out["holds_up"] = cc.excludes_zero(r["spearman_ci"], +1)
    out["status"] = "holds up" if out["holds_up"] else "does not hold up (the Spearman interval reaches 0 or below)"
    out["seasons"] = [{"year": int(y), "esi_mean": round(float(e), 4), twin_col: round(float(t), 4), "n_overpasses": int(n)}
                      for y, e, t, n in zip(q["year"], q["esi_mean"], q[twin_col], q["n_overpasses"])]
    return out


def overpass_pairs(overpasses, ks_daily):
    """Each kept ESI with the twin's Ks (daily ETa/ETc) on its local date; overpasses outside the twin's record dropped."""
    d = pd.DataFrame(overpasses).dropna(subset=["esi"])
    ks = pd.Series(ks_daily)
    d = d.assign(ks=d["local_date"].map(ks)).dropna(subset=["ks"])
    return d.reset_index(drop=True)


def overpass_day_result(pairs):
    """Descriptive: Spearman/Pearson of ESI and Ks on overpass days, raw and as anomalies from each calendar month's mean,
    with a year-block bootstrap."""
    if len(pairs) < 3:
        return {"n": int(len(pairs)), "status": "too few overpass days"}
    years = pairs["local_date"].dt.year.to_numpy()
    raw = cc.correlate(pairs["ks"], pairs["esi"], blocks=years)
    m = pairs["local_date"].dt.month
    anom = cc.correlate(pairs["ks"] - pairs["ks"].groupby(m).transform("mean"),
                        pairs["esi"] - pairs["esi"].groupby(m).transform("mean"), blocks=years)
    return {"n": int(len(pairs)), "raw_with_seasonal_cycle": raw, "monthly_anomalies": anom,
            "ks_below_1_share": round(float((pairs["ks"] < 1).mean()), 3)}
