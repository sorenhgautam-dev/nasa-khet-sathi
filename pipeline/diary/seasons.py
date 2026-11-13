"""Season detection from the field's daily NDVI (CLAUDE.md "Field diary", build step 6b). Pure functions; the
runner is scripts/run_diary.py, the rules are rules.yaml season_detection.

Every method labels each day **growing** (a crop season, green-up to end), **harvested** (between seasons but
not bare: stubble, residue or weeds, NDVI at or above the bare threshold) or **bare** (between seasons, NDVI
below it), and lists its seasons as {start, peak, end, peak_ndvi}. NDVI shows green cover, not which crop.

Amplitude rule (NASA MCD12Q2 C6.1 User Guide sec. 2.2; owner-approved 2026-11-12): a season counts when its rise
and its fall are each at least `min_amplitude` (0.1) and at least `range_fraction` (35%) of the curve's maximum
minus minimum over the `range_years` (3) calendar years centred on the peak's year.

1. Threshold method: Savitzky-Golay smoothed curve; a season is a peak passing the amplitude rule; it starts on the first day the curve reaches `fraction` of the rise from the
   left minimum, and ends on the last day it is still above `fraction` of the fall to the right minimum (the
   amplitude-fraction rule of TIMESAT, Jönsson & Eklundh).
2. Change-point method: PELT (ruptures) with a continuous piecewise-linear cost on the unsmoothed daily series,
   penalty sigma^2 * params_per_change * ln(n) (a BIC-type penalty; sigma = the scatter of the clear
   observations about the smoothed curve); the kinks are refitted by least squares. A season is a peak of that
   fit passing the amplitude rule; it starts at the kink where the rise begins (the largest gain
   in upward slope between the left minimum and the peak) and ends at the kink where the fall ends.
3. Season detective (pipeline/ml/seasons.py): a random forest labelling each day; seasons are its runs of
   'growing' (seasons_from_labels).

The comparison (held-out years, thinned observations) is in compare_on_held_out_years's helpers below: thin,
agreement and choose_best.
"""
import numpy as np
import pandas as pd

LABELS = ("growing", "harvested", "bare")


# ---------- shared ----------

def smooth(ndvi, window_days, polyorder):
    """Savitzky-Golay smoothing of a gap-free daily NDVI series."""
    from scipy.signal import savgol_filter
    v = np.asarray(ndvi, float)
    if np.isnan(v).any():
        raise ValueError("smooth needs a gap-free daily series: interpolate between clear observations first")
    if len(v) < window_days:
        raise ValueError(f"series of {len(v)} days is shorter than the {window_days}-day window")
    return savgol_filter(v, window_days, polyorder)


def observation_sigma(daily, curve):
    """Scatter (root mean square) of the clear observations about a curve: daily rows with gap_days == 0."""
    obs = np.asarray(daily["gap_days"]) == 0
    r = np.asarray(daily["ndvi"], float)[obs] - np.asarray(curve, float)[obs]
    if len(r) < 3:
        raise ValueError("fewer than 3 clear observations: no noise estimate")
    return float(np.sqrt(np.mean(r ** 2)))


def _amplitude_floor(dates, curve, p, min_amplitude, range_fraction, range_years):
    """max(min_amplitude, range_fraction x (max - min) of the curve over the range_years calendar years centred
    on the year of day p)."""
    if not range_fraction:
        return min_amplitude
    years = pd.DatetimeIndex(dates).year
    y, half = years[p], range_years // 2
    w = np.asarray(curve, float)[(years >= y - half) & (years <= y + half)]
    return max(min_amplitude, range_fraction * float(w.max() - w.min()))


def _peaks_and_troughs(curve, min_amplitude, dates=None, range_fraction=0.0, range_years=3):
    """Peaks whose rise and fall both pass the amplitude rule, with the index of the lowest point on each side
    (back to the previous kept peak or the series start, forward to the next or the series end). Peaks that fail
    are dropped and the troughs recomputed until every kept peak passes."""
    from scipy.signal import find_peaks
    curve = np.asarray(curve, float)
    pk = list(find_peaks(curve, prominence=min_amplitude)[0])
    while True:
        out, drop = [], None
        for i, p in enumerate(pk):
            a = pk[i - 1] if i > 0 else 0
            b = pk[i + 1] if i + 1 < len(pk) else len(curve) - 1
            left = a + int(np.argmin(curve[a:p + 1]))
            right = p + int(np.argmin(curve[p:b + 1]))
            floor = _amplitude_floor(dates, curve, p, min_amplitude, range_fraction, range_years)
            if curve[p] - curve[left] >= floor and curve[p] - curve[right] >= floor:
                out.append((int(p), left, right))
            elif drop is None or curve[p] < curve[drop]:
                drop = p                                    # drop the lowest failing peak, then look again
        if drop is None:
            return out
        pk.remove(drop)


def _season(dates, curve, s, p, e):
    return {"start": pd.Timestamp(dates[s]), "peak": pd.Timestamp(dates[p]), "end": pd.Timestamp(dates[e]),
            "peak_ndvi": round(float(curve[p]), 3)}


def labels_from_seasons(dates, seasons, curve, bare_max):
    """growing inside a season (start to end, both included); outside, bare below bare_max, else harvested."""
    lab = np.where(np.asarray(curve, float) < bare_max, "bare", "harvested").astype(object)
    idx = pd.DatetimeIndex(dates)
    for s in seasons:
        lab[(idx >= s["start"]) & (idx <= s["end"])] = "growing"
    return lab


