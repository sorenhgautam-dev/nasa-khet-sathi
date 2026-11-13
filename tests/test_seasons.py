"""Season detection, three methods (CLAUDE.md "Field diary" and "SI components" 1, build step 6b). Worked examples
for pipeline/diary/seasons.py and pipeline/ml/seasons.py; rules in rules.yaml season_detection."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import seasons as se
from pipeline.fetch.rules import load_rules
from pipeline.ml import seasons as det

R = load_rules()
S = R["season_detection"]


def test_the_rules():
    assert S["min_amplitude"] == 0.1 and S["min_amplitude_range_fraction"] == 0.35   # NASA MCD12Q2
    assert S["min_amplitude_range_years"] == 3 and S["threshold_fraction"] == 0.2
    assert S["held_out_thin_days"] == 16 and S["best_margin"] == 0.02
    assert R["bare_days"]["ndvi_max"] == 0.25


def _one_season(n=250):
    """Bare 0.2 to day 60, straight rise to 0.8 on day 124, straight fall to 0.2 on day 188, bare after."""
    t = np.arange(n)
    return np.interp(t, [0, 60, 124, 188, n - 1], [0.2, 0.2, 0.8, 0.2, 0.2])


def _dates(n, start="2020-01-01"):
    return pd.date_range(start, periods=n)


# ---------- shared ----------

def test_smoothing_keeps_a_parabola_unchanged():
    t = np.arange(101.0)
    y = 0.001 * (t - 50) ** 2
    assert np.allclose(se.smooth(y, 31, 2), y)


def test_smoothing_refuses_gaps():
    with pytest.raises(ValueError, match="gap-free"):
        se.smooth([0.2, np.nan] + [0.3] * 40, 31, 2)


def test_observation_scatter_uses_observation_days_only():
    daily = pd.DataFrame({"ndvi": [0.5, 0.6, 0.7, 0.9], "gap_days": [0, 0, 0, 10]})
    assert se.observation_sigma(daily, [0.5, 0.5, 0.5, 0.5]) == pytest.approx(np.sqrt(0.05 / 3))


# ---------- 1. threshold method ----------

def test_threshold_season_starts_and_ends_at_20_percent_of_the_rise_and_fall():
    """Rise 0.6 over 64 days: 20% (0.32) is passed 12.8 days in, so day 73; the fall stays above 0.32 for 51.2
    days after the peak, so the last day is 175."""
    c = _one_season()
    d = _dates(len(c))
    (s,) = se.threshold_seasons(d, c, 0.2, 0.2)
    assert (s["start"], s["peak"], s["end"]) == (d[73], d[124], d[175])
    assert s["peak_ndvi"] == 0.8


def test_a_bump_under_0_1_is_not_a_season():
    c = np.interp(np.arange(200), [0, 60, 100, 140, 199], [0.2, 0.2, 0.28, 0.2, 0.2])
    assert se.threshold_seasons(_dates(200), c, 0.1, 0.2, 0.35, 3) == []


def test_a_bump_under_35_percent_of_the_range_beside_a_crop_season_is_not_a_season():
    """Range 0.6 in the 3 years around it, so a season needs 0.21: the 0.15 bump fails, the crop passes."""
    c = np.interp(np.arange(500), [0, 60, 124, 188, 300, 340, 380, 499], [0.2, 0.2, 0.8, 0.2, 0.2, 0.35, 0.2, 0.2])
    d = _dates(500)
    (s,) = se.threshold_seasons(d, c, 0.1, 0.2, 0.35, 3)
    assert s["peak"] == d[124]


def test_a_lone_bump_of_0_15_is_a_season_under_the_nasa_rule():
    """0.15 >= 0.1 and >= 35% of its own range (0.15): MCD12Q2's rule counts it; NDVI cannot say it is a crop."""
    c = np.interp(np.arange(200), [0, 60, 100, 140, 199], [0.2, 0.2, 0.35, 0.2, 0.2])
    assert len(se.threshold_seasons(_dates(200), c, 0.1, 0.2, 0.35, 3)) == 1


def test_two_seasons_each_measured_from_their_own_minima():
    """Season 2 starts from a trough at 0.3, not 0.2: its 20% level is 0.3 + 0.2 x 0.5 = 0.4, reached 12.8 days
    into a 64-day rise, so day 160 + 13."""
    c = np.interp(np.arange(400), [0, 40, 100, 160, 224, 288, 399], [0.2, 0.2, 0.8, 0.3, 0.8, 0.2, 0.2])
    d = _dates(400)
    a, b = se.threshold_seasons(d, c, 0.2, 0.2)
    assert a["peak"] == d[100] and b["peak"] == d[224]
    assert b["start"] == d[173]


def test_labels_growing_harvested_and_bare():
    c = _one_season()
    d = _dates(len(c))
    lab = se.labels_from_seasons(d, se.threshold_seasons(d, c, 0.2, 0.2), c, 0.25)
    assert (lab == "growing").sum() == 175 - 73 + 1
    assert lab[0] == "bare" and lab[72] == "harvested" and lab[73] == "growing" and lab[200] == "bare"


# ---------- 2. change-point method ----------

def test_changepoints_find_the_kinks_of_a_clean_series():
    assert se.changepoints(_one_season(), sigma=0.01, params_per_change=2, min_size=5) == [60, 124, 188]


