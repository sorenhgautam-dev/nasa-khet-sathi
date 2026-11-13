"""Field memory (CLAUDE.md "Field memory", build step 7b; rules.yaml field_memory). Pure functions.

Question: does a small learned correction, fed with the twin's own stress and a few weather numbers, predict what
the satellite saw (each season's peak greenness, as a difference from that season's usual peak) better than the
physics twin alone, on years it has not seen? Leave one year out: both seasons of the held-out year are predicted
by a model fitted on the other years. The memory is kept only if its held-out error is lower than physics alone AND
lower than predicting no anomaly at all; otherwise physics only, and the result is reported either way.

Peak NDVI is a stand-in for harvest: it measures green cover, not grain or tubers. With about two dozen seasons the
test is weak; say so wherever the result is shown.
"""
import numpy as np
import pandas as pd

MIN_YEARS = 6


def window_features(daily, start, end, dry_day_mm):
    """The twin's water shortfall and the weather over [start, end]. daily: date, eta_mm, etc_mm, rain_mm, tmax_c."""
    d = daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))]
    if d.empty or d[["eta_mm", "etc_mm", "rain_mm", "tmax_c"]].isna().any().any():
        raise ValueError(f"no complete twin days between {start} and {end}")
    best = run = 0
    for v in d["rain_mm"].to_numpy(float):
        run = run + 1 if v < dry_day_mm else 0
        best = max(best, run)
    etc = float(d["etc_mm"].sum())
    return {"twin_shortfall": 1.0 - float(d["eta_mm"].sum()) / etc if etc > 0 else 0.0,
            "rain_mm": float(d["rain_mm"].sum()), "longest_dry_spell_days": int(best),
            "tmax_mean_c": float(d["tmax_c"].mean())}


def peak_anomaly(seasons):
    """Each season's peak NDVI minus the mean peak of its slot (monsoon, winter)."""
    return seasons["peak_ndvi"] - seasons.groupby("slot")["peak_ndvi"].transform("mean")


def fit_predict_ridge(alpha):
    def f(Xtr, ytr, Xte):
        from sklearn.linear_model import Ridge
        mu, sd = Xtr.mean(axis=0), Xtr.std(axis=0)
        sd = np.where(sd > 0, sd, 1.0)
        m = Ridge(alpha=alpha).fit((Xtr - mu) / sd, ytr)
        return m.predict((Xte - mu) / sd)
    return f


def fit_predict_zero(Xtr, ytr, Xte):
    return np.zeros(len(Xte))


def loyo_predict(X, y, years, fit_predict):
    """Held-out predictions: for each year, fit on every other year's seasons and predict that year's."""
    X, y, years = np.asarray(X, float), np.asarray(y, float), np.asarray(years)
    out = np.full(len(y), np.nan)
    for yr in sorted(set(years.tolist())):
        te = years == yr
        out[te] = fit_predict(X[~te], y[~te], X[te])
    return out


def _rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2)))


def compare(df, physics, features, alpha, target="target"):
    """Held-out error of 'no anomaly', physics only (a line on the twin's shortfall) and the memory (ridge on
    `features`), and the decision. df: one row per season with year, target and the predictor columns."""
    years = df["year"].to_numpy()
    if len(set(years.tolist())) < MIN_YEARS:
        raise ValueError(f"field memory needs at least {MIN_YEARS} years of seasons, got {len(set(years.tolist()))}")
    y = df[target].to_numpy(float)
    pred = {"no_anomaly": loyo_predict(df[[physics]].to_numpy(float), y, years, fit_predict_zero),
            "physics_only": loyo_predict(df[[physics]].to_numpy(float), y, years, fit_predict_ridge(0.0)),
            "memory": loyo_predict(df[list(features)].to_numpy(float), y, years, fit_predict_ridge(alpha))}
    rmse = {k: round(_rmse(v, y), 4) for k, v in pred.items()}
    kept = bool(rmse["memory"] < rmse["physics_only"] and rmse["memory"] < rmse["no_anomaly"])
    corr = {k: (round(float(np.corrcoef(v, y)[0, 1]), 3) if np.std(v) > 0 else None) for k, v in pred.items()}
    return {"n_seasons": int(len(df)), "n_years": int(len(set(years.tolist()))), "rmse": rmse, "correlation_with_observed": corr,
            "kept": kept, "predictions": {k: [round(float(x), 4) for x in v] for k, v in pred.items()},
            "decision": ("memory kept: lower held-out error than physics alone and than no anomaly" if kept else
                         "physics only: the memory did not beat both physics alone and 'no anomaly' on held-out years")}
