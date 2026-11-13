"""GPM break correction (owner's decision 1, 2026-11-13; rules.yaml gpm_series): scale IMERG Final rain from
2017-01-01 month by month back to GPM's own 2001-2016 level, keep the uncorrected rain beside it. Worked numbers."""
import numpy as np
import pandas as pd
import pytest

from pipeline.checks import rain_check as rc
from pipeline.fetch.rules import load_rules
from pipeline.twin import inputs


def _daily(per_day_by_period, start="2015-01-01", end="2018-12-31"):
    """Constant daily rain: {(first_year, last_year): mm per day}."""
    d = pd.date_range(start, end)
    v = np.zeros(len(d))
    for (a, b), mm in per_day_by_period.items():
        v[(d.year >= a) & (d.year <= b)] = mm
    return pd.Series(v, index=d)


def test_the_rules():
    G = load_rules()["gpm_series"]
    assert G["correction_reference_years"] == [2001, 2016] and G["correction_from"] == "2017-01-01"
    assert G["correction_products"] == ["final", "late"]            # owner's answer 7 to REVIEW_2, 2026-11-13
    assert G["correction_factor_products"] == ["final"]             # Late days never set a factor


def test_complete_month_totals_skip_months_with_a_missing_day():
    s = _daily({(2015, 2018): 1.0})
    s["2016-02-10"] = np.nan
    t = inputs.complete_month_totals(s)
    assert t[(2015, 1)] == 31.0 and t[(2016, 3)] == 31.0
    assert (2016, 2) not in t.index and len(t) == 47


def test_factor_is_the_reference_mean_over_the_later_mean_per_calendar_month():
    """1 mm a day in 2015-2016, 2 mm a day in 2017-2018: each month's factor is 31/62 = 0.5, except February:
    (28 + 29) / 2 = 28.5 mm before (2016 is a leap year) over 56 mm after = 0.509."""
    f = inputs.break_factors(_daily({(2015, 2016): 1.0, (2017, 2018): 2.0}), (2015, 2016), "2017-01-01")
    assert f[2] == pytest.approx(28.5 / 56) and all(f[m] == pytest.approx(0.5) for m in range(1, 13) if m != 2)


def test_a_month_missing_from_either_period_fails_loudly():
    s = _daily({(2015, 2016): 1.0, (2017, 2018): 2.0})
    s[s.index.month == 7] = np.nan
    with pytest.raises(ValueError, match="Jul"):
        inputs.break_factors(s, (2015, 2016), "2017-01-01")


def test_only_masked_days_from_the_start_are_scaled():
    """Final days from 2017 are halved; 2016 and the days the mask leaves out (Late, POWER fill) stay as they are."""
    s = _daily({(2015, 2016): 1.0, (2017, 2018): 2.0})
    mask = pd.Series(True, index=s.index)
    mask["2018-10-01":] = False                                   # e.g. IMERG Late days
    out, applied = inputs.apply_break_correction(s, {m: 0.5 for m in range(1, 13)}, "2017-01-01", mask)
    assert out["2016-12-31"] == 1.0 and out["2017-01-01"] == 1.0 and out["2018-09-30"] == 1.0
    assert out["2018-10-01"] == 2.0 and not applied[s.index.get_loc(pd.Timestamp("2018-10-01"))]
    assert int(applied.sum()) == 365 + 273


def test_the_twin_can_switch_between_the_two_rains():
    w = pd.DataFrame({"date": pd.date_range("2017-01-01", periods=2), "rain_mm": [1.0, 2.0],
                      "rain_uncorrected_mm": [2.0, 4.0]})
    assert list(inputs.with_rain(w, "uncorrected")["rain_mm"]) == [2.0, 4.0]
    assert list(inputs.with_rain(w, "corrected")["rain_mm"]) == [1.0, 2.0]
    with pytest.raises(ValueError, match="rain version"):
        inputs.with_rain(w, "station")


def test_held_out_check_fits_on_odd_years_tests_on_even_and_the_reverse():
    """GPM 1 mm/day before 2017 and 2 after; the station 1 mm/day throughout: the raw post-2017 error is a month's
    total, the corrected error 0, and the ratio to the station 2 -> 1."""
    g = rc.complete_month_totals(_daily({(2015, 2016): 1.0, (2017, 2020): 2.0}, end="2020-12-31"))
    st = rc.complete_month_totals(_daily({(2015, 2020): 1.0}, end="2020-12-31"))
    r = rc.holdout_break_correction(g, st, (2015, 2016), 2017)
    assert r["months"] == 48 and r["ratio_raw"] == pytest.approx(2.0)
    assert r["ratio_corrected"] == pytest.approx(1.0, abs=0.001)        # leap-year Februaries: 1.0007
    assert r["mae_corrected_mm"] < 0.1 and r["mae_raw_mm"] == pytest.approx(1461 / 48)
