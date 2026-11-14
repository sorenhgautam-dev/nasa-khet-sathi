"""rules.yaml gpm_series.gauge_calibration: the central rain times two gauge factors, a switch that is off until the owner
chooses. Worked numbers by hand on the fixture of tests/test_export_any_field.py (GPM 2 mm a day, 3 mm from 2017)."""
import pandas as pd
import pytest

from pipeline.fetch.weather import correct_gpm_break
from pipeline.twin.inputs import with_rain

DAYS = pd.date_range("2001-01-01", "2018-12-31")
RULE = {"correction_fields": ["demo"], "correction_from": "2017-01-01", "correction_reference_years": [2001, 2016],
        "correction_products": ["final"], "correction_factor_products": ["final"], "correction": "c", "trend_caveat": "t",
        "correction_for_samples": "text"}


def _run(apply, field_id="demo", fields=("demo",)):
    rain = pd.DataFrame({"date": DAYS, "rain_mm": 2.0, "rain_source": "gpm"})
    rain.loc[rain["date"] >= "2017-01-01", "rain_mm"] = 3.0
    gpm = pd.DataFrame({"date": DAYS, "product": "final", "rain_mm": rain["rain_mm"]})
    rule = {**RULE, "gauge_calibration": {"apply": apply, "factors": {"jjas": 1.1, "other": 0.8}, "fields": list(fields)}}
    field = {"id": field_id} if field_id == "demo" else {"id": field_id, "sample_of": "demo"}     # both break-corrected
    out, info = correct_gpm_break(rain, gpm, rule, field_id, field=field, break_test={"found": True, "year": 2017})
    return out.set_index("date"), info


def test_on_the_corrected_rain_is_times_the_season_factor_on_every_day():
    out, info = _run(True)
    # 2017: 3 mm x 2/3 (break) = 2 mm, then x 0.8 in January and x 1.1 in July; 2001 (not break-scaled): 2 mm x 0.8
    assert out.loc["2017-01-15", "rain_mm"] == pytest.approx(1.6)
    assert out.loc["2017-07-15", "rain_mm"] == pytest.approx(2.2)
    assert out.loc["2001-01-15", "rain_mm"] == pytest.approx(1.6)
    assert out.loc["2001-09-30", "rain_mm"] == pytest.approx(2.2)
    assert out.loc["2017-07-15", "rain_uncorrected_mm"] == 3.0          # GPM as published stays as it is
    g = info["gauge_calibration"]
    assert g["applied"] is True and g["central_rain"] == "gauge_calibrated" and g["factors"] == {"jjas": 1.1, "other": 0.8}


def test_off_or_another_field_leaves_the_corrected_rain_exactly():
    for out, info in (_run(False), _run(True, field_id="sample-1", fields=("demo",))):
        assert out.loc["2017-01-15", "rain_mm"] == pytest.approx(2.0) and out.loc["2001-07-15", "rain_mm"] == 2.0
        assert info["gauge_calibration"]["applied"] is False
        assert info["gauge_calibration"]["central_rain"] == "corrected"


def test_the_dhm_scaled_version_does_not_change():
    normals = {"normals_mm": {m: 50.0 for m in range(1, 13)}, "years": [2001, 2016]}
    on, off = (_run(a)[0].reset_index() for a in (True, False))
    a, b = (with_rain(w, "dhm", normals)["rain_mm"].to_numpy() for w in (on, off))
    assert abs(a - b).max() < 1e-9
    assert a[DAYS.get_loc("2001-01-31")] == pytest.approx(50 / 31)     # a 31-day month of 50 mm


def test_the_method_page_words_say_it_in_one_line():
    from pipeline.export.build_field_json import calibration_words
    from pipeline.words import texts
    held, vals = calibration_words({"gauge_calibration": {"applied": True, "factors": {"jjas": 1.053, "other": 0.746}}})
    assert held == {"rain_gauge_calibrated"} and vals == {"cal_dry_down": 25, "cal_wet_up": 5}
    lines = texts.load("tabs")["method_page"]["rain_correction"]
    line = [x for x in lines if x["when"] == ["rain_gauge_calibrated"]]
    assert len(line) == 1
    en = texts.fill(line[0], vals, "en")
    assert "25%" in en and "5%" in en and "four" in en
    assert calibration_words({"gauge_calibration": {"applied": False}}) == (set(), {})
    assert calibration_words({}) == (set(), {})
