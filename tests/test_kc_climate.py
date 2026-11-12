"""FAO-56 climate adjustment of Kc mid (eq. 62) and Kc end (eq. 65), REVIEW_NOTES M7 (owner review of d34fa93,
item 6). Table 12 values are for a sub-humid climate (RHmin about 45%, u2 about 2 m/s); the Kathmandu valley
monsoon is humid and calm, so Kc mid and Kc end are adjusted per season from the season's own weather.

Worked numbers, FAO-56 Chapter 6 (https://www.fao.org/4/x0490e/x0490e0b.htm, read 2026-11-12):
- Example 27, maize, Kc mid (Tab) 1.20, h 2 m: Taipei (u2 1.3 m/s, RHmin 75%) -> 1.07; Mocha (u2 4.6 m/s,
  RHmin 44%) -> 1.30.
- Box 15, dry bean, Kc mid 1.15, Kc end 0.35, h 0.4 m, RHmin 30%, u2 2.2 m/s -> Kc mid 1.19; Kc end stays 0.35
  ("As Kc end = 0.35 is less than 0.45, no adjustment is made").
"""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.plans import simulate as sim
from pipeline.twin import season as s
from pipeline.twin.crops import (STAGE_ORDER, kc_climate_adjust, kc_end_climate_adjust, rhmin_pct, season_kc,
                                 season_length)
from pipeline.twin.et0 import e0_kpa

LIB = load_crops()
SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200],
                     "theta_fc_m3m3": [0.32, 0.33, 0.33], "theta_wp_m3m3": [0.15, 0.20, 0.22]})


def test_example_27_maize_taipei_and_mocha():
    assert round(kc_climate_adjust(1.20, u2_ms=1.3, rhmin=75, h_m=2.0), 2) == 1.07
    assert round(kc_climate_adjust(1.20, u2_ms=4.6, rhmin=44, h_m=2.0), 2) == 1.30


def test_box_15_dry_bean_adjusts_kc_mid_and_leaves_kc_end_below_045_alone():
    assert round(kc_climate_adjust(1.15, u2_ms=2.2, rhmin=30, h_m=0.4), 2) == 1.19
    assert kc_end_climate_adjust(0.35, u2_ms=2.2, rhmin=30, h_m=0.4) == 0.35


def test_the_table_12_climate_needs_no_adjustment():
    assert kc_climate_adjust(1.15, u2_ms=2.0, rhmin=45, h_m=1.0) == pytest.approx(1.15)


def test_kc_end_above_045_is_adjusted_and_humid_calm_lowers_it():
    assert kc_end_climate_adjust(0.75, u2_ms=1.0, rhmin=80, h_m=1.0) < 0.75
    assert kc_end_climate_adjust(0.75, u2_ms=1.0, rhmin=80, h_m=1.0) == pytest.approx(
        kc_climate_adjust(0.75, u2_ms=1.0, rhmin=80, h_m=1.0))


def test_inputs_are_held_to_the_fao56_limits():
    """u2 1 to 6 m/s, RHmin 20 to 80%, h 0.1 to 10 m ("The limits ... should be observed")."""
    assert kc_climate_adjust(1.2, 0.3, 95, 1.0) == pytest.approx(kc_climate_adjust(1.2, 1.0, 80, 1.0))
    assert kc_climate_adjust(1.2, 9.0, 5, 1.0) == pytest.approx(kc_climate_adjust(1.2, 6.0, 20, 1.0))
    assert kc_climate_adjust(1.2, 3.0, 30, 25.0) == pytest.approx(kc_climate_adjust(1.2, 3.0, 30, 10.0))


def test_rhmin_is_ea_over_saturation_at_tmax_eq_63():
    """Eq. 63 uses e°(Tdew) = ea (eq. 14); our ea is POWER's, capped at e°(corrected Tmin) (REVIEW_NOTES M6)."""
    assert rhmin_pct(e0_kpa(30.0), 30.0) == pytest.approx(100.0)
    assert rhmin_pct(e0_kpa(20.0), 30.0) == pytest.approx(100 * 2.338 / 4.243, abs=0.05)   # eq. 11 at 20 and 30 C
    assert rhmin_pct(5.0, 20.0) == 100.0                                                  # never above saturation


def _stage_days(stages):
    ini, dev, mid, late = (stages[k] for k in STAGE_ORDER)
    return ini + dev, ini + dev + mid, ini + dev + mid + late


