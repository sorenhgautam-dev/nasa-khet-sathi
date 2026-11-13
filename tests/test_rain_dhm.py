"""Owner's queue item 4b (rules.yaml gpm_series.dhm_scaling): a third rain version, the break-corrected rain scaled month
by month to a DHM station's 1991-2020 monthly normals. Worked numbers by hand on synthetic rain."""
import numpy as np
import pandas as pd
import pytest

from pipeline.twin import inputs

NORMALS = {m: 30.0 for m in range(1, 13)} | {1: 31.0, 2: 56.0}


def _weather():
    d = pd.date_range("2001-01-01", "2002-12-31")
    rain = np.where(d.month == 1, 2.0, 1.0)                       # January 62 mm, February 28 mm, March 31 mm ...
    return pd.DataFrame({"date": d, "rain_mm": rain, "rain_uncorrected_mm": rain * 1.5, "et0_mm": 3.0})


def test_the_factor_is_the_normal_over_the_mean_complete_month_total_of_the_years():
    f = inputs.dhm_factors(_weather().set_index("date")["rain_mm"], NORMALS, [2001, 2002])
    assert f[1] == pytest.approx(31.0 / 62.0) and f[2] == pytest.approx(56.0 / 28.0)
    assert f[3] == pytest.approx(30.0 / 31.0) and f[4] == pytest.approx(30.0 / 30.0)


def test_only_the_named_years_set_the_factor():
    w = _weather()
    w.loc[w["date"].dt.year == 2002, "rain_mm"] *= 3.0                 # 2002 is three times wetter
    f = inputs.dhm_factors(w.set_index("date")["rain_mm"], NORMALS, [2001, 2001])
    assert f[1] == pytest.approx(0.5)


def test_with_rain_dhm_scales_every_day_of_the_corrected_rain_by_its_months_factor():
    w = _weather()
    out = inputs.with_rain(w, "dhm", dhm={"normals_mm": NORMALS, "years": [2001, 2002]})
    jan, feb = out["date"].dt.month == 1, out["date"].dt.month == 2
    assert np.allclose(out.loc[jan, "rain_mm"], 1.0) and np.allclose(out.loc[feb, "rain_mm"], 2.0)
    assert out["rain_mm"].groupby([out["date"].dt.year, out["date"].dt.month]).sum().loc[(2002, 2)] == pytest.approx(56.0)
    assert np.allclose(w["rain_mm"], np.where(w["date"].dt.month == 1, 2.0, 1.0))         # input untouched


def test_with_rain_dhm_needs_the_normals_and_the_old_versions_are_unchanged():
    w = _weather()
    with pytest.raises(ValueError, match="normals"):
        inputs.with_rain(w, "dhm")
    assert inputs.with_rain(w, "corrected") is w
    assert np.allclose(inputs.with_rain(w, "uncorrected")["rain_mm"], w["rain_uncorrected_mm"])


def test_a_month_without_a_complete_month_in_the_years_stops():
    w = _weather()
    w.loc[(w["date"].dt.month == 3) & (w["date"].dt.day == 5), "rain_mm"] = np.nan
    with pytest.raises(ValueError, match="Mar"):
        inputs.dhm_factors(w.set_index("date")["rain_mm"], NORMALS, [2001, 2002])
