"""Build step 4: crop coefficient curve, soil-water bucket, runoff and yield. Worked numbers are FAO-56's
printed examples (https://www.fao.org/4/x0490e/x0490e0b.htm Chapter 6; x0490e0e.htm Chapter 8, read
2026-11-12): Example 28 (Kc curve), Example 36 (TAW, RAW), Example 37 (Ks, Dr), Example 39 (Ks).
Validation layer 2 (balance closes, extremes behave) is checked at the end."""
import numpy as np
import pandas as pd
import pytest

from pipeline.twin import crops, runoff, soil_water as sw, yield_

# --- FAO-56 Example 28: dry bean, stages 25/25/30/20 days, Kc 0.15 / 1.19 / 0.35 ---
STAGES = {"ini": 25, "dev": 25, "mid": 30, "late": 20}
KC = {"ini": 0.15, "mid": 1.19, "end": 0.35}


@pytest.mark.parametrize("day,expected", [(20, 0.15), (40, 0.77), (70, 1.19), (95, 0.56)])
def test_kc_curve_example_28(day, expected):
    assert crops.kc_on_day(day, STAGES, KC) == pytest.approx(expected, abs=0.005)


@pytest.mark.parametrize("day,expected", [(12, 0.15), (37, 0.63), (65, 1.14), (90, 0.70)])
def test_kc_curve_example_30(day, expected):
    assert crops.kc_on_day(day, STAGES, {"ini": 0.15, "mid": 1.14, "end": 0.25}) == pytest.approx(expected, abs=0.006)


def test_kc_curve_over_a_season_has_one_value_per_day():
    kc = crops.kc_curve(STAGES, KC)
    assert len(kc) == 100 and kc[0] == pytest.approx(0.15) and kc[-1] == pytest.approx(0.35)


# --- FAO-56 Example 36: TAW and RAW ---
@pytest.mark.parametrize("fc,wp,zr,p,taw,raw", [
    (0.15, 0.06, 0.4, 0.30, 36, 11), (0.32, 0.15, 0.8, 0.40, 136, 54), (0.35, 0.23, 1.2, 0.55, 144, 79)])
def test_taw_and_raw_example_36(fc, wp, zr, p, taw, raw):
    t = sw.taw_mm(fc, wp, zr)
    assert t == pytest.approx(taw, abs=0.5) and p * t == pytest.approx(raw, abs=0.6)


def test_taw_from_soil_layers_weights_by_depth():
    layers = pd.DataFrame({"top_cm": [0, 30], "bottom_cm": [30, 100],
                           "theta_fc_m3m3": [0.30, 0.34], "theta_wp_m3m3": [0.15, 0.20]})
    # 0-0.3 m: 0.15 x 300 mm = 45; 0.3-0.5 m: 0.14 x 200 mm = 28
    assert sw.taw_from_layers(layers, 0.5) == pytest.approx(73.0)


# --- p adjusted for ETc (FAO-56 Table 22 note), limited to 0.1..0.8 ---
@pytest.mark.parametrize("p_tab,etc,expected", [(0.55, 5.0, 0.55), (0.55, 3.0, 0.63), (0.55, 8.0, 0.43),
                                                (0.20, 9.0, 0.10), (0.75, 0.0, 0.80)])
def test_p_adjustment(p_tab, etc, expected):
    assert sw.adjust_p(p_tab, etc) == pytest.approx(expected)


# --- FAO-56 Example 39: Ks for TAW 110, RAW 44 ---
@pytest.mark.parametrize("dr,ks", [(0, 1.0), (44, 1.0), (50, 0.91), (60, 0.76), (80, 0.45), (100, 0.15), (110, 0.0)])
def test_ks_example_39(dr, ks):
    assert sw.ks(dr, 110.0, 44.0) == pytest.approx(ks, abs=0.006)


