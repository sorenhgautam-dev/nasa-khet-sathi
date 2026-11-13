"""Rain check B (owner's upgrade list item 1, 2026-11-13): monthly climatology against DHM's 1991-2020 normals and
the Pettitt change-point test. Worked examples for pipeline/checks/rain_check.py."""
import numpy as np
import pandas as pd
import pytest

from pipeline.checks import rain_check as rc


def test_dhm_normals_load_with_a_source_for_every_number():
    n = rc.load_normals()
    assert set(n["station"]) == {"Kathmandu Airport", "Bhaktapur", "Changu Narayan", "Nagarkot"}
    air = rc.station_months(n, "Kathmandu Airport", "precip_mm")
    assert air[7] == 384.1 and round(sum(air.values()), 1) == 1502.0          # the printed annual normal
    printed = n[n["value"].notna()]                                          # DHM prints no annual value for some
    assert printed["document"].notna().all() and printed["page"].notna().all()


def test_monthly_climatology_uses_complete_months_only():
    days = pd.date_range("2019-01-01", "2020-02-29")
    s = pd.Series(1.0, index=days)
    s["2020-01-10"] = np.nan                                                  # January 2020 is incomplete
    c = rc.monthly_climatology(s)
    assert c.loc[1, "mean_mm"] == 31.0 and c.loc[1, "years"] == 1
    assert c.loc[2, "mean_mm"] == pytest.approx((28 + 29) / 2) and c.loc[2, "years"] == 2
    assert c.loc[3, "mean_mm"] == 31.0 and c.loc[3, "years"] == 1          # March 2019 only


def test_pettitt_finds_a_step_and_its_year():
    """Ten years at 1.0 then ten at 2.0: U at the step is the largest possible, 10 x 10 = 100, and the change
    point is the last year before the step."""
    years = list(range(2001, 2021))
    x = [1.0] * 10 + [2.0] * 10
    r = rc.pettitt(years, x)
    assert r["k"] == 100 and r["change_after"] == 2010
    assert r["p"] == pytest.approx(2 * np.exp(-6 * 100 ** 2 / (20 ** 3 + 20 ** 2)))   # 0.0016


def test_pettitt_on_a_series_without_a_step_is_not_significant():
    rng = np.random.default_rng(0)
    r = rc.pettitt(list(range(2001, 2026)), rng.normal(size=25))
    assert r["p"] > 0.05


def test_step_ratio_compares_the_years_after_a_break_with_the_years_before():
    """Final 1,000 mm a year in 2014-2016 and 1,500 after; Late 1,100 throughout: Final steps by 1.5, Late by 1.0."""
    final = {2014: 1000.0, 2015: 1000.0, 2016: 1000.0, 2017: 1500.0, 2018: 1500.0, 2019: 1500.0}
    late = {y: 1100.0 for y in final}
    assert rc.step_ratio(final, 2017) == pytest.approx(1.5) and rc.step_ratio(late, 2017) == pytest.approx(1.0)


def test_rain_against_gauges_sums_the_months_before_dividing():
    """REVIEW_2 Phase 3: a rain series against the mean of nearby gauges, month by month (DHM's 2025 bulletins)."""
    from pipeline.checks.rain_check import ratio_to_gauges
    gauges = {"2025-08": [400.0, 500.0, 300.0], "2025-09": [200.0, 300.0, 100.0], "2025-12": [0.0, 0.0, 0.0]}
    rain = {"2025-08": 500.0, "2025-09": 100.0, "2025-12": 12.0, "2025-07": 999.0}       # July has no gauge value
    r = ratio_to_gauges(rain, gauges)
    assert r["months"] == ["2025-08", "2025-09", "2025-12"]
    assert r["gauge_mean_mm"] == 600.0 and r["rain_mm"] == 612.0 and r["ratio"] == 1.02
    assert r["by_month"]["2025-12"] == {"rain_mm": 12.0, "gauge_mean_mm": 0.0, "ratio": None}