def test_season_kc_averages_u2_and_rhmin_over_the_mid_and_late_stages_only():
    st, kc, h = LIB["maize"]["stages_days"], LIB["maize"]["kc"], 2.0
    a, b, n = _stage_days(st)
    u2, rh = np.full(n, 6.0), np.full(n, 20.0)          # initial and development: windy and dry (ignored)
    u2[a:b], rh[a:b] = 1.3, 75.0                         # mid-season: Taipei
    u2[b:], rh[b:] = 4.6, 44.0                           # late season: Mocha
    out = season_kc(kc, st, h, u2, rh)
    assert out["ini"] == kc["ini"]
    assert out["mid"] == pytest.approx(kc_climate_adjust(kc["mid"], 1.3, 75, h))
    assert out["end"] == kc["end"]                      # maize Kc end 0.35 < 0.45: not adjusted
    assert out["u2_mid_ms"] == pytest.approx(1.3) and out["rhmin_mid_pct"] == pytest.approx(75.0)
    potato = season_kc(LIB["potato"]["kc"], LIB["potato"]["stages_days"], 0.6, u2[: season_length(LIB["potato"]["stages_days"])],
                       rh[: season_length(LIB["potato"]["stages_days"])])
    assert potato["end"] != LIB["potato"]["kc"]["end"]  # potato Kc end 0.75 > 0.45: adjusted


def test_a_season_with_no_mid_season_days_keeps_the_table_values():
    st, kc = LIB["maize"]["stages_days"], LIB["maize"]["kc"]
    a, _, _ = _stage_days(st)
    out = season_kc(kc, st, 2.0, np.full(a, 1.3), np.full(a, 75.0))
    assert (out["mid"], out["end"]) == (kc["mid"], kc["end"]) and out["u2_mid_ms"] is None


def test_every_simulatable_crop_has_a_sourced_height():
    for name, c in LIB.items():
        if c.get("simulate", True):
            assert c["height_m"] > 0, name
            assert "Table 12" in c["sources"]["height_m"], name


def _weather(u2, rh, start="2016-04-01", end="2016-12-31"):
    d = pd.date_range(start, end)
    return pd.DataFrame({"date": d, "et0_mm": 4.0, "rain_mm": 6.0, "u2_ms": u2, "rhmin_pct": rh})


def test_simulate_uses_the_adjusted_curve_and_reports_it():
    w = _weather(1.3, 75.0)
    cn = {"bare": 91, "maize": 83}
    _, plain = s.simulate(w, [("maize", "2016-05-01")], LIB, SOIL, cn, bare_kc=0.3, irrigated=True)
    _, adj = s.simulate(w, [("maize", "2016-05-01")], LIB, SOIL, cn, bare_kc=0.3, irrigated=True, kc_climate=True)
    m = adj["maize"]
    assert m["kc_climate_adjusted"] is True and plain["maize"]["kc_climate_adjusted"] is False
    assert m["kc_mid_used"] == pytest.approx(kc_climate_adjust(1.20, 1.3, 75, LIB["maize"]["height_m"]))
    assert m["kc_mid_used"] < 1.20 and m["sum_etc_mm"] < plain["maize"]["sum_etc_mm"]
    assert plain["maize"]["kc_mid_used"] == 1.20


def test_simulate_with_kc_climate_but_no_wind_or_humidity_fails_loudly():
    w = _weather(1.3, 75.0).drop(columns=["rhmin_pct"])
    with pytest.raises(ValueError, match="rhmin_pct"):
        s.simulate(w, [("maize", "2016-05-01")], LIB, SOIL, {"bare": 91, "maize": 83}, bare_kc=0.3,
                   irrigated=False, kc_climate=True)


def test_replay_derives_u2_and_rhmin_from_the_weather_table():
    d = pd.date_range("2015-01-01", "2017-12-31")
    w = pd.DataFrame({"date": d, "et0_mm": 4.0, "rain_mm": 6.0, "ws2m_ms": 1.3,
                      "ea_kpa": e0_kpa(15.0), "tmax_c": 25.0})
    out = sim.replay(w, ["rice", "potato"], LIB, SOIL, {"bare": 91, "rice": 83, "potato": 83}, bare_kc=0.3,
                     irrigated=True, kc_climate=True)
    rice = next(x for x in out["seasons"] if x["crop"] == "rice")
    assert rice["u2_mid_ms"] == pytest.approx(1.3)
    assert rice["rhmin_mid_pct"] == pytest.approx(rhmin_pct(e0_kpa(15.0), 25.0))
    assert out["kc_climate"] is True


def test_rules_yaml_turns_the_adjustment_on_with_the_code_s_limits():
    from pipeline.fetch.rules import load_rules
    from pipeline.twin.crops import KC_CLIMATE_LIMITS, KC_END_MIN_TO_ADJUST

    r = load_rules()["kc_climate"]
    assert r["apply"] is True
    assert {k: tuple(v) for k, v in r["limits"].items()} == KC_CLIMATE_LIMITS
    assert r["kc_end_min_to_adjust"] == KC_END_MIN_TO_ADJUST


def test_replay_with_kc_climate_names_the_weather_columns_it_lacks():
    d = pd.date_range("2015-01-01", "2016-12-31")
    w = pd.DataFrame({"date": d, "et0_mm": 4.0, "rain_mm": 6.0})
    with pytest.raises(ValueError, match="ws2m_ms.*ea_kpa.*tmax_c"):
        sim.replay(w, ["rice", "potato"], LIB, SOIL, {"bare": 91, "rice": 83, "potato": 83}, bare_kc=0.3,
                   irrigated=False, kc_climate=True)