# --- FAO-56 Example 37: tomato, TAW 160, p 0.40, Dr0 = 55, ETc 6 mm/day, no rain, ten days ---
def test_daily_depletion_example_37():
    dr_end_printed = [61.0, 67.0, 72.8, 78.3, 83.4, 88.2, 92.6, 96.9, 100.8, 104.5]
    dr = 55.0
    for expected in dr_end_printed:
        out = sw.step(dr, rain_mm=0.0, runoff_mm=0.0, irrigation_mm=0.0, etc_mm=6.0, taw_mm=160.0, p=0.40)
        dr = out["dr_mm"]
        assert dr == pytest.approx(expected, abs=0.15)


def test_rain_beyond_field_capacity_becomes_deep_percolation():
    out = sw.step(10.0, rain_mm=30.0, runoff_mm=0.0, irrigation_mm=0.0, etc_mm=4.0, taw_mm=100.0, p=0.5)
    assert out["dr_mm"] == 0.0 and out["dp_mm"] == pytest.approx(16.0) and out["eta_mm"] == pytest.approx(4.0)


# --- SCS curve number runoff (CLAUDE.md) ---
def test_runoff_is_zero_below_initial_abstraction():
    s = 25400 / 80 - 254
    assert runoff.scs_runoff_mm(0.2 * s - 0.1, 80) == 0.0


def test_runoff_equals_rain_for_cn_100():
    assert runoff.scs_runoff_mm(40.0, 100) == pytest.approx(40.0)


def test_runoff_formula_by_hand():
    s = 25400 / 85 - 254
    ia = 0.2 * s
    assert runoff.scs_runoff_mm(60.0, 85) == pytest.approx((60 - ia) ** 2 / (60 - ia + s))


# --- yield as % of potential (FAO-33 form, FAO-56 eq. 90) ---
def test_harvest_pct():
    assert yield_.harvest_pct(80.0, 100.0, 1.15) == pytest.approx(77.0)


def test_harvest_pct_is_clamped_to_0_100():
    assert yield_.harvest_pct(0.0, 100.0, 1.25) == 0.0 and yield_.harvest_pct(100.0, 100.0, 1.0) == 100.0


def test_harvest_pct_needs_a_known_ky():
    with pytest.raises(ValueError, match="Ky"):
        yield_.harvest_pct(80.0, 100.0, None)


def test_only_a_null_ky_gives_no_harvest_number_and_the_assumed_ky_does():
    """REVIEW_NOTES L3: crops with no published Ky carry the owner-assumed 1.0 and get a number; only ky null
    gets none. The text must say so, and must declare that the 0..100 clamp runs FAO-33 past its derived range."""
    with pytest.raises(ValueError) as e:
        yield_.harvest_pct(80.0, 100.0, None)
    assert "null" in str(e.value) and "no published Ky" not in str(e.value)
    assert yield_.harvest_pct(80.0, 100.0, 1.0) == pytest.approx(80.0)      # assumed Ky 1.0: 100 x (1 - 0.2)
    doc = yield_.__doc__
    assert "assumed" in doc and "null" in doc and "no harvest number rather than a guessed one" not in doc
    assert "clamp" in doc and "TODO-VERIFY" in doc


# --- validation layer 2: the balance closes and the extremes behave ---
def _season(rain, et0=5.0, days=120, kc=1.0, taw=150.0, p=0.5):
    df = pd.DataFrame({"rain_mm": rain if np.ndim(rain) else [rain] * days, "et0_mm": et0, "kc": kc})
    return sw.run_bucket(df, taw_mm=taw, p_table=p, cn=80, dr0_mm=0.0)


def test_water_balance_closes_within_1_mm_per_season():
    rng = np.random.default_rng(3)
    rain = rng.gamma(0.5, 12.0, 150) * (rng.random(150) < 0.45)
    out = _season(rain, days=150)
    inflow = (out["rain_mm"] - out["runoff_mm"] + out["irrigation_mm"]).sum()
    outflow = (out["eta_mm"] + out["dp_mm"]).sum()
    change_in_storage = -(out["dr_mm"].iloc[-1] - 0.0)          # depletion down = water stored up
    assert abs(inflow - outflow - change_in_storage) < 1.0


