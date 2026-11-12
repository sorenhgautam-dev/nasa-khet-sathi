"""Build step 3: FAO-56 Penman-Monteith reference evapotranspiration (daily, G = 0).

Worked numbers from FAO Irrigation and Drainage Paper 56 (Allen et al. 1998), as printed on fao.org
(checked 2026-11-11): Example 2 and Example 8 in Chapter 3 (https://www.fao.org/4/x0490e/x0490e07.htm),
Example 18 in Chapter 4 (https://www.fao.org/4/x0490e/x0490e08.htm). Example 18's ea (1.409 kPa) comes
from eq. 17 (RHmax, RHmin), so it is passed in directly. Real-data check: 30 days
of NASA POWER for the demo point against the pyet library (CLAUDE.md: within 3 percent).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyet
import pytest

from pipeline.twin import et0 as e

FIX = Path(__file__).parent / "fixtures" / "power_demo_2023-04.csv"


# --- FAO-56 Example 2: 1800 m ---
def test_pressure_at_1800_m():
    assert e.pressure_kpa(1800) == pytest.approx(81.8, abs=0.05)


def test_psychrometric_constant_at_1800_m():
    assert e.psychrometric_kpa_c(e.pressure_kpa(1800)) == pytest.approx(0.054, abs=0.0005)


# --- FAO-56 Example 8: 3 September (day 246), 20 deg S ---
def test_extraterrestrial_radiation_example_8():
    assert e.ra_mj_m2_day(-20.0, 246) == pytest.approx(32.2, abs=0.05)


def test_example_8_intermediates():
    dr, dec, ws = e.ra_parts(-20.0, 246)
    assert (dr, dec, ws) == (pytest.approx(0.985, abs=5e-4), pytest.approx(0.120, abs=5e-4), pytest.approx(1.527, abs=5e-4))


# --- FAO-56 Example 18: Uccle (Brussels), 6 July (day 187), 50 deg 48' N, 100 m ---
TMAX, TMIN, LAT, DOY, Z = 21.5, 12.3, 50.8, 187, 100
EA, RS, U2 = 1.409, 22.07, 2.078


def test_example_18_slope_of_vapour_pressure_curve():
    assert e.delta_kpa_c((TMAX + TMIN) / 2) == pytest.approx(0.122, abs=0.0005)


def test_example_18_psychrometric_constant():
    assert e.psychrometric_kpa_c(e.pressure_kpa(Z)) == pytest.approx(0.0666, abs=0.0002)


def test_example_18_saturation_vapour_pressure():
    assert e.es_kpa(TMAX, TMIN) == pytest.approx(1.997, abs=0.002)


def test_example_18_extraterrestrial_radiation():
    assert e.ra_mj_m2_day(LAT, DOY) == pytest.approx(41.09, abs=0.03)


def test_example_18_clear_sky_radiation():
    assert e.rso_mj_m2_day(41.09, Z) == pytest.approx(30.90, abs=0.01)


def test_example_18_pressure():
    assert e.pressure_kpa(Z) == pytest.approx(100.1, abs=0.05)


def test_example_18_net_longwave():
    assert e.rnl_mj_m2_day(TMAX, TMIN, EA, RS, 30.90) == pytest.approx(3.71, abs=0.01)


def test_example_18_net_radiation():
    rnl = e.rnl_mj_m2_day(TMAX, TMIN, EA, RS, 30.90)
    assert e.rn_mj_m2_day(RS, rnl) == pytest.approx(13.28, abs=0.02)   # printed 13.28


def test_example_18_et0():
    et = e.et0_mm(TMAX, TMIN, U2, RS, Z, LAT, DOY, ea=EA)
    assert et == pytest.approx(3.9, abs=0.05)


# --- other properties ---
def test_ea_from_mean_rh_is_fao56_eq_19():
    assert e.ea_from_rhmean_kpa(60.0, TMAX, TMIN) == pytest.approx(0.6 * e.es_kpa(TMAX, TMIN))


def test_rs_above_rso_is_capped_in_net_longwave():
    # FAO-56: Rs/Rso is limited to 1.0 in eq. 39
    assert e.rnl_mj_m2_day(TMAX, TMIN, EA, 40.0, 30.90) == pytest.approx(e.rnl_mj_m2_day(TMAX, TMIN, EA, 30.90, 30.90))


def test_very_cloudy_day_keeps_net_longwave_positive():
    # Rs/Rso below about 0.26 would make (1.35 Rs/Rso - 0.35) negative; the ratio is floored at 0.3
    # (ASCE-EWRI 2005 standardized equation; also what pyet does).
    rnl = e.rnl_mj_m2_day(TMAX, TMIN, EA, 3.0, 30.90)
    assert rnl > 0
    assert rnl == pytest.approx(e.rnl_mj_m2_day(TMAX, TMIN, EA, 0.3 * 30.90, 30.90))


def test_more_sun_gives_more_et0():
    lo = e.et0_mm(25, 12, 2.0, 10.0, 1300, 27.67, 100, rh_mean=50)
    hi = e.et0_mm(25, 12, 2.0, 20.0, 1300, 27.67, 100, rh_mean=50)
    assert hi > lo


def test_needs_rh_or_ea():
    with pytest.raises(ValueError):
        e.et0_mm(25, 12, 2.0, 15.0, 1300, 27.67, 100)


# --- CLAUDE.md step 3: within 3 percent of pyet on 30 days of real POWER data ---
def test_matches_pyet_within_3_percent_on_30_real_power_days():
    df = pd.read_csv(FIX, comment="#", parse_dates=["date"])
    assert len(df) == 30
    ours = e.et0_mm(df["tmax_c"], df["tmin_c"], df["ws2m_ms"], df["rs_mj_m2_day"], 1269.39, 27.67,
                    df["date"].dt.day_of_year, rh_mean=df["rh_pct"])
    idx = pd.DatetimeIndex(df["date"])

    def s(col):
        return pd.Series(df[col].to_numpy(), index=idx)

    ref = pyet.pm_fao56(tmean=(s("tmax_c") + s("tmin_c")) / 2, wind=s("ws2m_ms"), rs=s("rs_mj_m2_day"),
                        tmax=s("tmax_c"), tmin=s("tmin_c"), rh=s("rh_pct"), elevation=1269.39,
                        lat=np.deg2rad(27.67), clip_zero=False)
    rel = np.abs(np.asarray(ours) - ref.to_numpy()) / ref.to_numpy()
    assert rel.max() < 0.03, f"worst day differs by {100 * rel.max():.2f}%"
