"""pipeline/checks/rain_selection.py: choosing the central rain version on gauges it never saw, and DHM's year classes
(rules.yaml verification.rain_selection, verification.year_order). Worked numbers by hand."""
import math

import pandas as pd
import pytest

from pipeline.checks import rain_selection as rs


def test_season_factors_are_ratios_of_sums_and_skip_missing_gauges():
    # June-September: (100 + 200) / (200 + 200) = 0.75 (August has no gauge value, so its 500 mm is left out);
    # the other months: (10 + 30) / (20 + 60) = 0.5
    f = rs.season_factors([6, 7, 8, 1, 2], [100, 200, float("nan"), 10, 30], [200, 200, 500, 20, 60])
    assert f == {"jjas": pytest.approx(0.75), "other": pytest.approx(0.5)}


def test_calibrate_uses_the_season_factor():
    assert list(rs.calibrate([6, 1], [400, 80], {"jjas": 0.75, "other": 0.5})) == [300, 40]


def test_judged_scores_months_of_at_least_10_mm_within_19_percent():
    hit, al = rs.judged([119, 81, 120, 5, 50], [100, 100, 100, 100, 9], tol=0.19, min_mm=10)
    assert list(hit) == [True, True, False, False]          # +19 %, -19 %, +20 %, -95 %; the 9 mm month is not scored
    assert list(al) == pytest.approx([math.log(1.19), -math.log(0.81), math.log(1.2), -math.log(0.05)])
    s = rs.summary(hit, al)
    assert (s["k"], s["n"], s["share"]) == (2, 4, 0.5)
    assert s["median_abs_log"] == pytest.approx((math.log(1.2) - math.log(0.81)) / 2, abs=1e-4)   # 0.1965
    assert s["ci95"] == pytest.approx([0.150, 0.850], abs=1e-3)    # Wilson, 2 of 4


def test_leave_one_gauge_out_fits_on_the_other_gauges_only():
    # Corrected rain: July 200 mm, January 50 mm. Gauges A and B read half of it, C all of it.
    t = pd.DataFrame({"station": list("AABBCC"), "month": [7, 1] * 3, "gauge_mm": [100, 25, 100, 25, 200, 50],
                      "corrected": [200, 50] * 3, "published": [400, 100] * 3, "dhm_scaled": [100, 25] * 3})
    per, pooled = rs.leave_one_gauge_out(t, tol=0.19, min_mm=10)
    assert per["C"]["factors"] == {"jjas": 0.5, "other": 0.5}         # (100 + 100) / 400 and (25 + 25) / 100
    assert per["A"]["factors"] == {"jjas": 0.75, "other": 0.75}       # (100 + 200) / 400 and (25 + 50) / 100
    assert per["C"]["gauge_calibrated"]["k"] == 0                    # 100 and 25 mm against 200 and 50 mm
    assert pooled["corrected"]["k"] == 2 and pooled["corrected"]["n"] == 6     # right only at C
    assert pooled["dhm_scaled"]["k"] == 4                            # right at A and B
    assert pooled["gauge_calibrated"]["k"] == 0 and pooled["published"]["k"] == 0
    assert rs.winner(pooled) == "dhm_scaled"


@pytest.mark.parametrize("cal_median,expected", [(0.05, "gauge_calibrated"), (0.15, "dhm_scaled")])
def test_winner_tie_goes_to_lower_median_and_calibration_must_beat_the_best(cal_median, expected):
    pooled = {"published": {"share": 0.5, "median_abs_log": 0.3}, "corrected": {"share": 0.6, "median_abs_log": 0.2},
              "dhm_scaled": {"share": 0.6, "median_abs_log": 0.1},
              "gauge_calibrated": {"share": 0.6, "median_abs_log": cal_median}}
    assert rs.winner(pooled) == expected


@pytest.mark.parametrize("pct,cls", [(89.9, "below"), (90, "near"), (110, "near"), (110.1, "above"),
                                     (float("nan"), None)])
def test_dhm_class_bands(pct, cls):
    assert rs.dhm_class(pct) == cls


def test_year_order_spearman_classes_and_2023():
    years = range(2019, 2024)
    ours = pd.Series([1000, 1200, 800, 1100, 1400], index=years)        # mean 1,100 mm: 90.9, 109.1, 72.7, 100, 127.3 %
    ref = pd.Series([95, 105, 80, 112, 130], index=years)               # % of normal
    r = rs.year_order(ours, ref, n_boot=200)
    assert r["n"] == 5 and r["spearman"] == pytest.approx(0.9)          # ranks 2,4,1,3,5 against 2,3,1,4,5: 1 - 6*2/120
    assert r["class_agreement"]["k"] == 4 and r["class_agreement"]["n"] == 5   # 2022: near (100 %) against above (112 %)
    assert r["2023"] == {"ours": {"rank": 1, "of": 5, "pct": 127.3, "class": "above"},
                         "dhm": {"rank": 1, "of": 5, "pct": 130.0, "class": "above"}}
