"""Owner decision D (after D6): GPM IMERG is the twin's rain; POWER only fills GPM gaps, never with
2001-2003 values, and every filled day is flagged."""
import numpy as np
import pandas as pd
import pytest

from pipeline.twin.inputs import merge_rain

NEVER = [2001, 2002, 2003]


def _series(dates, values):
    return pd.Series(values, index=pd.DatetimeIndex(dates), dtype=float)


DATES = pd.to_datetime(["2002-07-01", "2010-05-01", "2010-05-02"])


def test_primary_is_used_where_it_has_a_value():
    out = merge_rain(DATES, _series(DATES, [5.0, 6.0, 7.0]), _series(DATES, [1.0, 1.0, 1.0]), NEVER)
    assert list(out["rain_mm"]) == [5.0, 6.0, 7.0]
    assert set(out["rain_source"]) == {"gpm"} and not out["rain_filled"].any()


def test_a_gap_is_filled_from_the_fallback_and_flagged():
    out = merge_rain(DATES, _series(DATES, [5.0, np.nan, 7.0]), _series(DATES, [1.0, 3.0, 1.0]), NEVER)
    row = out.set_index("date").loc[pd.Timestamp("2010-05-01")]
    assert row["rain_mm"] == 3.0 and row["rain_source"] == "power_fill" and row["rain_filled"]


def test_never_fill_from_2001_to_2003():
    out = merge_rain(DATES, _series(DATES, [np.nan, 6.0, 7.0]), _series(DATES, [12.0, 1.0, 1.0]), NEVER)
    row = out.set_index("date").loc[pd.Timestamp("2002-07-01")]
    assert np.isnan(row["rain_mm"]) and row["rain_source"] == "missing" and not row["rain_filled"]


def test_without_any_primary_there_is_no_rain_at_all():
    out = merge_rain(DATES, None, _series(DATES, [1.0, 2.0, 3.0]), NEVER)
    assert out["rain_mm"].isna().all() and set(out["rain_source"]) == {"missing"}


def test_a_gap_with_no_fallback_stays_missing():
    out = merge_rain(DATES, _series(DATES, [5.0, np.nan, 7.0]), _series(DATES, [1.0, np.nan, 1.0]), NEVER)
    assert out.set_index("date").loc[pd.Timestamp("2010-05-01"), "rain_source"] == "missing"


# REVIEW_NOTES M2 (2026-11-12): rules.yaml power_rain.max_filled_fraction_per_year (0.05). A partly failed GPM
# download must not turn into POWER rain unnoticed: the weather table fails loudly above the cap.

from pipeline.twin.inputs import fill_by_year, fill_cap_breaches  # noqa: E402


def _merged(year_days, gaps, never=()):
    """GPM on every day of `year_days` except `gaps`; POWER everywhere."""
    d = pd.DatetimeIndex(year_days)
    gpm = _series(d, np.where(d.isin(pd.DatetimeIndex(gaps)), np.nan, 2.0))
    return merge_rain(d, gpm, _series(d, np.ones(len(d))), list(never))


def test_filled_days_are_counted_per_year_inside_the_gpm_record():
    days = pd.date_range("2018-01-01", "2019-12-31")
    gaps = list(pd.date_range("2018-03-01", periods=18)) + list(pd.date_range("2019-07-01", periods=19))
    f = fill_by_year(_merged(days, gaps))
    assert f["primary_record"] == ["2018-01-01", "2019-12-31"]
    assert f["by_year"][2018] == {"days": 365, "filled": 18, "missing": 0, "fraction_filled": pytest.approx(18 / 365)}
    assert f["by_year"][2019]["filled"] == 19 and f["filled_outside_primary_record"] == 0


def test_a_year_above_five_percent_filled_breaches_the_cap_and_one_at_18_days_does_not():
    """Worked number: 18 / 365 = 0.0493 <= 0.05 passes; 19 / 365 = 0.0521 > 0.05 fails."""
    days = pd.date_range("2018-01-01", "2019-12-31")
    gaps = list(pd.date_range("2018-03-01", periods=18)) + list(pd.date_range("2019-07-01", periods=19))
    br = fill_cap_breaches(fill_by_year(_merged(days, gaps))["by_year"], 0.05)
    assert [b["year"] for b in br] == [2019]
    assert br[0]["filled"] == 19 and br[0]["fraction_filled"] == pytest.approx(0.0521, abs=1e-4)


def test_fill_outside_the_gpm_record_is_counted_separately_not_against_the_cap():
    """simulate.rain_record_problems already refuses POWER standing in beyond GPM's own record."""
    days = pd.date_range("2018-01-01", "2019-12-31")
    gaps = list(pd.date_range("2019-11-01", "2019-12-31"))               # GPM ends 2019-10-31
    f = fill_by_year(_merged(days, gaps))
    assert f["primary_record"] == ["2018-01-01", "2019-10-31"]
    assert f["filled_outside_primary_record"] == 61
    assert f["by_year"][2019] == {"days": 304, "filled": 0, "missing": 0, "fraction_filled": 0.0}
    assert fill_cap_breaches(f["by_year"], 0.05) == []


def test_never_fill_years_count_as_missing_not_filled():
    days = pd.date_range("2002-01-01", "2002-12-31")
    f = fill_by_year(_merged(days, list(pd.date_range("2002-07-01", periods=30)), never=NEVER))
    assert f["by_year"][2002]["filled"] == 0 and f["by_year"][2002]["missing"] == 30


def test_without_gpm_there_is_no_record_to_count():
    f = fill_by_year(merge_rain(DATES, None, _series(DATES, [1.0, 2.0, 3.0]), NEVER))
    assert f == {"primary_record": None, "by_year": {}, "filled_outside_primary_record": 0}
