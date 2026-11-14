"""pipeline/sections/attributes.py (build step 8): each section's HLS greenness by area weights, the pre-declared
'usually greener' test, and low ground from NASADEM (rules.yaml `sections`). Worked numbers first."""
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.sections import attributes as at

GRID = (30.0, 0.0, 0.0, 0.0, -30.0, 90.0)      # 30 m pixels, x 0..90 east, y 90..0 north (rows go south)


def _w(ws):
    return {(w["row"], w["col"]): round(w["weight"], 6) for w in ws}


def test_pixel_weights_worked_numbers():
    # a 30 m square centred on the corner of four pixels: a quarter in each
    sq = [(15, 45), (45, 45), (45, 75), (15, 75)]
    assert _w(at.pixel_weights(sq, GRID, (3, 3))) == {(0, 0): 0.25, (0, 1): 0.25, (1, 0): 0.25, (1, 1): 0.25}
    # exactly one pixel
    assert _w(at.pixel_weights([(0, 60), (30, 60), (30, 90), (0, 90)], GRID, (3, 3))) == {(0, 0): 1.0}
    # 10 m east of the grid: 20 x 30 in the first pixel, 10 x 30 in the next, largest first
    ws = at.pixel_weights([(10, 60), (40, 60), (40, 90), (10, 90)], GRID, (3, 3))
    assert _w(ws) == {(0, 0): round(2 / 3, 6), (0, 1): round(1 / 3, 6)}
    assert ws[0]["row"] == 0 and ws[0]["col"] == 0


def test_pixel_weights_refuse_a_section_outside_the_raster():
    with pytest.raises(ValueError, match="outside"):
        at.pixel_weights([(80, 60), (100, 60), (100, 90), (80, 90)], GRID, (3, 3))


def test_a_section_observation_is_the_weighted_mean_of_its_clear_pixels():
    r = at.section_observation([0.5, 0.8, np.nan], [True, True, True], [0.6, 0.3, 0.1], 0.75)
    assert r["clear_share"] == pytest.approx(0.9) and r["ndvi"] == pytest.approx((0.6 * 0.5 + 0.3 * 0.8) / 0.9)
    r = at.section_observation([0.5, 0.8, 0.7], [False, True, True], [0.6, 0.3, 0.1], 0.75)
    assert r["clear_share"] == pytest.approx(0.4) and r["ndvi"] is None          # under 75% of the area is clear
    r = at.section_observation([0.5, 0.8, 0.7], [True, True, False], [0.6, 0.15, 0.25], 0.75)
    assert r["clear_share"] == pytest.approx(0.75) and r["ndvi"] == pytest.approx((0.3 + 0.12) / 0.75)   # 75% counts


def test_weighted_mean():
    assert at.weighted_mean([0.2, 0.4, 0.6, 0.8], [1, 1, 1, 1]) == pytest.approx(0.5)
    assert at.weighted_mean([0.2, 0.6], [3, 1]) == pytest.approx(0.3)
    assert at.weighted_mean([0.2, None], [1, 1]) is None


def test_season_peaks_follow_the_smoothed_curve_and_need_enough_images():
    days = pd.date_range("2020-01-01", "2020-12-31", freq="5D")
    t = (days - pd.Timestamp("2020-07-01")).days.to_numpy()
    ndvi = 0.8 - 0.6 * (t / 120.0) ** 2                                      # a smooth season peaking at 0.8 on 1 July
    seasons = [{"start": pd.Timestamp("2020-04-01"), "end": pd.Timestamp("2020-10-01")},
               {"start": pd.Timestamp("2020-12-22"), "end": pd.Timestamp("2020-12-25")}]   # no image inside
    r = at.season_peaks(days, ndvi, seasons, 31, 2, 3)
    assert r[0]["obs"] == 36 and r[0]["peak"] == pytest.approx(0.8, abs=0.005)
    assert r[1]["obs"] == 0 and r[1]["peak"] is None


def test_sign_test_worked_numbers():
    r = at.sign_test([0.1] * 9 + [-0.2])
    assert (r["n"], r["positive"], r["negative"], r["zeros"]) == (10, 9, 1, 0)
    assert r["p"] == pytest.approx(2 * 11 / 1024)                              # 0.021484375
    assert at.sign_test([0.01] * 8 + [0.0])["p"] == pytest.approx(2 / 256)   # the zero is left out: n = 8
    assert at.sign_test([1, -1, 1, -1])["p"] == 1.0
    from scipy.stats import binomtest
    assert at.sign_test([1] * 14 + [-1] * 6)["p"] == pytest.approx(binomtest(14, 20, 0.5).pvalue)


