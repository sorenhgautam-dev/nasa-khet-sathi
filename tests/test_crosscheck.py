"""Cross-checks between sources (validation layer 3), on made-up series with known answers."""
import pandas as pd
import pytest

from pipeline.checks import crosscheck as x


def _days(start, end, value):
    d = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": d, "rain_mm": value})


def test_complete_month_totals_keep_only_full_months():
    jan = _days("2015-01-01", "2015-01-31", 1.0)
    feb = _days("2015-02-01", "2015-02-27", 1.0)          # 27 of 28 days: incomplete
    totals = x.complete_month_totals(pd.concat([jan, feb]), "rain_mm")
    assert list(totals.index.astype(str)) == ["2015-01"] and totals.iloc[0] == pytest.approx(31.0)


def test_a_month_with_a_missing_value_is_incomplete():
    jan = _days("2015-01-01", "2015-01-31", 1.0)
    jan.loc[3, "rain_mm"] = float("nan")
    assert x.complete_month_totals(jan, "rain_mm").empty


def test_compare_reports_bias_correlation_error_and_count():
    ref = pd.Series([10.0, 20.0, 30.0], index=pd.period_range("2015-01", periods=3, freq="M"))
    other = ref * 1.1
    r = x.compare(ref, other)
    assert r["n"] == 3 and r["bias_pct"] == pytest.approx(10.0)
    assert r["r"] == pytest.approx(1.0) and r["mae"] == pytest.approx(2.0)


def test_compare_uses_only_shared_periods():
    ref = pd.Series([10.0, 20.0], index=pd.period_range("2015-01", periods=2, freq="M"))
    other = pd.Series([10.0, 99.0], index=pd.period_range("2014-12", periods=2, freq="M"))
    assert x.compare(ref, other)["n"] == 1


def test_paired_difference_on_shared_days():
    a = pd.DataFrame({"date": pd.date_range("2015-01-01", periods=3), "tmin_c": [0.0, 1.0, None]})
    b = pd.DataFrame({"date": pd.date_range("2015-01-02", periods=3), "tmin_c": [4.0, 5.0, 6.0]})
    r = x.paired_difference(a, b, "tmin_c")
    assert r["n"] == 1 and r["mean_diff"] == pytest.approx(3.0)  # only 2015-01-02 has both
