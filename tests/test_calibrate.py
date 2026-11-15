"""Owner's probe brief, 2026-11-14, fix 4: real water and honest words (robot/calibrate.py; rules.yaml probe.band,
probe.kalman.r and .z). The bench calibration (config/probe_calibration.yaml, from scripts/run_probe_bench.py) turns the
probe's percent into water %; the field's own soil and the crop now turn water % into a band. Hand-worked numbers."""
import pandas as pd
import pytest
import yaml

from robot import calibrate as cal

LINE = {"model": "line", "coef": [-5.0, 0.6]}            # water % = -5 + 0.6 x probe %
SOIL = pd.DataFrame({"top_cm": [0, 5, 15, 30, 60], "bottom_cm": [5, 15, 30, 60, 100],
                     "theta_fc_m3m3": [0.333, 0.331, 0.326, 0.322, 0.322],
                     "theta_wp_m3m3": [0.148, 0.152, 0.159, 0.173, 0.191]})


def test_apply_a_line_and_a_curve():
    assert cal.apply_fit(40, LINE) == pytest.approx(19.0)                               # -5 + 24
    q = {"model": "quadratic", "coef": [1.0, 0.5, 0.002]}                                # 1 + 20 + 0.002 x 1600
    assert cal.apply_fit(40, q) == pytest.approx(24.2) and cal.slope_at(40, q) == pytest.approx(0.66)   # 0.5 + 2 x 0.002 x 40
    assert cal.slope_at(40, LINE) == 0.6


def test_depth_weighted_soil_water_hand_worked():
    # 0-10 cm: half of 0-5 and half of 5-15: fc (0.333 + 0.331) / 2 = 0.332, wp (0.148 + 0.152) / 2 = 0.150
    fc, wp = cal.depth_theta(SOIL, 0.10)
    assert fc == pytest.approx(0.332) and wp == pytest.approx(0.150)
    # 0-60 cm, weights 5, 10, 15, 30: fc 19.525/60 = 0.325417, wp 9.835/60 = 0.163917
    fc, wp = cal.depth_theta(SOIL, 0.6)
    assert fc == pytest.approx(0.325417, abs=1e-6) and wp == pytest.approx(0.163917, abs=1e-6)


def test_bands_hand_worked():
    # potato p 0.35: stress starts at theta 0.332 - 0.35 x (0.332 - 0.150) = 0.2683 -> 26.83 water %; field capacity 33.2 %
    b = cal.band(25.0, 0.332, 0.150, 0.35)
    assert b["band"] == "needs water" and b["needs_water_below_pct"] == pytest.approx(26.83) and b["too_wet_above_pct"] == pytest.approx(33.2)
    assert cal.band(30.0, 0.332, 0.150, 0.35)["band"] == "good"
    assert cal.band(26.83, 0.332, 0.150, 0.35)["band"] == "good"                         # at the point: not yet suffering
    assert cal.band(34.0, 0.332, 0.150, 0.35)["band"] == "too wet"


def test_water_to_twin_wetness_and_r_hand_worked():
    assert cal.wetness_from_water(25.0, 0.33, 0.17) == pytest.approx(50.0)               # 100 x (0.25 - 0.17) / 0.16
    # R_probe 1.3, slope 0.6 water-% per probe %, fc - wp 0.16: 1.3 x (0.6 / 0.16)^2 = 1.3 x 14.0625 = 18.28125
    assert cal.r_twin_var(1.3, 0.6, 0.33, 0.17) == pytest.approx(18.28125)
    # the spoon calibration adds its own error (rules.yaml probe.bench.spoon.use): (2 x 0.8^2 + 4) / 0.25^2 = 84.48
    assert cal.r_twin_var(2.0, 0.8, 0.40, 0.15, fit_var=4.0) == pytest.approx(84.48)


def test_drier_or_wetter_than_the_other_parts():
    # others 40 and 41: median 40.5; 30 is 10.5 lower -> drier; 3 points or less is about the same
    assert cal.relative(30.0, [40.0, 41.0], 3) == "drier"
    assert cal.relative(43.0, [40.0, 41.0], 3) == "about the same"                     # 2.5 points
    assert cal.relative(45.0, [40.0, 41.0], 3) == "wetter"
    assert cal.relative(45.0, [], 3) is None


def test_the_calibration_file_is_read_and_must_say_where_it_came_from(tmp_path):
    good = {"made_from": "the bench test of 2026-11-15, not field-tested", "fit": LINE, "mae_water_pct": 2.3,
            "r_probe_pct2": 1.3, "cups": 6, "date": "2026-11-15"}
    p = tmp_path / "probe_calibration.yaml"
    p.write_text(yaml.safe_dump(good))
    assert cal.load_calibration(p)["mae_water_pct"] == 2.3
    assert cal.load_calibration(tmp_path / "missing.yaml") is None
    p.write_text(yaml.safe_dump({**good, "made_from": "fake_probe rehearsal"}))
    with pytest.raises(ValueError, match="bench"):
        cal.load_calibration(p)