# ---------- 1. threshold method ----------

def threshold_seasons(dates, curve, min_amplitude, fraction, range_fraction=0.0, range_years=3):
    curve = np.asarray(curve, float)
    out = []
    for p, l, r in _peaks_and_troughs(curve, min_amplitude, dates, range_fraction, range_years):
        up = curve[l] + fraction * (curve[p] - curve[l])
        down = curve[r] + fraction * (curve[p] - curve[r])
        s = l + int(np.argmax(curve[l:p + 1] >= up))
        above = curve[p:r + 1] >= down
        e = p + int(len(above) - 1 - np.argmax(above[::-1]))
        out.append(_season(dates, curve, s, p, e))
    return out


# ---------- 2. change-point method ----------

def changepoints(y, sigma, params_per_change, min_size):
    """Kink indices of a continuous piecewise-linear PELT fit (ruptures 'clinear'). ruptures returns segment
    ends b; its clinear segment runs through y[start - 1] and y[b - 1], so the kink sits at index b - 1."""
    import ruptures as rpt
    y = np.asarray(y, float)
    if np.isnan(y).any():
        raise ValueError("changepoints needs a gap-free daily series")
    pen = sigma ** 2 * params_per_change * np.log(len(y))
    bk = rpt.Pelt(model="clinear", min_size=min_size, jump=1).fit(y.reshape(-1, 1)).predict(pen=pen)
    return [b - 1 for b in bk[:-1]]


def piecewise_linear_fit(y, kinks):
    """Least-squares continuous piecewise-linear fit with kinks at the given indices."""
    y = np.asarray(y, float)
    t = np.arange(len(y), dtype=float)
    X = np.column_stack([np.ones_like(t), t] + [np.clip(t - k, 0, None) for k in kinks])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return X @ coef


def changepoint_seasons(dates, fit, kinks, min_amplitude, range_fraction=0.0, range_years=3):
    fit = np.asarray(fit, float)
    v = np.array(sorted({0, len(fit) - 1, *kinks}))
    slope = np.diff(fit[v]) / np.diff(v)                          # slope of each segment between vertices
    before = np.concatenate([[0.0], slope])                       # slope arriving at each vertex (0 at the start)
    after = np.concatenate([slope, [0.0]])                        # slope leaving it (0 at the end)
    rise_gain = after - np.maximum(before, 0)                     # where a rise begins
    fall_end = np.minimum(after, 0) - before                      # where a fall ends
    out = []
    for p, l, r in _peaks_and_troughs(fit, min_amplitude, dates, range_fraction, range_years):
        left = (v >= l) & (v < p)
        right = (v > p) & (v <= r)
        s = int(v[left][np.argmax(rise_gain[left])]) if left.any() else l
        e = int(v[right][np.argmax(fall_end[right])]) if right.any() else r
        out.append(_season(dates, fit, s, p, e))
    return out


# ---------- from day labels to seasons (season detective) ----------

def mode_filter(labels, window_days):
    """Centred rolling majority of the labels; a tie keeps the day's own label."""
    lab = np.asarray(labels, object)
    half = window_days // 2
    out = lab.copy()
    for i in range(len(lab)):
        w = lab[max(0, i - half): i + half + 1]
        vals, counts = np.unique(w.astype(str), return_counts=True)
        top = vals[counts == counts.max()]
        if len(top) == 1:
            out[i] = top[0]
    return out


def seasons_from_labels(dates, labels, curve, bare_max, min_days):
    """Runs of 'growing' at least min_days long become seasons (peak = the curve's highest day in the run);
    shorter runs are relabelled bare or harvested from the curve. Returns (seasons, labels)."""
    lab = np.asarray(labels, object).copy()
    curve = np.asarray(curve, float)
    g = lab == "growing"
    seasons, i = [], 0
    while i < len(lab):
        if not g[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(lab) and g[j + 1]:
            j += 1
        if j - i + 1 >= min_days:
            p = i + int(np.argmax(curve[i:j + 1]))
            seasons.append(_season(dates, curve, i, p, j))
        else:
            lab[i:j + 1] = np.where(curve[i:j + 1] < bare_max, "bare", "harvested")
        i = j + 1
    return seasons, lab


# ---------- comparison on held-out years ----------

def thin(obs, year, window_days):
    """Keep, in `year` only, the first clear observation in each window_days-day window from 1 January (the
    density of a cloudy year or of the early record); other years are untouched."""
    o = obs.dropna(subset=["ndvi"]).assign(date=lambda d: pd.to_datetime(d["date"])).sort_values("date")
    in_y = o["date"].dt.year == year
    sub = o[in_y]
    k = (sub["date"] - pd.Timestamp(f"{year}-01-01")).dt.days // window_days
    return pd.concat([o[~in_y], sub.groupby(k.to_numpy()).head(1)]).sort_values("date").reset_index(drop=True)


def agreement(a, b, mask=None):
    """Share of days on which two label arrays agree (only where mask is True)."""
    a, b = np.asarray(a, object), np.asarray(b, object)
    m = np.ones(len(a), bool) if mask is None else np.asarray(mask, bool)
    if m.sum() == 0:
        return None
    return float((a[m] == b[m]).mean())


def choose_best(scores, baseline, margin):
    """The method with the highest score; it replaces the baseline only if it beats it by at least `margin`."""
    best = max(scores, key=lambda k: scores[k])
    if best != baseline and scores[best] - scores[baseline] < margin:
        return baseline
    return best
