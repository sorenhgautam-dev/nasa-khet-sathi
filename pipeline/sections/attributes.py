"""Per-section attributes (build step 8, rules.yaml `sections`). Pure functions; scripts/run_sections.py reads the files.

Greenness. A section's NDVI on one HLS image is the area-weighted mean of the 30 m pixels it overlaps (weight = overlap
area / section area), kept only when its clear pixels holding NDVI carry at least greenness.min_clear_fraction of its
area: the field's own cloud rule (pipeline/diary/greenness.py), by area instead of by pixel count. A season's peak is
the maximum of the smoothed daily curve between the season's start and end, drawn as the diary draws the field's
(greenness.daily_series, then seasons.smooth); a section's anomaly is its peak minus the field's (all sections).

'Usually greener' (owner, 2026-11-14). Per section, a two-sided exact sign test on its seasons' anomalies (zeros left
out), Holm's step-down over the field's sections. 'greener' / 'less green' need the test AND a median anomaly larger
in size than the satellite's normal noise: the same-day Landsat/Sentinel-2 vegetation-index difference of HLS v2.0
(below 4.5%, Ju et al. 2025) times the field's median season peak. Otherwise 'same'. "can't tell" only when the
seasons are too few for any outcome to pass Holm's first step.

Low ground. Topographic position index (Weiss 2001, as documented by Jenness 2006): a pixel's elevation minus the mean
of the elevations whose pixel centres lie within a radius (itself included), with their standard deviation (ddof 0).
Weiss's valley class is TPI <= -1 SD. A TPI smaller in size than NASADEM's stated relative error says nothing: null.
"""
import math

import numpy as np

from pipeline.sections.grid import clip_to_rect, shoelace


# ---------- greenness ----------

def pixel_weights(section_xy, transform, shape):
    """[{'row', 'col', 'weight'}], largest first: the share of the section's area in each pixel of a north-up grid.
    section_xy: corners in the grid's coordinates; transform: (a, b, c, d, e, f) as rasterio's Affine (x = c + col a,
    y = f + row e, with b = d = 0 and e < 0)."""
    a, b, c, d, e, f = (float(v) for v in tuple(transform)[:6])
    if b or d or a <= 0 or e >= 0:
        raise ValueError("pixel_weights needs a north-up grid (no rotation, rows going south)")
    x0, y0 = (float(v) for v in section_xy[0][:2])     # from the first corner: UTM-sized products round off in shoelace
    section_xy, c, f = [(float(x) - x0, float(y) - y0) for x, y in section_xy], c - x0, f - y0
    area = shoelace(section_xy)
    if area <= 0:
        raise ValueError("the section has no area")
    xs, ys = [p[0] for p in section_xy], [p[1] for p in section_xy]
    c0, c1 = math.floor((min(xs) - c) / a), math.floor((max(xs) - c) / a)
    r0, r1 = math.floor((max(ys) - f) / e), math.floor((min(ys) - f) / e)
    out = []
    for row in range(r0, r1 + 1):
        for col in range(c0, c1 + 1):
            x_lo, y_hi = c + col * a, f + row * e
            piece = clip_to_rect(section_xy, x_lo, y_hi + e, x_lo + a, y_hi)
            w = shoelace(piece) / area if piece else 0.0
            if w <= 1e-9:
                continue
            if not (0 <= row < shape[0] and 0 <= col < shape[1]):
                raise ValueError(f"the section reaches outside the raster (row {row}, col {col})")
            out.append({"row": int(row), "col": int(col), "weight": w})
    total = sum(o["weight"] for o in out)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"pixel weights sum to {total}, not 1")
    return sorted(out, key=lambda o: (-o["weight"], o["row"], o["col"]))


def section_observation(ndvi, clear, weights, min_clear_fraction):
    """One image over one section: {'ndvi': weighted mean of the clear pixels holding NDVI, or None when they carry
    under min_clear_fraction of the section's weight; 'clear_share'}. Arrays in the order of `weights`."""
    w = np.asarray(weights, float)
    v = np.asarray(ndvi, float)
    ok = np.asarray(clear, bool) & np.isfinite(v)
    share = float(w[ok].sum() / w.sum())
    value = float((w[ok] * v[ok]).sum() / w[ok].sum()) if ok.any() and share >= min_clear_fraction - 1e-12 else None
    return {"ndvi": value, "clear_share": share}


def weighted_mean(values, weights):
    """Area-weighted mean; None if any value is missing."""
    if any(v is None or not np.isfinite(v) for v in values):
        return None
    w = np.asarray(weights, float)
    return float((np.asarray(values, float) * w).sum() / w.sum())


def season_peaks(dates, values, seasons, window_days, polyorder, min_obs):
    """Per season ({'start', 'end'} timestamps): {'peak': max of the smoothed daily curve in [start, end] or None,
    'obs': observations in [start, end]}. The curve: linear interpolation between observations, then Savitzky-Golay,
    as the diary draws the field's (pipeline/diary/greenness.daily_series, seasons.smooth)."""
    import pandas as pd

    from pipeline.diary import greenness as gr
    from pipeline.diary import seasons as se
    obs = pd.DataFrame({"date": pd.DatetimeIndex(dates), "ndvi": np.asarray(values, float)}).dropna()
    daily = gr.daily_series(obs, obs["date"].min(), obs["date"].max())
    curve = pd.Series(se.smooth(daily["ndvi"], window_days, polyorder), index=pd.DatetimeIndex(daily["date"]))
    out = []
    for s in seasons:
        n = int(((obs["date"] >= s["start"]) & (obs["date"] <= s["end"])).sum())
        part = curve[(curve.index >= s["start"]) & (curve.index <= s["end"])]
        out.append({"peak": float(part.max()) if n >= min_obs and len(part) else None, "obs": n})
    return out


