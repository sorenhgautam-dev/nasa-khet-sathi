"""Bare-soil evaporation from the surface layer only, FAO-56 Chapter 7 (Allen et al. 1998), eqs. 71-79
(https://www.fao.org/4/x0490e/x0490e0c.htm, read 2026-11-14). Worked numbers are FAO-56's printed examples:
Example 31 (bare loam, ten drying days after heavy rain: every printed column) and Example 35 (Kc max, TEW, and
days 1-2 of its daily table: the surface-layer balance with a wetting at the start of the day and deep percolation
from the layer). Example 35's later rows are not used: they are not consistent with themselves as printed (day 3:
E 2.8 mm and Kc 1.04, while its own Ke 0.62 x ETo 3.9 = 2.4 mm and Kcb 0.32 + Ke 0.62 = 0.94).
Texture class: SSSA Glossary of Soil Science Terms (2022), 'soil texture', p. 115."""
import pandas as pd
import pytest

from pipeline.twin import evaporation as ev

# --- FAO-56 Example 31: bare loam, Kcb 0.15, Kc max 1.20, few 1, TEW 20, REW 9, ETo 4.5 mm/day, De = 0 at the start,
# no rain. Printed per day: De start, Kr, Ke, Ke ETo, De end, ETc = (Kcb + Ke) ETo.
EX31 = [(0.00, 1.00, 1.05, 4.73, 4.73, 5.4), (4.73, 1.00, 1.05, 4.73, 9.45, 5.4),
        (9.45, 0.96, 1.01, 4.53, 13.98, 5.2), (13.98, 0.55, 0.57, 2.59, 16.57, 3.3),
        (16.57, 0.31, 0.33, 1.47, 18.04, 2.1), (18.04, 0.18, 0.19, 0.84, 18.88, 1.5),
        (18.88, 0.10, 0.11, 0.48, 19.36, 1.2), (19.36, 0.06, 0.06, 0.27, 19.64, 0.9),
        (19.64, 0.03, 0.03, 0.16, 19.79, 0.8), (19.79, 0.02, 0.02, 0.09, 19.88, 0.8)]


def test_example_31_bare_loam_ten_drying_days_every_printed_column():
    de = 0.0
    for day, (de0, kr, ke, e, de1, etc) in enumerate(EX31, start=1):
        d = ev.surface_day(de, et0_mm=4.5, p_minus_ro_mm=0.0, tew_mm=20.0, rew_mm=9.0, kc_max=1.20, kcb=0.15, few=1.0)
        assert d["de_start_mm"] == pytest.approx(de0, abs=0.006), day
        assert d["kr"] == pytest.approx(kr, abs=0.006), day
        assert d["ke"] == pytest.approx(ke, abs=0.006), day
        assert d["e_mm"] == pytest.approx(e, abs=0.006), day
        assert d["de_mm"] == pytest.approx(de1, abs=0.006), day
        assert (0.15 + d["ke"]) * 4.5 == pytest.approx(etc, abs=0.051), day
        de = d["de_mm"]


def test_kr_is_1_up_to_rew_and_falls_to_0_at_tew():                       # eq. 74
    assert ev.kr(9.0, 20.0, 9.0) == 1.0 and ev.kr(0.0, 20.0, 9.0) == 1.0
    assert ev.kr(9.45, 20.0, 9.0) == pytest.approx((20 - 9.45) / 11)     # Example 31, day 3
    assert ev.kr(20.0, 20.0, 9.0) == 0.0


def test_ke_is_limited_by_the_exposed_and_wetted_fraction():              # eq. 71, Example 34
    assert ev.ke(1.0, 1.30, 0.90, 0.19) == pytest.approx(0.19 * 1.30)    # min(0.40, 0.25) = 0.25
    assert ev.ke(1.0, 1.20, 0.0, 1.0) == pytest.approx(1.20)             # bare soil: Ke = Kc max


# --- FAO-56 Example 35: sandy loam, theta_fc 0.23, theta_wp 0.10, Ze 0.1 m; h 0.3 m, u2 1.6 m/s, RHmin 35 % ---
def test_example_35_kc_max_eq_72():
    assert ev.kc_max(u2_ms=1.6, rhmin_pct=35.0, h_m=0.3, kcb=0.30) == pytest.approx(1.21, abs=0.005)


def test_kc_max_is_at_least_kcb_plus_0_05():
    assert ev.kc_max(u2_ms=2.0, rhmin_pct=45.0, h_m=1.0, kcb=1.25) == pytest.approx(1.30)


def test_kc_max_for_bare_soil_is_1_20_in_any_climate():
    """h = 0 (no plants): the climate term of eq. 72, multiplied by (h/3)^0.3, is zero (Example 31: 1.20)."""
    for u2, rh in ((1.0, 90.0), (2.0, 45.0), (5.0, 20.0)):
        assert ev.kc_max(u2_ms=u2, rhmin_pct=rh, h_m=0.0, kcb=0.0) == pytest.approx(1.20)


