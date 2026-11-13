"""Season detective (CLAUDE.md "SI components" 1, build step 6b): a random forest that labels each day growing,
harvested or bare from the smoothed NDVI curve plus rain and temperature. Pure functions (no file I/O).

Features of a day d (all from data, none from a calendar):
- ndvi_s: the smoothed NDVI (pipeline/diary/seasons.smooth)
- slope_back, slope_fwd: change of ndvi_s over the slope_days before d and after d
- days_since_low: days since the lowest ndvi_s of the low_window_days ending on d ("time since green-up")
- rain_mm_sum: rain over the weather_days ending on d (the twin's GPM rain)
- tmean_c: mean of (tmax_c + tmin_c) / 2 over the weather_days ending on d (the twin's corrected POWER)

Training labels are the days on which the threshold and change-point methods agree, in the training years only
(CLAUDE.md: "high-confidence dates from the threshold method plus the farmer-confirmed calendar"; there is no
farmer-confirmed calendar yet: the demo field is a placeholder).
"""
import numpy as np
import pandas as pd

FEATURES = ("ndvi_s", "slope_back", "slope_fwd", "days_since_low", "rain_mm_sum", "tmean_c")


def features(dates, ndvi_s, rain_mm, tmean_c, slope_days, low_window_days, weather_days):
    """One row per day; NaN where a window runs off the series (those days are not labelled)."""
    idx = pd.DatetimeIndex(dates)
    s = pd.Series(np.asarray(ndvi_s, float), index=idx)
    arr = s.to_numpy()
    low = np.full(len(arr), np.nan)
    for i in range(low_window_days - 1, len(arr)):
        a = i - low_window_days + 1
        low[i] = i - (a + int(np.argmin(arr[a:i + 1])))
    rain = pd.Series(np.asarray(rain_mm, float), index=idx)
    temp = pd.Series(np.asarray(tmean_c, float), index=idx)
    return pd.DataFrame({
        "ndvi_s": arr,
        "slope_back": (s - s.shift(slope_days)).to_numpy(),
        "slope_fwd": (s.shift(-slope_days) - s).to_numpy(),
        "days_since_low": low,
        "rain_mm_sum": rain.rolling(weather_days, min_periods=weather_days).sum().to_numpy(),
        "tmean_c": temp.rolling(weather_days, min_periods=weather_days).mean().to_numpy(),
    }, index=idx)


def train(X, y, trees, min_samples_leaf, seed):
    from sklearn.ensemble import RandomForestClassifier
    ok = X[list(FEATURES)].notna().all(axis=1).to_numpy() & pd.notna(np.asarray(y, object))
    if ok.sum() == 0:
        raise ValueError("no training day has all features and a label")
    m = RandomForestClassifier(n_estimators=trees, min_samples_leaf=min_samples_leaf, random_state=seed, n_jobs=1)
    m.fit(X.loc[ok, list(FEATURES)].to_numpy(), np.asarray(y, object)[ok].astype(str))
    return m


def predict(model, X):
    """Labels per day; None where a feature is missing."""
    ok = X[list(FEATURES)].notna().all(axis=1).to_numpy()
    out = np.full(len(X), None, dtype=object)
    if ok.any():
        out[ok] = model.predict(X.loc[ok, list(FEATURES)].to_numpy())
    return out