def test_changepoint_season_runs_from_the_kink_where_the_rise_begins_to_the_kink_where_the_fall_ends():
    c = _one_season()
    d = _dates(len(c))
    k = se.changepoints(c, 0.01, 2, 5)
    (s,) = se.changepoint_seasons(d, se.piecewise_linear_fit(c, k), k, 0.2)
    assert (s["start"], s["peak"], s["end"]) == (d[60], d[124], d[188])


def test_a_gently_sloping_floor_does_not_move_the_start():
    """Floor rising 0.20 to 0.22 over 60 days, then the crop: the season starts on day 60, not day 0."""
    t = np.arange(250)
    c = np.interp(t, [0, 60, 124, 188, 249], [0.2, 0.22, 0.8, 0.2, 0.2])
    d = _dates(250)
    (s,) = se.changepoint_seasons(d, c, [60, 124, 188], 0.2)
    assert s["start"] == d[60] and s["end"] == d[188]


def test_piecewise_linear_fit_is_exact_on_a_piecewise_linear_series():
    c = _one_season()
    assert np.allclose(se.piecewise_linear_fit(c, [60, 124, 188]), c)


# ---------- labels to seasons ----------

def test_majority_filter_removes_one_odd_day_and_a_tie_keeps_the_day():
    assert list(se.mode_filter(["bare", "growing", "bare", "bare", "bare"], 3)) == ["bare"] * 5
    assert list(se.mode_filter(["bare", "growing"], 3)) == ["bare", "growing"]


def test_short_growing_runs_are_not_seasons():
    lab = np.array(["bare"] * 10 + ["growing"] * 5 + ["bare"] * 10 + ["growing"] * 40 + ["bare"] * 5, object)
    curve = np.array([0.2] * 25 + list(np.linspace(0.3, 0.8, 40)) + [0.2] * 5)
    d = _dates(len(lab))
    seasons, out = se.seasons_from_labels(d, lab, curve, 0.25, 30)
    assert len(seasons) == 1 and seasons[0]["start"] == d[25] and seasons[0]["end"] == d[64]
    assert seasons[0]["peak"] == d[64] and (out[10:15] == "bare").all()


# ---------- comparison ----------

def test_thinning_keeps_the_first_observation_in_each_16_days_of_the_held_out_year_only():
    days = list(pd.date_range("2020-01-01", "2020-01-31")) + [pd.Timestamp("2019-06-01"), pd.Timestamp("2019-06-02")]
    obs = pd.DataFrame({"date": days, "ndvi": 0.5})
    t = se.thin(obs, 2020, 16)
    assert list(t["date"]) == [pd.Timestamp(x) for x in ("2019-06-01", "2019-06-02", "2020-01-01", "2020-01-17")]


def test_agreement_on_masked_days():
    assert se.agreement(["a", "b", "c"], ["a", "x", "c"]) == pytest.approx(2 / 3)
    assert se.agreement(["a", "b", "c"], ["a", "x", "c"], [True, False, True]) == 1.0


def test_a_method_must_beat_the_threshold_method_by_the_margin():
    assert se.choose_best({"threshold": 0.90, "changepoint": 0.91, "detective": 0.85}, "threshold", 0.02) == "threshold"
    assert se.choose_best({"threshold": 0.90, "changepoint": 0.93, "detective": 0.85}, "threshold", 0.02) == "changepoint"


# ---------- 3. season detective ----------

def test_detective_features_worked_numbers():
    n = 200
    d = _dates(n)
    x = det.features(d, 0.2 + 0.001 * np.arange(n), [2.0] * n, [20.0] * n,
                     slope_days=15, low_window_days=120, weather_days=30)
    assert x["slope_back"].iloc[50] == pytest.approx(0.015) and x["slope_fwd"].iloc[50] == pytest.approx(0.015)
    assert x["days_since_low"].iloc[150] == 119            # rising: the lowest day is the window's first
    assert x["rain_mm_sum"].iloc[100] == 60.0 and x["tmean_c"].iloc[100] == 20.0
    assert np.isnan(x["rain_mm_sum"].iloc[28]) and np.isnan(x["slope_fwd"].iloc[n - 1])


def test_detective_learns_labels_from_two_years_and_labels_a_third():
    one = np.interp(np.arange(365), [0, 60, 124, 188, 240, 300, 364], [0.2, 0.2, 0.8, 0.2, 0.2, 0.7, 0.3])
    curve = np.concatenate([one, one, one])
    d = _dates(len(curve), "2018-01-01")
    rain = np.tile(np.where((np.arange(365) > 150) & (np.arange(365) < 270), 10.0, 0.5), 3)
    temp = np.tile(15 + 8 * np.sin(np.arange(365) / 365 * 2 * np.pi), 3)
    lab = se.labels_from_seasons(d, se.threshold_seasons(d, curve, 0.2, 0.2), curve, 0.25)
    X = det.features(d, curve, rain, temp, 15, 120, 30)
    train = d.year < 2020
    m = det.train(X[train], lab[train], trees=50, min_samples_leaf=5, seed=0)
    pred = det.predict(m, X[~train])
    ok = pd.notna(pred)
    assert se.agreement(pred[ok], lab[~train][ok]) > 0.9
