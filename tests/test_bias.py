"""Owner decision A: a monthly correction of POWER temperature from days shared with a nearby station,
fitted on half the station's qualifying years and tested on the other half."""
import numpy as np
import pandas as pd
import pytest

from pipeline.twin import bias as b

YEARS = [2015, 2016, 2017, 2019, 2021, 2022]


def _pair(offset_by_month, years=YEARS, col="tmin_c"):
    dates = pd.DatetimeIndex([d for d in pd.date_range("2015-01-01", "2022-12-31") if d.year in years])
    station = 10 + 8 * np.sin(2 * np.pi * dates.day_of_year / 365)
    offset = np.array([offset_by_month(d.year, d.month) for d in dates])
    st = pd.DataFrame({"date": dates, col: station})
    pw = pd.DataFrame({"date": dates, col: station + offset})
    return pw, st


def test_shared_days_keep_only_days_where_both_have_a_value():
    pw, st = _pair(lambda y, m: 1.0)
    st.loc[0, "tmin_c"] = np.nan
    assert len(b.shared_days(pw, st, "tmin_c")) == len(st) - 1


def test_qualifying_years_need_enough_shared_days():
    pw, st = _pair(lambda y, m: 1.0)
    st = st[~((st["date"].dt.year == 2016) & (st["date"].dt.month > 3))]   # 2016 keeps only Jan-Mar
    assert b.qualifying_years(b.shared_days(pw, st, "tmin_c"), min_days=200) == [2015, 2017, 2019, 2021, 2022]


def test_split_alternates_years():
    assert b.split_years([2015, 2016, 2017, 2019, 2021]) == ([2015, 2017, 2021], [2016, 2019])


def test_fit_recovers_the_monthly_offsets():
    pw, st = _pair(lambda y, m: 3.8 if m == 1 else 1.0)
    off = b.fit_monthly_offsets(b.shared_days(pw, st, "tmin_c"), YEARS, min_days_per_month=20)
    assert off[1]["offset"] == pytest.approx(3.8) and off[7]["offset"] == pytest.approx(1.0)
    assert off[1]["n"] == 31 * len(YEARS)


def test_a_month_with_too_few_days_gets_no_correction():
    pw, st = _pair(lambda y, m: 2.0)
    st = st[~((st["date"].dt.month == 2) & (st["date"].dt.day > 3))]
    off = b.fit_monthly_offsets(b.shared_days(pw, st, "tmin_c"), YEARS, min_days_per_month=20)
    assert off[2]["offset"] is None and off[2]["n"] == 3 * len(YEARS)


def test_apply_subtracts_each_month_offset_without_touching_the_input():
    df = pd.DataFrame({"date": pd.to_datetime(["2020-01-05", "2020-02-05"]), "tmin_c": [7.0, 9.0]})
    before = df.copy()
    out = b.apply_offsets(df, "tmin_c", {1: {"offset": 3.8, "n": 100}, 2: {"offset": None, "n": 5}})
    assert list(out) == pytest.approx([3.2, 9.0])
    pd.testing.assert_frame_equal(df, before)


def test_evaluate_reports_error_before_and_after():
    pw, st = _pair(lambda y, m: 3.0)
    shared = b.shared_days(pw, st, "tmin_c")
    off = b.fit_monthly_offsets(shared, YEARS, 20)
    r = b.evaluate(shared, YEARS, off, "tmin_c")
    assert r["mae_before"] == pytest.approx(3.0) and r["mae_after"] == pytest.approx(0.0, abs=1e-9)
    assert r["bias_before"] == pytest.approx(3.0) and r["n"] == len(shared)


def test_build_correction_splits_tests_and_refits_on_all_years():
    pw, st = _pair(lambda y, m: 3.8 if m == 1 else 0.5)
    c = b.build_correction(pw, st, "tmin_c", min_days_per_year=200, min_days_per_month=20)
    assert c["fit_years"] == [2015, 2017, 2021] and c["test_years"] == [2016, 2019, 2022]
    assert c["test"]["mae_after"] < c["test"]["mae_before"] and c["apply"] is True
    assert c["offsets"][1]["offset"] == pytest.approx(3.8)          # final fit uses all qualifying years


def test_build_correction_is_not_applied_when_it_does_not_help_on_held_out_years():
    pw, st = _pair(lambda y, m: 2.0 if y in (2015, 2017, 2021) else -2.0)
    c = b.build_correction(pw, st, "tmin_c", min_days_per_year=200, min_days_per_month=20)
    assert c["apply"] is False


def test_months_without_an_offset_are_listed_so_they_can_be_reported_loudly():
    """REVIEW_NOTES M8: a month with no fitted offset passes through uncorrected; say which months."""
    pw, st = _pair(lambda y, m: 2.0)
    st = st[~((st["date"].dt.month.isin([2, 11])) & (st["date"].dt.day > 3))]
    off = b.fit_monthly_offsets(b.shared_days(pw, st, "tmin_c"), YEARS, min_days_per_month=20)
    assert b.months_without_offset(off) == [2, 11]
    assert b.months_without_offset({m: {"offset": 1.0, "n": 99} for m in range(1, 13)}) == []