def test_example_35_tew_eq_73():
    assert ev.tew_mm(0.23, 0.10, 0.1) == pytest.approx(18.0)


def test_example_35_days_1_and_2_wetting_at_the_start_of_the_day():
    """Day 1: 40 mm irrigation at the start of the day, fw 0.8 (I/fw 50 mm) on a layer at TEW (18 mm): De start 0,
    Kr 1.00, Ke 0.91, E/few 5.1, DPe 32 (eq. 79), De end 5, E 4.1, Kc 1.21, ETc 5.5. Day 2: ETo 5.0, Kcb 0.31:
    De start 5, Kr 1.00, Ke 0.90, E/few 5.6, DPe 0, De end 11, E 4.5, ETc 6.1 (printed to their precision)."""
    kcm = ev.kc_max(u2_ms=1.6, rhmin_pct=35.0, h_m=0.3, kcb=0.30)
    d1 = ev.surface_day(18.0, et0_mm=4.5, p_minus_ro_mm=0.0, tew_mm=18.0, rew_mm=8.0, kc_max=kcm, kcb=0.30, few=0.80,
                        irrigation_mm=40.0, fw=0.8, wetting_first=True)
    assert d1["de_start_mm"] == 0.0 and d1["kr"] == 1.0
    assert d1["ke"] == pytest.approx(0.91, abs=0.005) and d1["e_mm"] / 0.80 == pytest.approx(5.1, abs=0.05)
    assert d1["dpe_mm"] == pytest.approx(32.0) and round(d1["de_mm"]) == 5 and d1["e_mm"] == pytest.approx(4.1, abs=0.05)
    assert (0.30 + d1["ke"]) * 4.5 == pytest.approx(5.5, abs=0.05)
    d2 = ev.surface_day(d1["de_mm"], et0_mm=5.0, p_minus_ro_mm=0.0, tew_mm=18.0, rew_mm=8.0, kc_max=kcm, kcb=0.31,
                        few=0.80, wetting_first=True)
    assert d2["kr"] == 1.0 and d2["ke"] == pytest.approx(0.90, abs=0.005) and d2["dpe_mm"] == 0.0
    assert d2["e_mm"] / 0.80 == pytest.approx(5.6, abs=0.05) and round(d2["de_mm"]) == 11
    assert d2["e_mm"] == pytest.approx(4.5, abs=0.05) and (0.31 + d2["ke"]) * 5.0 == pytest.approx(6.1, abs=0.05)


def test_example_35_day_6_rain_at_the_start_of_the_day_updates_the_start_depletion():
    """Day 6: 6 mm rain at the start of the day on the printed day-5 end (17 mm): De start = 17 - 6 = 11."""
    d = ev.surface_day(17.0, et0_mm=2.7, p_minus_ro_mm=6.0, tew_mm=18.0, rew_mm=8.0, kc_max=1.21, kcb=0.36, few=0.89,
                       wetting_first=True)
    assert d["de_start_mm"] == pytest.approx(11.0) and d["dpe_mm"] == 0.0


def test_rain_late_in_the_day_uses_the_previous_days_depletion_for_kr():
    """The twin's order (rules.yaml bare_soil.method): Kr from De of the end of the previous day (eq. 74 as printed);
    the day's rain then wets the layer. A dry layer (De = TEW) evaporates nothing on the day of the rain."""
    d = ev.surface_day(20.0, et0_mm=4.0, p_minus_ro_mm=15.0, tew_mm=20.0, rew_mm=9.0, kc_max=1.2)
    assert d["kr"] == 0.0 and d["e_mm"] == 0.0 and d["de_mm"] == pytest.approx(5.0) and d["dpe_mm"] == 0.0
    d = ev.surface_day(3.0, et0_mm=4.0, p_minus_ro_mm=15.0, tew_mm=20.0, rew_mm=9.0, kc_max=1.2)
    assert d["e_mm"] == pytest.approx(4.8) and d["dpe_mm"] == pytest.approx(12.0) and d["de_mm"] == pytest.approx(4.8)


def test_the_surface_layer_balance_closes_eq_77():
    """De_end = De_prev - (P - RO) + E + DPe (eq. 77 with no irrigation and no transpiration), 0 <= De <= TEW (eq. 78)."""
    de = 12.0
    for p in (0.0, 2.0, 0.0, 30.0, 0.0, 0.5, 0.0, 0.0, 8.0):
        d = ev.surface_day(de, et0_mm=5.0, p_minus_ro_mm=p, tew_mm=25.7, rew_mm=9.0, kc_max=1.2)
        assert d["de_mm"] == pytest.approx(de - p + d["e_mm"] + d["dpe_mm"])
        assert 0.0 <= d["de_mm"] <= 25.7
        de = d["de_mm"]