# ---------- 'usually greener' ----------

def _binom_cdf_half(k, n):
    """P(X <= k) for X ~ Binomial(n, 1/2)."""
    return sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n if k >= 0 else 0.0


def sign_test(values):
    """Two-sided exact sign test of 'the median is 0' (zeros left out): {'n', 'positive', 'negative', 'zeros', 'p'}."""
    v = [float(x) for x in values]
    pos, neg = sum(x > 0 for x in v), sum(x < 0 for x in v)
    n = pos + neg
    p = min(1.0, 2.0 * _binom_cdf_half(min(pos, neg), n)) if n else 1.0
    return {"n": n, "positive": pos, "negative": neg, "zeros": len(v) - n, "p": p}


def holm(pvalues, alpha):
    """Holm's step-down: [rejected?] in the order given (Holm 1979)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    out = [False] * m
    for rank, i in enumerate(order):
        if pvalues[i] <= alpha / (m - rank):
            out[i] = True
        else:
            break
    return out


def median_ci(values, level):
    """(lo, hi, coverage): the widest-k order-statistic interval [x_(k), x_(n-k+1)] whose coverage
    1 - 2 P(X <= k - 1), X ~ Binomial(n, 1/2), is at least `level`; None when even k = 1 falls short."""
    x = sorted(float(v) for v in values)
    n, best = len(x), None
    for k in range(1, n // 2 + 1):
        cover = 1.0 - 2.0 * _binom_cdf_half(k - 1, n)
        if cover >= level:
            best = (x[k - 1], x[n - k], cover)
        else:
            break
    return best


def min_decidable_n(alpha, m):
    """Fewest non-zero anomalies for which the most one-sided outcome passes Holm's first step (p <= alpha / m)."""
    n = 1
    while 2.0 * 0.5 ** n > alpha / m:
        n += 1
    return n


def size_floor(field_peaks, relative):
    """The 'a little greener' floor in NDVI: `relative` (rules.yaml sections.size_floor_relative, the published
    same-day L30/S30 vegetation-index difference) times the field's median season peak; None without peaks."""
    p = [float(x) for x in field_peaks if x is not None and np.isfinite(x)]
    return float(relative * np.median(p)) if p else None


def usually(anomalies, alpha, level, floor_ndvi):
    """{section id: {'word', 'n', 'positive', 'negative', 'zeros', 'p', 'holm_rejected', 'above_floor', 'median', 'ci',
    'decidable'}} from each section's season anomalies (rules.yaml sections.usually_test; owner, 2026-11-14):
    'greener' / 'less green' need BOTH the sign test (Holm over the sections) AND |median anomaly| > floor_ndvi;
    otherwise 'same'. "can't tell" only when the seasons are too few for any outcome to pass Holm's first step.
    The order-statistic interval for the median (at `level`) is reported, not used for the word."""
    ids = list(anomalies)
    tests = {s: sign_test(anomalies[s]) for s in ids}
    rejected = dict(zip(ids, holm([tests[s]["p"] for s in ids], alpha)))
    need = min_decidable_n(alpha, len(ids))
    out = {}
    for s in ids:
        t, vals = tests[s], [float(v) for v in anomalies[s]]
        ci = median_ci(vals, level) if vals else None
        med = float(np.median(vals)) if vals else None
        decidable = t["n"] >= need
        above = med is not None and floor_ndvi is not None and abs(med) > floor_ndvi
        if not decidable:
            word = "can't tell"
        elif rejected[s] and above:
            word = "greener" if t["positive"] > t["negative"] else "less green"
        else:
            word = "same"
        out[s] = {"word": word, **t, "holm_rejected": bool(rejected[s]), "above_floor": bool(above),
                  "decidable": decidable, "median": med,
                  "ci": [ci[0], ci[1]] if ci else None, "ci_coverage": ci[2] if ci else None}
    return out


# ---------- low ground ----------

def tpi_at(dem, row, col, dx_m, dy_m, radius_m):
    """{'tpi_m', 'mean_m', 'sd_m', 'n'} at one DEM pixel: its elevation minus the mean of the elevations whose pixel
    centres lie within radius_m (itself included), and their standard deviation (ddof 0). The circle must lie inside
    the grid and hold no missing height."""
    z = np.asarray(dem, float)
    ri, ci = int(math.floor(radius_m / dy_m)), int(math.floor(radius_m / dx_m))
    if row - ri < 0 or col - ci < 0 or row + ri >= z.shape[0] or col + ci >= z.shape[1]:
        raise ValueError(f"the {radius_m} m circle around row {row}, col {col} reaches outside the grid")
    dr = (np.arange(-ri, ri + 1) * dy_m)[:, None]
    dc = (np.arange(-ci, ci + 1) * dx_m)[None, :]
    disk = dr ** 2 + dc ** 2 <= radius_m ** 2
    vals = z[row - ri: row + ri + 1, col - ci: col + ci + 1][disk]
    if not np.isfinite(vals).all():
        raise ValueError("missing heights inside the TPI circle")
    mean = float(vals.mean())
    return {"tpi_m": float(z[row, col] - mean), "mean_m": mean, "sd_m": float(vals.std()), "n": int(vals.size)}


def low_ground(tpi_m, sd_m, threshold_sd, dem_error_m):
    """True (Weiss's valley class: TPI <= threshold_sd x SD), False, or None when |TPI| is within the DEM's stated
    error (or unknown): "can't tell"."""
    if tpi_m is None or sd_m is None or not (np.isfinite(tpi_m) and np.isfinite(sd_m)):
        return None
    if abs(tpi_m) < dem_error_m:
        return None
    return bool(tpi_m <= threshold_sd * sd_m)