def test_water_balance_closes_with_ponded_paddy_days_counting_the_pond_once_as_irrigation():
    """H1: the pond's water is irrigation water. pond_supply_mm is the paddy part of irrigation_mm, so the
    balance counts irrigation_mm only (counting pond_supply_mm again would leave a residual)."""
    rng = np.random.default_rng(4)
    rain = rng.gamma(0.5, 12.0, 150) * (rng.random(150) < 0.45)
    df = pd.DataFrame({"rain_mm": rain, "et0_mm": 4.0, "kc": 1.1})
    out = sw.run_bucket(df, taw_mm=120.0, p_table=0.2, cn=85, dr0_mm=0.0, ponded=np.arange(150) < 90)
    inflow = (out["rain_mm"] - out["runoff_mm"] + out["irrigation_mm"]).sum()
    outflow = (out["eta_mm"] + out["dp_mm"]).sum()
    assert abs(inflow - outflow + out["dr_mm"].iloc[-1]) < 1e-9
    pond = out["ponded"]
    assert (out.loc[pond, "ks"] == 1.0).all() and not out.loc[pond, "dry_day"].any()
    assert (out.loc[pond, "pond_supply_mm"] == out.loc[pond, "irrigation_mm"]).all()
    assert (out.loc[~pond, "pond_supply_mm"] == 0.0).all() and out["pond_supply_mm"].sum() > 0


def test_a_ponded_day_refills_the_root_zone_at_the_start_of_the_day_so_ks_is_honestly_1():
    """H1 + L1, worked number. Yesterday's depletion 80 mm (TAW 120, p 0.2: RAW 24), no rain, ETc 5 mm.
    The pond refills 80 mm at the start of the day, booked as irrigation; Ks is then taken at Dr = 0, so
    ETa = ETc = 5 mm and the day ends at Dr = 5 mm with no deep percolation. (The old code took Ks at
    Dr = 80, i.e. (120 - 80) / (120 - 24) = 0.417, gave ETa 2.08 mm, reported Ks 1 and booked 2.92 mm as
    deep percolation.)"""
    df = pd.DataFrame({"rain_mm": [0.0], "et0_mm": [5.0], "kc": [1.0]})
    row = sw.run_bucket(df, taw_mm=120.0, p_table=0.2, cn=85, dr0_mm=80.0, ponded=[True]).iloc[0]
    assert row["irrigation_mm"] == pytest.approx(80.0) and row["pond_supply_mm"] == pytest.approx(80.0)
    assert row["ks"] == 1.0 and row["eta_mm"] == pytest.approx(5.0)
    assert row["dr_mm"] == pytest.approx(5.0) and row["dp_mm"] == 0.0


def test_ponded_days_without_rain_refill_yesterdays_water_use():
    """Worked number: Dr0 = 0, three rainless ponded days with ETc 4 mm. Day 1 needs no refill; days 2 and 3
    refill the 4 mm used the day before. Irrigation 0 + 4 + 4 = 8 mm; the season ends at Dr = 4 mm."""
    df = pd.DataFrame({"rain_mm": [0.0] * 3, "et0_mm": [4.0] * 3, "kc": [1.0] * 3})
    out = sw.run_bucket(df, taw_mm=120.0, p_table=0.2, cn=85, dr0_mm=0.0, ponded=[True] * 3)
    assert list(out["irrigation_mm"]) == pytest.approx([0.0, 4.0, 4.0])
    assert out["pond_supply_mm"].sum() == pytest.approx(8.0) and out["dr_mm"].iloc[-1] == pytest.approx(4.0)


def test_sixty_dry_days_give_heavy_stress():
    out = _season(0.0, days=60)
    assert out["ks"].iloc[-1] < 0.3 and (out["ks"] < 1).sum() > 30


