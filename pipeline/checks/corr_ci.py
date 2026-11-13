"""Shared statistics of the independent checks of the twin (rules.yaml validation_checks.common). Pure.

correlate(): Pearson and Spearman with 95% percentile bootstrap intervals (10,000 resamples, seed 0); `blocks` resamples
whole groups (e.g. calendar years of monthly anomalies) so autocorrelated values stay together (Efron & Tibshirani 1993,
ch. 13 and sec. 8.6). detectable_r(): the smallest |r| an n can tell from zero at the 5% level (t test on r).
"""
import numpy as np
import pandas as pd
from scipy import stats

N_BOOT, SEED = 10_000, 0


def _corr(x, y, method):
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan
    if method == "spearman":
        x, y = stats.rankdata(x), stats.rankdata(y)
    return float(np.corrcoef(x, y)[0, 1])


def bootstrap(x, y, blocks=None, n_boot=N_BOOT, seed=SEED, method="pearson"):
    """The correlation of n_boot resamples (NaN for a resample in which one series is constant)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    blocks = np.arange(len(x)) if blocks is None else np.asarray(blocks)
    groups = [np.flatnonzero(blocks == b) for b in pd.unique(blocks)]
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for k in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        out[k] = _corr(x[idx], y[idx], method)
    return out


def detectable_r(n, alpha=0.05):
    """Smallest |r| distinguishable from 0 at `alpha` (two-sided): r = t / sqrt(n - 2 + t^2)."""
    if n < 3:
        return None
    t = stats.t.ppf(1 - alpha / 2, n - 2)
    return round(float(t / np.sqrt(n - 2 + t * t)), 3)


def correlate(x, y, blocks=None, n_boot=N_BOOT, seed=SEED):
    """{n, pearson, spearman, pearson_ci, spearman_ci, boot_valid, detectable_r} over the pairs where both are finite."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    b = None if blocks is None else np.asarray(blocks)[ok]
    x, y = x[ok], y[ok]
    out = {"n": int(len(x)), "detectable_r": detectable_r(len(x))}
    for m in ("pearson", "spearman"):
        out[m] = None if len(x) < 3 else _round(_corr(x, y, m))
        if len(x) < 3:
            out[f"{m}_ci"] = None
            continue
        v = bootstrap(x, y, b, n_boot, seed, m)
        v = v[np.isfinite(v)]
        out[f"{m}_ci"] = [_round(np.percentile(v, 2.5)), _round(np.percentile(v, 97.5))] if len(v) else None
        out["boot_valid"] = int(len(v))
    return out


def _round(v):
    return None if v is None or not np.isfinite(v) else round(float(v), 3)


def is_degenerate(values, decimals=6):
    """More than half of the values are one and the same value (to `decimals`): not testable."""
    v = np.round(np.asarray(values, float), decimals)
    v = v[np.isfinite(v)]
    if not len(v):
        return True
    _, counts = np.unique(v, return_counts=True)
    return bool(counts.max() > len(v) / 2)


def excludes_zero(ci, sign):
    """The interval lies wholly on the expected side of zero (sign +1 or -1)."""
    if ci is None:
        return False
    return bool(ci[0] > 0) if sign > 0 else bool(ci[1] < 0)


def monthly_anomaly(s):
    """A monthly series minus each calendar month's own mean."""
    s = pd.Series(s).astype(float)
    return s - s.groupby(s.index.month).transform("mean")


def step_sd(anom, year):
    """Mean from `year` on minus the mean before it, in units of the series' own standard deviation."""
    before, after = anom[anom.index.year < year], anom[anom.index.year >= year]
    return round(float((after.mean() - before.mean()) / anom.std()), 2)
