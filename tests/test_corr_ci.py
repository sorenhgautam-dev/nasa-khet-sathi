"""Shared statistics of the independent checks (rules.yaml validation_checks.common): correlation with a fixed-seed
bootstrap interval, the smallest |r| an n can show, the degenerate-series rule, monthly anomalies. Worked numbers."""
import numpy as np
import pandas as pd
import pytest

from pipeline.checks import corr_ci as cc


def test_pearson_and_spearman_of_a_worked_example():
    # x 1..5, y 2 1 4 3 5: deviations (-2,-1,0,1,2) and (-1,-2,1,0,2), sum of products 8, sums of squares 10 and 10 -> 0.8
    r = cc.correlate([1, 2, 3, 4, 5], [2, 1, 4, 3, 5], n_boot=2000)
    assert r["n"] == 5 and r["pearson"] == pytest.approx(0.8) and r["spearman"] == pytest.approx(0.8)
    lo, hi = r["spearman_ci"]
    assert -1.0 <= lo <= 0.8 <= hi <= 1.0


def test_the_bootstrap_is_fixed_by_its_seed():
    x, y = np.arange(12.0), np.r_[3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8.0]
    assert cc.correlate(x, y)["pearson_ci"] == cc.correlate(x, y)["pearson_ci"]
    assert cc.correlate(x, y, seed=1)["pearson_ci"] != cc.correlate(x, y, seed=0)["pearson_ci"]


def test_a_perfect_line_has_an_interval_of_one():
    r = cc.correlate(np.arange(8.0), 2 * np.arange(8.0) + 1, n_boot=500)
    assert r["pearson_ci"] == [1.0, 1.0] and r["spearman_ci"] == [1.0, 1.0]


def test_block_bootstrap_resamples_whole_blocks():
    # two blocks; any resample is block A twice, B twice, or A+B: the interval holds at most 3 distinct values
    x, y = np.r_[1, 2, 3, 4.0, 5, 6, 7, 8], np.r_[1, 3, 2, 4.0, 8, 6, 7, 5]
    vals = cc.bootstrap(x, y, blocks=[0, 0, 0, 0, 1, 1, 1, 1], n_boot=300, seed=0, method="pearson")
    assert len(np.unique(np.round(vals, 12))) <= 3


def test_the_smallest_detectable_r():
    # t(0.975, 10) = 2.2281: 2.2281 / sqrt(10 + 2.2281^2) = 0.576; n 6: 2.7764 / sqrt(4 + 7.7085) = 0.811
    assert cc.detectable_r(12) == pytest.approx(0.576, abs=1e-3)
    assert cc.detectable_r(6) == pytest.approx(0.811, abs=1e-3)
    assert cc.detectable_r(300) == pytest.approx(0.113, abs=1e-3)


def test_degenerate_when_more_than_half_are_one_value():
    assert cc.is_degenerate([1.0] * 7 + [0.99, 0.98, 0.97, 0.96, 0.95])
    assert not cc.is_degenerate([1.0] * 6 + [0.99, 0.98, 0.97, 0.96, 0.95, 0.94])
    assert cc.is_degenerate([1.0, 0.9999999999, 1.0, 0.5])            # equal to 6 decimals


def test_excludes_zero_on_the_expected_side():
    assert cc.excludes_zero([0.1, 0.8], +1) and not cc.excludes_zero([-0.1, 0.8], +1)
    assert cc.excludes_zero([-0.9, -0.2], -1) and not cc.excludes_zero([0.2, 0.9], -1)


def test_monthly_anomaly_removes_each_calendar_months_mean():
    idx = pd.date_range("2001-01-01", periods=24, freq="MS")
    s = pd.Series(np.r_[np.arange(12.0), np.arange(12.0) + 2], index=idx)
    a = cc.monthly_anomaly(s)
    assert a.iloc[0] == pytest.approx(-1.0) and a.iloc[12] == pytest.approx(1.0)


def test_step_in_standard_deviations():
    idx = pd.date_range("2015-01-01", periods=4, freq="YS")
    s = pd.Series([0.0, 0.0, 1.0, 1.0], index=idx)       # sd 0.5774; step 1.0 -> 1.73
    assert cc.step_sd(s, 2017) == pytest.approx(1.73, abs=0.01)
