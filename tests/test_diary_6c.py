"""Build step 6c (CLAUDE.md "Field diary"): groundwater trend, trends, monthly calendar and rotation guess.
Worked examples for pipeline/diary/groundwater.py, trends.py, months.py and guess.py."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import groundwater as gw
from pipeline.diary import guess as gu
from pipeline.diary import months as mo
from pipeline.diary import trends as tr
from pipeline.fetch.rules import load_rules

R = load_rules()


# ---------- groundwater (GRACE/GRACE-FO mascons, D7) ----------

def _grace(slope_cm_per_year, years=range(2003, 2013), drop=()):
    t = pd.period_range(f"{min(years)}-01", f"{max(years)}-12", freq="M")
    yr = np.arange(len(t)) / 12.0
    v = slope_cm_per_year * yr + np.tile(10 * np.sin(2 * np.pi * np.arange(12) / 12), len(t) // 12)   # exact repeats
    s = pd.Series(v, index=t)
    for p in drop:
        s[pd.Period(p, "M")] = np.nan
    return s


def test_a_steady_fall_is_found_with_its_slope():
    r = gw.trend(_grace(-1.2), alpha=0.05)
    assert r["trend_cm_per_year"] == pytest.approx(-1.2) and r["p"] < 0.001
    assert gw.direction(r["trend_cm_per_year"], r["p"], 0.05) == "falling"
    assert gw.confidence(r["p"]) == 1.0


def test_no_trend_is_steady_with_low_confidence():
    r = gw.trend(_grace(0.0), alpha=0.05)
    assert r["trend_cm_per_year"] == pytest.approx(0.0, abs=1e-12)
    assert gw.direction(r["trend_cm_per_year"], r["p"], 0.05) == "steady" and gw.confidence(r["p"]) == 0.0


def test_a_gap_of_missing_months_is_allowed():
    s = _grace(0.8, drop=[f"2007-{m:02d}" for m in range(7, 13)] + ["2008-01"])
    r = gw.trend(s, alpha=0.05)
    assert r["trend_cm_per_year"] == pytest.approx(0.8) and gw.direction(r["trend_cm_per_year"], r["p"], 0.05) == "rising"
    assert r["n_months"] == 120 - 7


def test_monthly_series_averages_two_solutions_in_a_month_and_marks_missing_months():
    s = gw.monthly_series(pd.to_datetime(["2002-04-17", "2002-06-10", "2002-06-25"]), [1.0, 2.0, 4.0])
    assert list(s.index.astype(str)) == ["2002-04", "2002-05", "2002-06"]
    assert np.isnan(s.iloc[1]) and s.iloc[2] == 3.0


# ---------- trends (Mann-Kendall with Sen's slope) ----------

def test_sen_slope_and_its_range_on_a_straight_line():
    r = tr.mk_sen({y: 2.0 * (y - 2001) for y in range(2001, 2026)}, alpha=0.05)
    assert r["slope_per_year"] == pytest.approx(2.0) and r["low"] == pytest.approx(2.0) and r["high"] == pytest.approx(2.0)
    assert r["p"] < 0.001 and r["n"] == 25


def test_years_without_a_value_are_left_out():
    r = tr.mk_sen({2001: 1.0, 2002: None, 2003: 3.0, 2004: 4.0, 2005: 5.0}, alpha=0.05)
    assert r["n"] == 4 and r["slope_per_year"] == pytest.approx(1.0)


def test_change_over_the_record_is_the_slope_times_the_years_between_first_and_last():
    assert tr.over_record({"slope_per_year": -0.5, "low": -1.0, "high": 0.25}, 2001, 2025) == (-12.0, -24.0, 6.0)


def _days(start, end):
    return pd.date_range(start, end)


def test_longest_dry_spell_per_year_counts_days_under_1_mm():
    d = _days("2020-01-01", "2021-12-31")
    rain = pd.Series(5.0, index=d)
    rain["2020-03-01":"2020-03-12"] = 0.5            # 12 days under 1 mm
    rain["2021-07-01":"2021-07-03"] = 0.0
    out = tr.longest_dry_spell(rain, wet_mm=1.0)
    assert out == {2020: 12, 2021: 3}


def test_heavy_rain_days_are_days_of_20_mm_or_more():
    d = _days("2020-01-01", "2020-12-31")
    rain = pd.Series(0.0, index=d)
    rain[["2020-07-01", "2020-07-02", "2020-08-01"]] = [20.0, 19.9, 55.0]
    assert tr.heavy_rain_days(rain, mm=20.0) == {2020: 2}


def test_hot_days_exceed_the_calendar_day_90th_percentile():
    """Ten years with the same seasonal Tmax, except one hot week in 2015: those 7 days are the hot days of
    2015; in other years no day exceeds its own calendar-day threshold by construction."""
    d = _days("2011-01-01", "2020-12-31")
    base = 25 + 5 * np.sin(2 * np.pi * (d.dayofyear - 100) / 365.0)
    noise = np.where(d.year % 2 == 0, -0.1, 0.1)               # small spread so the 90th percentile is defined
    t = pd.Series(base + noise, index=d)
    t["2015-06-01":"2015-06-07"] += 5.0
    out = tr.hot_days(t, base_years=(2011, 2020), pct=90, window_days=5)
    assert out[2015] >= 7 and out[2015] == max(out.values())


# ---------- monthly calendar ----------

def test_pinned_onset_years_count_from_each_years_own_search_start():
    """REVIEW_2 M10: 17 May is day 138 in a leap year and 137 otherwise; both are 2 days after 15 May."""
    doy = {2007: 154, 2008: 138, 2009: 137, 2010: 135, 2011: 138, 2012: None}     # 2011: 18 May, not pinned
    assert tr.pinned_years(doy, "05-15", within_days=2) == 3


def test_a_trend_is_also_given_without_the_years_named_as_faulty():
    """REVIEW_2 H8: POWER's 2001-2003 are far too hot, so the hot-day trend is shown without them as well."""
    counts = [96, 139, 113, 21, 34, 34, 8, 5, 60, 66, 8, 50, 14, 14, 21, 37, 54, 26, 33, 12, 20, 10, 24, 25, 7]        # the demo field's hot days, 2001-2025 (data/checks/demo/diary.json, 2026-11-13)
    vals = dict(zip(range(2001, 2026), counts))
    full = tr.mk_sen(vals, 0.05)
    rest = tr.mk_sen(tr.without_years(vals, [2001, 2002, 2003]), 0.05)
    assert full["p"] == pytest.approx(0.033, abs=0.001) and full["slope_per_year"] == pytest.approx(-1.66, abs=0.01)
    assert rest["first"] == 2004 and rest["n"] == 22
    assert rest["p"] == pytest.approx(0.46, abs=0.01) and rest["slope_per_year"] == pytest.approx(-0.47, abs=0.01)


