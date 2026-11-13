"""Area numbers and their stated uncertainty (rules.yaml area_map numbers, threshold_shift, year_to_year,
worldcover_bound). Pure functions."""
import warnings

import numpy as np


def mean_over_counted(values, counted, min_years):
    """values, counted: (years x pixels). The mean over the years that count; NaN with fewer than min_years."""
    v = np.where(counted, np.asarray(values, float), np.nan)
    n = np.asarray(counted).sum(0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        m = np.nanmean(v, axis=0)
    return np.where(n >= min_years, m, np.nan)


def season_class(mean):
    """Nearest whole number, halves up, 3 = three or more; -1 where there is no value."""
    m = np.asarray(mean, float)
    c = np.floor(np.where(np.isfinite(m), m, 0) + 0.5).astype(int)
    return np.where(np.isfinite(m), np.minimum(c, 3), -1)


def bare_class(mean, breaks):
    """0 below the first break ... len(breaks) at or above the last; -1 where there is no value."""
    m = np.asarray(mean, float)
    return np.where(np.isfinite(m), np.digitize(np.where(np.isfinite(m), m, 0), breaks), -1)


def commission(users_pct, ci_pct):
    """Worst-case share of mapped pixels that are not cropland: 1 - the lower end of the user's accuracy."""
    return round(1 - (users_pct - ci_pct) / 100, 6)


def share_bound(s, c):
    """A share s among mapped pixels, if a fraction c of them are not cropland and all fall on one side."""
    return max(0.0, (s - c) / (1 - c)), min(1.0, s / (1 - c))


def median_bound(values, c):
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    return float(np.quantile(v, 0.5 - c / 2)), float(np.quantile(v, 0.5 + c / 2))


def numbers(mean_bare, season_cls, long_bare_days):
    """The three area numbers over the pixels with a value."""
    ok = np.isfinite(mean_bare)
    sc = season_cls[season_cls >= 0]
    return {"median_bare_days": float(np.median(mean_bare[ok])) if ok.any() else None,
            "share_long_bare": float((mean_bare[ok] > long_bare_days).mean()) if ok.any() else None,
            "share_two_seasons": float((sc == 2).mean()) if len(sc) else None,
            "pixels_bare": int(ok.sum()), "pixels_seasons": int(len(sc))}
