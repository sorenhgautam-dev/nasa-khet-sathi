"""The gauge evidence behind the 2017 rain break (REVIEW_2 M6, 2026-11-13): pipeline/fetch/gauge_evidence.py.
Worked examples for the pure parts: grid indices and the summary that rules.yaml gpm_series.break_evidence quotes."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import gauge_evidence as ge
from pipeline.fetch.guards import DataGuardError


def test_imerg_index_of_the_demo_field():
    # 0.1 deg grid from -180 and -90: the cell 85.4-85.5 E, 27.6-27.7 N
    assert ge.imerg_index(lon=85.441792, lat=27.690767) == (2654, 1176)


def test_gpcc_box_is_the_one_degree_box_holding_the_point():
    lats, lons = np.arange(89.5, -90, -1.0), np.arange(-179.5, 180, 1.0)
    i, j = ge.gpcc_box(lats, lons, lat=27.690767, lon=85.441792)
    assert (lats[i], lons[j]) == (27.5, 85.5)
    with pytest.raises(DataGuardError):
        ge.gpcc_box(lats[:10], lons, lat=27.69, lon=85.44)          # a file that does not reach the field


def test_summary_gives_the_ranges_before_and_after_the_break():
    months = pd.period_range("2015-01", "2018-12", freq="M")
    w = np.where(months.year < 2017, 96.5, np.where(months.year == 2017, 62.0, 70.0))
    n = np.where(months.year < 2017, 50.0, 1.0)
    t = pd.DataFrame({"month": months.astype(str), "imerg_gauge_weight_pct": w, "gpcc_stations": n})
    s = ge.summarise(t, break_from="2017-01", gpcc_before_years=2)
    assert s["gauge_weight_before_pct"] == [96.5, 96.5] and s["gauge_weight_after_yearly_pct"] == [62.0, 70.0]
    assert s["gauge_weight_first_month_below_90"] == "2017-01"
    assert s["gpcc_stations_before"] == 50.0 and s["gpcc_stations_after"] == 1.0
    assert s["months"] == {"before": 24, "after": 24}


def test_summary_leaves_out_months_without_a_value():
    t = pd.DataFrame({"month": ["2016-12", "2017-01", "2017-02"], "imerg_gauge_weight_pct": [97.0, np.nan, 60.0],
                      "gpcc_stations": [40.0, 1.0, np.nan]})
    s = ge.summarise(t, break_from="2017-01", gpcc_before_years=1)
    assert s["gauge_weight_after_yearly_pct"] == [60.0, 60.0] and s["gpcc_stations_after"] == 1.0
