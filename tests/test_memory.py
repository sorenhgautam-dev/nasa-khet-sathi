"""Field memory (CLAUDE.md "Field memory", build step 7b; rules.yaml field_memory): pipeline/ml/memory.py.
Does a small learned correction predict a season's peak greenness better than the physics twin alone, on years it
has not seen? Worked examples on made-up seasons."""
import numpy as np
import pandas as pd
import pytest

from pipeline.ml import memory as fm


def _seasons(n_years=12, seed=0, signal=0.0):
    """Two seasons a year; the target follows `rain` by `signal` and the twin's shortfall not at all."""
    rng = np.random.default_rng(seed)
    rows = []
    for y in range(2014, 2014 + n_years):
        for slot in ("monsoon", "winter"):
            rain = rng.uniform(0, 1)
            rows.append({"year": y, "slot": slot, "twin_shortfall": rng.uniform(0, 1), "rain": rain,
                         "target": signal * (rain - 0.5) + rng.normal(0, 0.02)})
    return pd.DataFrame(rows)


def test_window_features_are_sums_and_means_over_the_window_only():
    d = pd.date_range("2020-01-01", "2020-01-10")
    daily = pd.DataFrame({"date": d, "eta_mm": [1.0] * 10, "etc_mm": [2.0] * 10, "rain_mm": [0, 0, 5, 0, 0, 0, 0, 3, 0, 0],
                          "tmax_c": np.arange(10.0, 20.0)})
    f = fm.window_features(daily, "2020-01-02", "2020-01-09", dry_day_mm=1.0)
    assert f["twin_shortfall"] == pytest.approx(0.5) and f["rain_mm"] == 8.0
    assert f["longest_dry_spell_days"] == 4 and f["tmax_mean_c"] == pytest.approx(14.5)


def test_the_target_is_the_peak_minus_its_slots_own_mean():
    df = pd.DataFrame({"slot": ["monsoon", "monsoon", "winter", "winter"], "peak_ndvi": [0.9, 0.8, 0.7, 0.9]})
    assert fm.peak_anomaly(df).tolist() == pytest.approx([0.05, -0.05, -0.1, 0.1])


def test_leave_one_year_out_never_trains_on_a_season_of_the_held_out_year():
    df = _seasons(4)
    seen = []

    def spy(Xtr, ytr, Xte):
        seen.append((len(Xtr), len(Xte)))
        return np.zeros(len(Xte))
    fm.loyo_predict(df[["rain"]].to_numpy(), df["target"].to_numpy(), df["year"].to_numpy(), spy)
    assert seen == [(6, 2)] * 4


def test_memory_is_kept_when_it_beats_physics_and_no_anomaly_on_held_out_years():
    df = _seasons(signal=0.3)
    r = fm.compare(df, physics="twin_shortfall", features=["twin_shortfall", "rain"], alpha=1.0)
    assert r["rmse"]["memory"] < r["rmse"]["physics_only"] and r["rmse"]["memory"] < r["rmse"]["no_anomaly"]
    assert r["kept"] is True and r["n_seasons"] == 24 and r["n_years"] == 12


def test_memory_is_not_kept_when_there_is_nothing_to_learn():
    df = _seasons(signal=0.0, seed=3)
    r = fm.compare(df, physics="twin_shortfall", features=["twin_shortfall", "rain"], alpha=1.0)
    assert r["kept"] is False and "physics only" in r["decision"]


def test_too_few_years_is_refused():
    with pytest.raises(ValueError, match="years"):
        fm.compare(_seasons(2), physics="twin_shortfall", features=["rain"], alpha=1.0)