def test_steady_rain_gives_no_stress():
    out = _season(6.0, days=120)
    assert (out["ks"] == 1.0).all()


def test_harvest_stays_within_0_and_100_for_any_season():
    for rain in (0.0, 2.0, 30.0):
        out = _season(rain)
        h = yield_.harvest_pct(out["eta_mm"].sum(), out["etc_mm"].sum(), 1.25)
        assert 0.0 <= h <= 100.0


# --- SCS runoff against published values (inches): TR-55 Table 2-1 and NEH 630 Ch. 10 Example 10-1,
# read 2026-11-12. Cases that agree with the exact equation (TR-55 Example 2-4 used a rounded S).
@pytest.mark.parametrize("p_in,cn,q_in", [(1.0, 98, 0.79), (2.0, 90, 1.09), (3.0, 80, 1.25), (4.0, 70, 1.33),
                                         (5.0, 60, 1.30), (6.0, 75, 3.28), (10.0, 85, 8.16), (15.0, 40, 5.33),
                                         (4.3, 74, 1.82), (1.0, 70, 0.00)])
def test_runoff_matches_published_tr55_and_neh_values(p_in, cn, q_in):
    assert runoff.scs_runoff_mm(p_in * 25.4, cn) / 25.4 == pytest.approx(q_in, abs=0.006)


# --- sowing date = middle of the crop's default calendar window (rules.yaml crop_calendar) ---
def test_sow_date_is_the_middle_of_the_window():
    cal = {"windows": [{"sow": "10-15", "sow_end": "11-15"}], "default": 0}
    assert crops.sow_date(cal, 2015) == pd.Timestamp("2015-10-30")


def test_sow_date_for_a_window_crossing_the_new_year():
    cal = {"windows": [{"sow": "12-20", "sow_end": "01-09"}], "default": 0}
    assert crops.sow_date(cal, 2015) == pd.Timestamp("2015-12-30")


def test_irrigation_refills_at_the_start_of_the_day_so_the_crop_is_not_stressed():
    """CLAUDE.md: refill when Dr > RAW. The refill happens before the day's water use, so Ks stays 1."""
    df = pd.DataFrame({"rain_mm": [0.0] * 40, "et0_mm": [5.0] * 40, "kc": [1.0] * 40})
    out = sw.run_bucket(df, taw_mm=100.0, p_table=0.5, cn=83, dr0_mm=0.0, irrigate=True)
    assert (out["ks"] == 1.0).all() and not out["dry_day"].any()
    first = out.index[out["irrigation_mm"] > 0][0]
    assert out.loc[first, "irrigation_mm"] == pytest.approx(out.loc[first - 1, "dr_mm"])
    assert out.loc[first - 1, "dr_mm"] > out.loc[first - 1, "raw_mm"]


# --- step 7 may sow at the window's start, middle or end (owner's batch decisions item 10, 2026-11-12) ---
def test_sow_date_at_the_start_and_end_of_the_window():
    cal = {"windows": [{"sow": "10-15", "sow_end": "11-15"}], "default": 0}
    assert crops.sow_date(cal, 2015, position="start") == pd.Timestamp("2015-10-15")
    assert crops.sow_date(cal, 2015, position="middle") == pd.Timestamp("2015-10-30")
    assert crops.sow_date(cal, 2015, position="end") == pd.Timestamp("2015-11-15")


def test_sow_date_end_crosses_the_new_year():
    cal = {"windows": [{"sow": "12-20", "sow_end": "01-09"}], "default": 0}
    assert crops.sow_date(cal, 2015, position="end") == pd.Timestamp("2016-01-09")


def test_sow_date_refuses_an_unknown_position():
    cal = {"windows": [{"sow": "10-15", "sow_end": "11-15"}], "default": 0}
    with pytest.raises(ValueError, match="position"):
        crops.sow_date(cal, 2015, position="early")