def test_terciles_give_four_months_to_each_word():
    vals = [10, 20, 30, 80, 150, 300, 400, 350, 250, 60, 15, 5]
    w = mo.tercile_words(vals, ("low", "medium", "high"))
    assert w == ["low", "low", "medium", "medium", "medium", "high", "high", "high", "high", "medium", "low", "low"]


def test_frost_band_from_the_coldest_night():
    assert [mo.frost_band(x, 0.0, 2.0) for x in (-0.2, 0.0, 1.9, 2.0, 5.0)] == ["high", "risk", "risk", "none", "none"]


def test_frost_band_per_year_month_and_per_calendar_month():
    d = _days("2010-01-01", "2012-12-31")
    t = pd.Series(10.0, index=d)
    t["2010-01-12"] = -0.2
    t["2011-01-05"] = 1.0
    t["2012-01-09"] = -1.0
    ym = mo.coldest_by_month(t)
    assert ym[(2010, 1)] == -0.2 and mo.frost_band(ym[(2010, 1)], 0.0, 2.0) == "high"
    cal = mo.frost_by_calendar_month(ym, 0.0, 2.0)
    assert cal[1] == "high" and cal[7] == "none"           # median coldest January night -0.2


def test_cover_word_is_the_most_common_label_of_the_month():
    d = _days("2020-01-01", "2020-02-29")
    lab = pd.Series(["growing"] * 20 + ["bare"] * 11 + ["harvested"] * 29, index=d)
    assert mo.cover_by_month(lab) == {1: "crop", 2: "partial"}


# ---------- rotation guess ----------

LIB = {
    "rice": {"stages_days": {"ini": 22, "dev": 22, "mid": 44, "late": 22},
             "calendar": {"windows": [{"sow": "06-01", "sow_end": "07-15", "harvest": "10-01", "harvest_end": "11-15", "days": [120, 135]}]}},
    "wheat": {"stages_days": {"ini": 18, "dev": 29, "mid": 58, "late": 35},
              "calendar": {"windows": [{"sow": "11-15", "sow_end": "12-15", "harvest": "04-01", "harvest_end": "05-15", "days": [135, 150]}]}},
    "potato": {"stages_days": {"ini": 25, "dev": 30, "mid": 30, "late": 30},
               "calendar": {"windows": [{"sow": "10-15", "sow_end": "11-15", "harvest": "02-15", "harvest_end": "03-15", "days": [100, 120]}]}},
}


def test_window_distance_is_zero_inside_and_days_outside():
    lo, hi = pd.Timestamp("2020-06-01"), pd.Timestamp("2020-06-30")
    assert gu.distance_days(pd.Timestamp("2020-06-15"), lo, hi) == 0
    assert gu.distance_days(pd.Timestamp("2020-07-10"), lo, hi) == 10
    assert gu.distance_days(pd.Timestamp("2020-05-25"), lo, hi) == 7


def test_a_season_is_compared_with_green_up_after_the_initial_stage_harvest_and_length():
    """Wheat sown 15 Nov to 15 Dec turns green 18 days later (3 Dec to 2 Jan); harvest 1 Apr to 15 May; detected
    length should be 135-150 days minus the 18-day initial stage = 117-132 days."""
    s = {"start": pd.Timestamp("2020-01-07"), "end": pd.Timestamp("2020-05-20")}
    d = gu.season_fit(s, LIB["wheat"])
    assert d == {"start": 5, "end": 5, "length": 3, "total": 13}     # 7 Jan vs 2 Jan; 20 May vs 15 May; 135 vs 132


def test_the_guess_takes_the_crop_with_the_smallest_median_distance_per_slot():
    seasons = [{"start": pd.Timestamp(f"{y}-01-05"), "peak": pd.Timestamp(f"{y}-03-15"), "end": pd.Timestamp(f"{y}-05-15")}
               for y in (2018, 2019, 2020)] + \
              [{"start": pd.Timestamp(f"{y}-06-25"), "peak": pd.Timestamp(f"{y}-08-20"), "end": pd.Timestamp(f"{y}-10-25")}
               for y in (2018, 2019, 2020)]
    g = gu.guess(seasons, LIB, crops=["rice", "wheat", "potato"])
    assert g["guess"] == ["rice", "wheat"]
    assert g["slots"]["winter"]["fit"]["wheat"]["median_total"] < g["slots"]["winter"]["fit"]["potato"]["median_total"]