def test_holm_worked_numbers():
    assert at.holm([0.01, 0.04, 0.03, 0.2], 0.05) == [True, False, False, False]    # 0.03 > 0.05 / 3: stop
    assert at.holm([0.001, 0.01, 0.02, 0.04], 0.05) == [True, True, True, True]
    assert at.holm([0.02, 0.5], 0.05) == [True, False]                               # 0.02 <= 0.05 / 2
    assert at.holm([0.03, 0.5], 0.05) == [False, False]                              # 0.03 > 0.05 / 2


def test_median_interval_from_order_statistics():
    lo, hi, cover = at.median_ci(list(range(10, 0, -1)), 0.95)
    assert (lo, hi) == (2, 9) and cover == pytest.approx(1 - 2 * 11 / 1024)        # 0.978515625
    assert at.median_ci([1, 2, 3, 4, 5], 0.95) is None                              # 1 - 2/32 = 0.9375 < 0.95


def test_fewest_seasons_that_could_ever_pass_holm():
    assert at.min_decidable_n(0.05, 4) == 8           # 2 x 0.5^7 = 0.0156 > 0.0125; 2 x 0.5^8 = 0.0078
    assert at.min_decidable_n(0.05, 1) == 6           # 2 x 0.5^5 = 0.0625; 2 x 0.5^6 = 0.03125


def test_the_size_floor_is_the_published_same_day_difference_times_the_field_peak():
    """Owner, 2026-11-14: 'a little greener' only above the satellite's normal noise. Ju et al. 2025: same-day L30/S30
    vegetation-index difference below 4.5%; the floor in NDVI is 4.5% of the field's median season peak."""
    assert at.size_floor([0.8, 0.9, 0.85], 0.045) == pytest.approx(0.03825)
    assert at.size_floor([0.8, None, 0.9], 0.045) == pytest.approx(0.045 * 0.85)
    assert at.size_floor([], 0.045) is None


def test_usually_words_by_the_owners_rule():
    """greener / less green need BOTH the sign test (Holm) AND |median| above the floor; otherwise 'same'."""
    an = {"s1": [0.01] * 12,                           # steady (p 0.00049, rejected) but tiny: same
          "s2": [0.04] * 12,                           # steady and above the floor: greener
          "s3": [-0.06] * 12,                          # steady and below: less green
          "s4": [0.2, -0.2] * 6}                       # no steady sign: same
    r = at.usually(an, alpha=0.05, level=0.95, floor_ndvi=0.03825)
    assert r["s1"]["holm_rejected"] is True and r["s1"]["above_floor"] is False and r["s1"]["word"] == "same"
    assert r["s2"]["word"] == "greener" and r["s3"]["word"] == "less green"
    assert r["s4"]["word"] == "same" and r["s4"]["holm_rejected"] is False
    assert r["s2"]["ci"] == [0.04, 0.04]
    few = at.usually({"s1": [0.1] * 7, "s2": [-0.1] * 7, "s3": [0.0] * 7, "s4": [0.01] * 7}, 0.05, 0.95, 0.03825)
    assert all(v["word"] == "can't tell" and v["decidable"] is False for v in few.values())   # 7 < 8: no test possible


def test_tpi_worked_numbers():
    dem = np.full((5, 5), 10.0)
    dem[2, 2] = 0.0
    r = at.tpi_at(dem, 2, 2, 1.0, 1.0, 1.0)            # the pixel and its four neighbours
    assert r["n"] == 5 and r["mean_m"] == pytest.approx(8.0) and r["tpi_m"] == pytest.approx(-8.0)
    assert r["sd_m"] == pytest.approx(4.0)            # sqrt(((0 - 8)^2 + 4 x (10 - 8)^2) / 5)
    with pytest.raises(ValueError, match="circle"):
        at.tpi_at(dem, 0, 2, 1.0, 1.0, 1.0)
    # 30 x 27 m pixels, 500 m: every centre within 500 m counts
    big = np.zeros((41, 41))
    r = at.tpi_at(big, 20, 20, 27.35, 30.89, 500.0)
    want = sum(1 for i in range(-20, 21) for j in range(-20, 21) if (i * 30.89) ** 2 + (j * 27.35) ** 2 <= 500.0 ** 2)
    assert r["n"] == want and r["tpi_m"] == 0.0


def test_low_ground_needs_a_tpi_larger_than_the_dem_error():
    assert at.low_ground(-8.0, 4.0, -1.0, 7.0) is True         # valley class, beyond the DEM's error
    assert at.low_ground(-3.0, 1.0, -1.0, 7.0) is None         # within NASADEM's error: can't tell
    assert at.low_ground(-8.0, 10.0, -1.0, 7.0) is False       # lower than around, but not by 1 SD
    assert at.low_ground(8.0, 4.0, -1.0, 7.0) is False
    assert at.low_ground(math.nan, 4.0, -1.0, 7.0) is None
