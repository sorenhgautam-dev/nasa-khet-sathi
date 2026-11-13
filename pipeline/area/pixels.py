"""Per-pixel versions of the field diary's own steps (rules.yaml area_map). Pure functions, vectorised over pixels.

- Cropland on the HLS 30 m grid: the share of WorldCover 2021 10 m pixel centres inside each 30 m pixel that are
  cropland (class 40), and how many centres fall inside it (an edge pixel half outside the box has few).
- Daily series: same-day clear observations averaged, then linear interpolation in time between clear observations,
  nothing outside them: pipeline/diary/greenness.py daily_series, here for many pixels at once and bit for bit the
  same (the same arithmetic as numpy.interp on nanosecond times, which pandas' 'time' interpolation calls).
- Bare days per year, and seasons with the threshold method (pipeline/diary/seasons.py, called as the diary does).
"""
import math

import numpy as np
import pandas as pd

from pipeline.diary import seasons as se
from pipeline.fetch.worldcover import KM_PER_DEG


# ---------- cropland ----------

def cropland_fraction(classes, transform, crs, grid_shape, grid_transform, grid_crs, cls=40):
    """(fraction of centres of class `cls`, number of centres) per pixel of the target grid."""
    from rasterio.warp import transform as warp
    a = np.asarray(classes)
    rows, cols = np.indices(a.shape)
    x = transform.c + transform.a * (cols.ravel() + 0.5)
    y = transform.f + transform.e * (rows.ravel() + 0.5)
    if str(crs) != str(grid_crs):
        x, y = (np.asarray(v) for v in warp(crs, grid_crs, x, y))
    c = np.floor((x - grid_transform.c) / grid_transform.a).astype(np.int64)
    r = np.floor((y - grid_transform.f) / grid_transform.e).astype(np.int64)
    H, W = grid_shape
    ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
    idx = r[ok] * W + c[ok]
    n = np.bincount(idx, minlength=H * W).reshape(H, W)
    k = np.bincount(idx, weights=(a.ravel()[ok] == cls).astype(float), minlength=H * W).reshape(H, W)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(n > 0, k / np.maximum(n, 1), 0.0)
    return frac, n


def expected_centres(wc_transform, lat, pixel_m=30):
    """How many WorldCover pixel centres a pixel_m x pixel_m square holds at latitude `lat`."""
    m = KM_PER_DEG * 1000
    area = abs(wc_transform.e) * m * abs(wc_transform.a) * m * math.cos(math.radians(lat))
    return pixel_m * pixel_m / area


def cropland_mask(frac, n, expected, min_fraction, min_coverage):
    return (np.asarray(n) >= min_coverage * expected) & (np.asarray(frac) >= min_fraction)


# ---------- the diary's daily series, per pixel ----------

def same_day_mean(dates, values):
    """values (observations x pixels, NaN = not clear) -> (unique days, their per-pixel mean; NaN if none clear)."""
    d = pd.DatetimeIndex(dates).normalize()
    days, inv = np.unique(d.to_numpy(), return_inverse=True)
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    s = np.zeros((len(days),) + v.shape[1:]); n = np.zeros_like(s)
    np.add.at(s, inv, np.where(ok, v, 0.0))
    np.add.at(n, inv, ok)
    with np.errstate(invalid="ignore"):
        return pd.DatetimeIndex(days), np.where(n > 0, s / np.where(n > 0, n, 1), np.nan)


def daily_matrix(obs_days, obs_values, start, end):
    """Interpolated daily NDVI (days x pixels) between each pixel's clear observations, NaN outside them.
    obs_days: unique, sorted days inside [start, end]; obs_values: (len(obs_days) x pixels), NaN = no clear value."""
    days = pd.date_range(start, end)
    od = pd.DatetimeIndex(obs_days)
    if len(od) and (od.min() < days[0] or od.max() > days[-1]):
        raise ValueError("observations outside [start, end] would change the edges; cut them first")
    v = np.asarray(obs_values, float).reshape(len(od), -1)
    T, P = len(days), v.shape[1]
    M = np.full((T, P), np.nan)
    M[days.get_indexer(od)] = v
    ns = days.asi8                                        # pandas hands numpy.interp the nanosecond index
    for p in range(P):                                    # numpy.interp itself: its compiled arithmetic (fused
        col = M[:, p]                                     # multiply-add on some machines) is matched bit for bit
        ok = np.nonzero(np.isfinite(col))[0]
        if len(ok) == 0:
            continue
        gap = np.arange(ok[0], ok[-1] + 1)
        gap = gap[~np.isfinite(col[gap])]                 # only the days without a value, as pandas passes them
        if len(gap):
            col[gap] = np.interp(ns[gap], ns[ok], col[ok])
    return M


def yearly_counts(daily, days, years, ndvi_max):
    """(bare days, days with a value), each (years x pixels): bare = interpolated NDVI below ndvi_max."""
    yr = pd.DatetimeIndex(days).year.to_numpy()
    has = np.isfinite(daily)
    with np.errstate(invalid="ignore"):
        bare = has & (daily < ndvi_max)
    b = np.stack([bare[yr == y].sum(0) for y in years])
    h = np.stack([has[yr == y].sum(0) for y in years])
    return b, h


def pixel_season_peak_years(days, ndvi, S):
    """Calendar years of the peaks of one pixel's threshold-method seasons (rules.yaml season_detection), run as
    scripts/run_diary.py runs it: on the days with a value (a gap-free stretch between the first and last clear day)."""
    v = np.asarray(ndvi, float)
    ok = np.isfinite(v)
    if ok.sum() < S["smooth_window_days"]:
        return []
    idx = np.nonzero(ok)[0]
    v = v[idx[0]: idx[-1] + 1]
    if np.isnan(v).any():
        raise ValueError("a pixel's daily series has a gap inside it")
    d = pd.DatetimeIndex(days)[idx[0]: idx[-1] + 1]
    sm = se.smooth(v, S["smooth_window_days"], S["smooth_polyorder"])
    th = se.threshold_seasons(d, sm, S["min_amplitude"], S["threshold_fraction"],
                              S["min_amplitude_range_fraction"], S["min_amplitude_range_years"])
    return [s["peak"].year for s in th]


def count_by_year(peak_years, years):
    return [sum(1 for p in peak_years if p == y) for y in years]


def process_chunk(args):
    """One block of pixels, for a worker process: raw HLS observations -> yearly bare days at each threshold,
    days with a value, and seasons per year. args: (obs_dates, raw int16 (granules x pixels), fill, scale, start, end,
    years, thresholds, S)."""
    dates, raw, fill, scale, start, end, years, thresholds, S = args
    v = raw.astype(float)
    v[raw == fill] = np.nan
    v *= scale                                            # as pipeline/diary/ndvi.py scale_ndvi
    udays, mean = same_day_mean(dates, v)
    daily = daily_matrix(udays, mean, start, end)
    days = pd.date_range(start, end)
    bare = {}
    for thr in thresholds:
        bare[thr], has = yearly_counts(daily, days, years, thr)
    seasons = np.array([count_by_year(pixel_season_peak_years(days, daily[:, p], S), years)
                        for p in range(daily.shape[1])]).T.reshape(len(years), -1)
    return bare, has, seasons
