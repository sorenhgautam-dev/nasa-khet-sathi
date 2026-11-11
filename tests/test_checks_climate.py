"""Validation layer 3 ("data sensible") summary statistics, checked on made-up series with known answers."""
import pandas as pd
import pytest

from pipeline.checks import climate as c


def _daily(start="2001-01-01", end="2002-12-31", rain=4.0):
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dates, "rain_mm": rain, "tmin_c": dates.month.astype(float),
                         "tmax_c": 20.0 + dates.month})


def test_mean_annual_total_over_complete_years():
    total, years = c.mean_annual_total(_daily(), "rain_mm")
    assert total == pytest.approx(1460.0) and years == [2001, 2002]


def test_an_incomplete_year_is_left_out():
    df = pd.concat([_daily(), _daily("2003-01-01", "2003-01-10", rain=100.0)])
    total, years = c.mean_annual_total(df, "rain_mm")
    assert total == pytest.approx(1460.0) and 2003 not in years


def test_a_year_with_a_missing_day_is_left_out():
    df = _daily()
    df.loc[5, "rain_mm"] = float("nan")
    _, years = c.mean_annual_total(df, "rain_mm")
    assert years == [2002]


def test_share_in_months_all_in_monsoon():
    df = _daily()
    df["rain_mm"] = df["date"].dt.month.isin([6, 7, 8, 9]) * 10.0
    assert c.share_in_months(df, "rain_mm", [6, 7, 8, 9]) == pytest.approx(1.0)


def test_share_in_months_for_even_rain():
    assert c.share_in_months(_daily("2001-01-01", "2001-12-31"), "rain_mm", [6, 7, 8, 9]) == pytest.approx(122 / 365)


def test_month_mean():
    df = _daily()
    assert c.month_mean(df, "tmin_c", [1]) == pytest.approx(1.0)
    assert c.month_mean(df, "tmax_c", [5, 6]) == pytest.approx((31 * 25 + 30 * 26) / 61)  # daily mean, May has 31 days


@pytest.mark.parametrize("value,band,expected", [(1450, (1260, 1650), "PASS"), (1260, (1260, 1650), "PASS"),
                                                 (1200, (1260, 1650), "FAIL"), (1700, (1260, 1650), "FAIL")])
def test_judge(value, band, expected):
    assert c.judge(value, band) == expected
