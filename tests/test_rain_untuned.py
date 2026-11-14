"""The fourth rain version, 'untuned' (owner, 2026-11-14 afternoon: 'Keep the other versions as the range'): the
break-corrected rain before the gauge factors of rules.yaml gpm_series.gauge_calibration (pipeline/twin/inputs.with_rain)."""
import pandas as pd
import pytest

from pipeline.twin.inputs import with_rain
from scripts.common import RAIN_DIRS, rain_kw

W = pd.DataFrame({"date": pd.to_datetime(["2020-05-31", "2020-06-01", "2020-09-30", "2020-10-01"]),
                  "rain_mm": [7.46, 10.53, 21.06, 0.0]})


def test_untuned_divides_out_the_month_s_gauge_factor():
    """Tuned = corrected x 1.053 in June-September, x 0.746 otherwise: 7.46 / 0.746 = 10, 10.53 / 1.053 = 10,
    21.06 / 1.053 = 20, 0 stays 0."""
    u = with_rain(W, "untuned", gauge={"jjas": 1.053, "other": 0.746})
    assert u["rain_mm"].tolist() == pytest.approx([10.0, 10.0, 20.0, 0.0])
    assert W["rain_mm"].tolist() == [7.46, 10.53, 21.06, 0.0]                      # the input is not changed


def test_without_gauge_factors_untuned_is_the_central_rain():
    assert with_rain(W, "untuned", gauge=None)["rain_mm"].tolist() == W["rain_mm"].tolist()


def test_the_runners_pass_the_factors_only_for_a_calibrated_field():
    rules = {"gpm_series": {"gauge_calibration": {"apply": True, "fields": ["demo"], "factors": {"jjas": 1.053, "other": 0.746}},
                            "dhm_scaling": {"years": [2001, 2020]}}}
    assert rain_kw(rules, "untuned", "demo") == {"gauge": {"jjas": 1.053, "other": 0.746}}
    assert rain_kw(rules, "untuned", "sample-1") == {"gauge": None}
    rules["gpm_series"]["gauge_calibration"]["apply"] = False
    assert rain_kw(rules, "untuned", "demo") == {"gauge": None}
    assert rain_kw(rules, "corrected", "demo") == {} and rain_kw(rules, "uncorrected", "demo") == {}
    assert set(rain_kw(rules, "dhm", "demo")) == {"dhm"}
    assert RAIN_DIRS["untuned"] == "rain_untuned"
