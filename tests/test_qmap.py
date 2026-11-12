"""Owner decision (step-3 review 1, 2026-11-12): empirical quantile mapping for cold nights, per month
or per season when a month has too few days, judged against the monthly offset on held-out years by
three numbers: mean absolute error, each January's coldest night, and nights below 2 C."""
import numpy as np
import pandas as pd
import pytest

from pipeline.twin import qmap as q

SEASONS = {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "JJAS": [6, 7, 8, 9], "ON": [10, 11]}
YEARS = [2015, 2016, 2017, 2019, 2021, 2022]


def _pair(transform, years=YEARS, seed=0):
    """POWER nights are milder than the station's: the station = transform(POWER)."""
    rng = np.random.default_rng(seed)
    dates = pd.DatetimeIndex([d for d in pd.date_range("2015-01-01", "2022-12-31") if d.year in years])
    doy = dates.day_of_year.to_numpy()
    power = 9 + 7 * np.sin(2 * np.pi * (doy - 100) / 365) + rng.normal(0, 1.5, len(dates))
    station = np.array([transform(p, d) for p, d in zip(power, dates)])
    pw = pd.DataFrame({"date": dates, "tmin_c": power})
    st = pd.DataFrame({"date": dates, "tmin_c": station})
    return pw, st


def _shared(pw, st):
    from pipeline.twin.bias import shared_days
    return shared_days(pw, st, "tmin_c")


def test_mapping_follows_a_linear_relation_inside_the_fitted_range():
    pw, st = _pair(lambda p, d: 1.8 * p - 6)
    models = q.fit_qmap(_shared(pw, st), YEARS, "tmin_c", SEASONS, min_days=20, n_quantiles=99)
    probe = pd.DataFrame({"date": pd.to_datetime(["2020-01-10"]), "tmin_c": [3.0]})
    assert q.apply_qmap(probe, "tmin_c", models).iloc[0] == pytest.approx(1.8 * 3.0 - 6, abs=0.3)


def test_values_beyond_the_fitted_range_keep_the_end_difference():
    pw, st = _pair(lambda p, d: p - 4)
    models = q.fit_qmap(_shared(pw, st), YEARS, "tmin_c", SEASONS, min_days=20, n_quantiles=99)
    m = models[1]
    probe = pd.DataFrame({"date": pd.to_datetime(["2020-01-10"]), "tmin_c": [m["power_q"][0] - 10]})
    expected = probe["tmin_c"].iloc[0] + (m["station_q"][0] - m["power_q"][0])
    assert q.apply_qmap(probe, "tmin_c", models).iloc[0] == pytest.approx(expected)


def test_a_month_with_too_few_days_uses_its_season():
    pw, st = _pair(lambda p, d: p - 4)
    st = st[~((st["date"].dt.month == 1) & (st["date"].dt.day > 2))]           # January: 2 days a year
    models = q.fit_qmap(_shared(pw, st), YEARS, "tmin_c", SEASONS, min_days=20, n_quantiles=99)
    assert models[1]["basis"] == "season DJF" and models[2]["basis"] == "month"


def test_a_season_with_too_few_days_gets_no_correction():
    pw, st = _pair(lambda p, d: p - 4)
    st = st[~st["date"].dt.month.isin([10, 11])]
    models = q.fit_qmap(_shared(pw, st), YEARS, "tmin_c", SEASONS, min_days=20, n_quantiles=99)
    assert models[10] is None
    probe = pd.DataFrame({"date": pd.to_datetime(["2020-10-10"]), "tmin_c": [12.0]})
    assert q.apply_qmap(probe, "tmin_c", models).iloc[0] == 12.0


def test_cold_night_scores_on_a_hand_example():
    dates = pd.to_datetime(["2016-01-01", "2016-01-02", "2016-07-01", "2019-01-05"])
    station = pd.Series([-1.0, 3.0, 18.0, 0.5])
    corrected = pd.Series([0.0, 1.5, 19.0, 2.5])
    s = q.cold_night_scores(dates, station, corrected, frost_c=2.0)
    assert s["mae"] == pytest.approx((1 + 1.5 + 1 + 2) / 4)
    assert s["jan_coldest_error"] == pytest.approx((abs(0.0 - -1.0) + abs(2.5 - 0.5)) / 2)   # 2016 and 2019
    assert s["nights_below"] == {"station": 2, "corrected": 2, "abs_diff": 0}


def test_quantile_mapping_wins_when_power_nights_are_too_mild_in_the_tails():
    pw, st = _pair(lambda p, d: 1.8 * p - 6)          # wider spread at the station than in POWER
    c = q.compare_cold_night_methods(pw, st, "tmin_c", SEASONS, min_days_per_year=200, min_days=20,
                                     n_quantiles=99, frost_c=2.0)
    assert set(c["qmap_better_on"]) == {"mae", "jan_coldest_error", "nights_below_abs_diff"}
    for key in ("mae", "jan_coldest_error", "nights_below_abs_diff"):
        assert c["qmap"][key] < c["offset"][key]


def test_the_comparison_reports_where_quantile_mapping_does_not_win():
    pw, st = _pair(lambda p, d: p - 4)                # a pure shift: the offset is already right
    c = q.compare_cold_night_methods(pw, st, "tmin_c", SEASONS, min_days_per_year=200, min_days=20,
                                     n_quantiles=99, frost_c=2.0)
    assert len(c["qmap_better_on"]) < 3


def test_quantile_mapping_models_are_always_returned_for_frost():
    """Owner, step-4 review item 1 (2026-11-12): quantile mapping is used for frost whatever the comparison says."""
    pw, st = _pair(lambda p, d: p - 4)
    c = q.compare_cold_night_methods(pw, st, "tmin_c", SEASONS, min_days_per_year=200, min_days=20,
                                     n_quantiles=99, frost_c=2.0)
    assert c["qmap_models"] is not None and c["qmap_models"][1] is not None


def test_the_comparison_refuses_when_there_are_no_held_out_years():
    pw, st = _pair(lambda p, d: p - 4)
    one_year = pw["date"].dt.year == pw["date"].dt.year.min()
    with pytest.raises(ValueError, match="held-out"):
        q.compare_cold_night_methods(pw[one_year], st[one_year], "tmin_c", SEASONS, min_days_per_year=200,
                                     min_days=20, n_quantiles=99, frost_c=2.0)
