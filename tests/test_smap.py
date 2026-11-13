"""SMAP cleaning (REVIEW_2 Phase 3, 2026-11-13): pipeline/fetch/smap.py. Worked examples for the pure parts:
which 9 km cell holds the field, the quality flag, the valid range, and the daily mean of the 3-hourly L4 values."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import smap
from pipeline.fetch.guards import DataGuardError

# cell centres of the demo box as AppEEARS delivers them (EASE-Grid 2.0 Global, EPSG:6933, metres)
XS = [8237851.67983862, 8246859.72983862]
YS = [3400542.38922696, 3391534.33922696]


def test_the_demo_field_lies_in_the_north_east_cell():
    assert smap.ease2_cell(XS, YS, lon=85.441792, lat=27.690767) == (0, 1)


def test_a_point_outside_every_cell_is_refused():
    with pytest.raises(DataGuardError, match="outside"):
        smap.ease2_cell(XS, YS, lon=86.5, lat=27.69)


def test_recommended_quality_is_bit_0_clear():
    # AppEEARS's own lookup table for this box: 7, 9 and 13 all read "doesn't have recommended quality"
    assert smap.recommended([0, 8, 7, 9, 13]).tolist() == [True, True, False, False, False]


def test_l3_keeps_only_recommended_values_and_counts_what_it_drops():
    values = np.array([0.20, -9999.0, 0.31, 0.561, 0.25], dtype="float32")
    flags = np.array([0, 7, 9, 13, 8])
    clean, n = smap.clean_l3(values, flags, fill=-9999.0, valid_range=(0.02, 0.5))
    assert np.allclose(clean[[0, 4]], [0.20, 0.25]) and np.isnan(clean[[1, 2, 3]]).all()
    assert n == {"fill": 1, "not_recommended_quality": 1, "not_recommended_and_out_of_range": 1, "kept": 2}


def test_a_recommended_value_outside_the_products_range_fails_loudly():
    with pytest.raises(DataGuardError):
        smap.clean_l3(np.array([0.561]), np.array([0]), fill=-9999.0, valid_range=(0.02, 0.5))


def test_l4_daily_mean_needs_all_eight_values_of_the_utc_day():
    t = pd.date_range("2018-01-01 01:30", periods=16, freq="3h")
    v = np.r_[np.full(8, 0.30), np.full(8, 0.20)]
    daily, incomplete = smap.daily_mean(t, v)
    assert daily.index.tolist() == [pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-02")]
    assert daily.tolist() == pytest.approx([0.30, 0.20]) and incomplete == 0
    daily, incomplete = smap.daily_mean(t[:-1], v[:-1])
    assert np.isnan(daily.iloc[1]) and incomplete == 1


def test_monthly_anomalies_remove_each_calendar_months_own_mean():
    idx = pd.date_range("2016-01-01", "2017-12-31", freq="D")
    s = pd.Series(np.where(idx.year == 2016, 1.0, 3.0) + idx.month, index=idx)     # a seasonal cycle plus a step
    a = smap.monthly_anomaly(s)
    assert len(a) == 24 and a[a.index.year == 2016].tolist() == pytest.approx([-1.0] * 12)
    assert a[a.index.year == 2017].tolist() == pytest.approx([1.0] * 12)