# --- TEW from the twin's own soil table (SoilGrids layers) over 0..Ze, depth-weighted ---
SOIL = pd.DataFrame({"top_cm": [0, 5, 15, 30], "bottom_cm": [5, 15, 30, 60],
                     "theta_fc_m3m3": [0.333, 0.331, 0.326, 0.322], "theta_wp_m3m3": [0.148, 0.152, 0.159, 0.173],
                     "sand_pct": [33.6, 33.0, 31.0, 28.8], "clay_pct": [20.6, 21.4, 25.2, 29.8]})


def test_tew_from_layers_weights_the_layers_by_depth():
    # 0-5 cm: 1000 (0.333 - 0.074) 0.05 = 12.95; 5-10 cm: 1000 (0.331 - 0.076) 0.05 = 12.75; sum 25.70 mm
    assert ev.tew_from_layers(SOIL, 0.10) == pytest.approx(25.70)


# --- USDA texture class (SSSA Glossary 2022, p. 115) and FAO-56 Table 19's REW ---
@pytest.mark.parametrize("sand,silt,clay,cls", [
    (33.6, 45.8, 20.6, "loam"),            # the demo field's SoilGrids top layer
    (40.0, 40.0, 20.0, "loam"),
    (52.0, 28.0, 20.0, "loam"),            # Soil Survey Manual 'sand 52 percent or less' (SSSA prints '<52%')
    (30.0, 30.0, 40.0, "clay"),            # SSSA: 40% or more clay, <45% sand, <40% silt
    (35.0, 35.0, 30.0, "clay loam"),       # SSSA: 27 to 40% clay and 20 to 45% sand
    (80.0, 12.0, 8.0, "loamy sand"),       # SSSA: 70-91% sand, silt + 1.5 clay >= 15, silt + 2 clay < 30
    (95.0, 3.0, 2.0, "sand"),
    (65.0, 25.0, 10.0, "sandy loam"),
    (20.0, 65.0, 15.0, "silt loam"),
    (5.0, 85.0, 10.0, "silt"),
    (10.0, 55.0, 35.0, "silty clay loam"),
    (5.0, 50.0, 45.0, "silty clay")])
def test_usda_texture_class(sand, silt, clay, cls):
    assert ev.usda_texture(sand, silt, clay) == cls


def test_texture_fractions_must_add_up_to_100():
    with pytest.raises(ValueError, match="100"):
        ev.usda_texture(30.0, 30.0, 30.0)


def test_rew_is_the_midpoint_of_table_19_and_loam_gives_example_31s_9_mm():
    table = {"loam": [8, 10], "sandy loam": [6, 10]}
    assert ev.rew_mm("loam", table) == pytest.approx(9.0) and ev.rew_mm("sandy loam", table) == pytest.approx(8.0)
    with pytest.raises(ValueError, match="clay loam"):
        ev.rew_mm("clay loam", table)


def test_start_depletion_of_a_bare_spell_follows_the_root_zone():
    """rules.yaml bare_soil.de_start: De = TEW x Dr / TAW (0 at field capacity, TEW at the wilting point)."""
    assert ev.de_start_mm(0.0, 150.0, 25.0) == 0.0
    assert ev.de_start_mm(30.0, 150.0, 25.0) == pytest.approx(5.0)
    assert ev.de_start_mm(150.0, 150.0, 25.0) == pytest.approx(25.0)


RULES = {"kc": 0.3, "apply": False, "method": "fao56_surface_layer", "ze_m": 0.10, "kc_max": 1.20,
         "table_19_rew_mm": {"loam": [8, 10]}}


def test_bare_soil_setting_for_the_demo_soil():
    s = ev.bare_soil_setting(RULES, SOIL, method="fao56")
    assert s["method"] == "fao56_surface_layer" and s["texture"] == "loam"
    assert s["rew_mm"] == pytest.approx(9.0) and s["tew_mm"] == pytest.approx(25.70) and s["kc_max"] == 1.20
    assert s["ze_m"] == 0.10


def test_the_old_method_is_the_constant_kc():
    assert ev.bare_soil_setting(RULES, SOIL, method="kc") == 0.3
    assert ev.bare_soil_setting(RULES, SOIL, method="rules") == 0.3              # apply: false
    assert isinstance(ev.bare_soil_setting({**RULES, "apply": True}, SOIL, method="rules"), dict)
    with pytest.raises(ValueError, match="method"):
        ev.bare_soil_setting(RULES, SOIL, method="other")


# --- the free callers follow rules.yaml bare_soil.apply (coordinator's item 1, 2026-11-14) ---
@pytest.mark.parametrize("script", ["scripts/run_diary.py", "scripts/run_memory.py", "scripts/run_smap_check.py",
                                    "scripts/run_season.py", "scripts/run_replay.py", "scripts/run_plans.py",
                                    "scripts/run_twin_now.py", "scripts/run_validation_checks.py", "pipeline/future/runs.py"])
def test_callers_take_the_bare_soil_method_from_the_switch_not_the_constant(script):
    """Every runner takes the switches through evaporation.bare_soil_setting or pipeline/plans/twin_options.py."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / script).read_text()
    assert 'rules["bare_soil"]["kc"]' not in src and ("bare_soil_setting" in src or "twin_options" in src)