# --- build step 2a: FAO-56 surface-layer evaporation on bare days (rules.yaml bare_soil; twin/evaporation.py) ---
SURF = {"tew_mm": 20.0, "rew_mm": 9.0, "kc_max": 1.20, "de0_mm": 0.0}


def _bare(rain, et0=4.5):
    return pd.DataFrame({"rain_mm": rain, "et0_mm": et0, "kc": np.nan})


def test_bare_surface_layer_evaporation_leaves_the_root_zone_and_stops_near_tew():
    """Worked number (FAO-56 eqs. 71-74 with Kcb = 0, few = 1, Kc max 1.20, TEW 20, REW 9, ETo 4.5, no rain): day 1 and
    2 E = 1.2 x 4.5 = 5.40 mm (stage 1, De 5.40 then 10.80); day 3 Kr = (20 - 10.80) / 11 = 0.836, E = 4.52 mm. The
    root zone loses the same water, with Ks 1 (no transpiration, no stress); over 10 days less than TEW in all."""
    out = sw.run_bucket(_bare([0.0] * 10), taw_mm=150.0, p_table=0.2, cn=91, dr0_mm=30.0, surface=SURF)
    assert list(out["eta_mm"].iloc[:3]) == pytest.approx([5.40, 5.40, 4.5164], abs=1e-4)
    assert list(out["de_mm"].iloc[:3]) == pytest.approx([5.40, 10.80, 15.3164], abs=1e-4)
    assert (out["ks"] == 1.0).all() and not out["dry_day"].any() and (out["irrigation_mm"] == 0.0).all()
    assert out["eta_mm"].sum() == pytest.approx(out["de_mm"].iloc[-1]) and out["eta_mm"].sum() < 20.0
    assert out["dr_mm"].iloc[-1] == pytest.approx(30.0 + out["eta_mm"].sum())
    assert (out["etc_mm"] == out["eta_mm"]).all()                       # bare soil: ETc = Ke ETo (Example 31, col. 8)


def test_bare_rain_wets_the_surface_layer_and_the_root_zone_and_the_balance_closes():
    rng = np.random.default_rng(7)
    rain = rng.gamma(0.5, 12.0, 120) * (rng.random(120) < 0.3)
    out = sw.run_bucket(_bare(rain, et0=5.0), taw_mm=150.0, p_table=0.2, cn=91, dr0_mm=40.0, surface={**SURF, "de0_mm": 20.0})
    inflow = (out["rain_mm"] - out["runoff_mm"]).sum()
    assert abs(inflow - (out["eta_mm"] + out["dp_mm"]).sum() - (40.0 - out["dr_mm"].iloc[-1])) < 1e-9
    de_prev = np.r_[20.0, out["de_mm"].to_numpy()[:-1]]               # eq. 77 day by day
    assert np.allclose(out["de_mm"], de_prev - (out["rain_mm"] - out["runoff_mm"]) + out["eta_mm"] + out["dpe_mm"])
    assert ((out["de_mm"] >= 0) & (out["de_mm"] <= 20.0)).all()


def test_bare_evaporation_stops_where_the_root_zone_reaches_the_wilting_point():
    out = sw.run_bucket(_bare([0.0] * 5), taw_mm=100.0, p_table=0.2, cn=91, dr0_mm=97.0, surface=SURF)
    assert out["dr_mm"].max() <= 100.0 and out["eta_mm"].sum() == pytest.approx(3.0)
    assert out["de_mm"].iloc[-1] == pytest.approx(3.0)                  # the layer lost only what the bucket gave


def test_the_bare_surface_path_refuses_irrigation_and_a_pond():
    with pytest.raises(ValueError, match="bare"):
        sw.run_bucket(_bare([0.0] * 3), taw_mm=100.0, p_table=0.2, cn=91, irrigate=True, surface=SURF)
    with pytest.raises(ValueError, match="bare"):
        sw.run_bucket(_bare([0.0] * 3), taw_mm=100.0, p_table=0.2, cn=91, ponded=[True] * 3, surface=SURF)
