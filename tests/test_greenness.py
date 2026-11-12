"""Field greenness and bare days (CLAUDE.md "Field diary", build step 6a). Worked examples for the pure
functions in pipeline/diary/greenness.py; rules in rules.yaml greenness and bare_days."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import greenness as gr
from pipeline.fetch.rules import load_rules

R = load_rules()


def test_the_rules():
    assert R["bare_days"]["ndvi_max"] == 0.25                      # CLAUDE.md: start at 0.25
    assert 0 < R["greenness"]["min_clear_fraction"] <= 1
    assert R["greenness"]["modis_reliability_ok"] == [0]


# ---------- one image over the field ----------

def test_a_clear_field_gives_the_mean_of_its_pixels():
    ndvi = np.array([[0.2, 0.4], [0.6, 0.8]])
    clear = np.ones((2, 2), bool)
    mask = np.array([[True, True], [False, False]])
    assert gr.field_observation(ndvi, clear, mask, 0.75) == pytest.approx({"ndvi": 0.3, "clear_fraction": 1.0, "n_pixels": 2})


def test_too_few_clear_pixels_give_no_value():
    ndvi = np.full((2, 2), 0.5)
    clear = np.array([[True, False], [False, False]])
    mask = np.ones((2, 2), bool)
    r = gr.field_observation(ndvi, clear, mask, 0.75)
    assert r["ndvi"] is None and r["clear_fraction"] == 0.25


def test_a_clear_pixel_without_ndvi_does_not_count_as_clear():
    ndvi = np.array([[0.5, np.nan], [0.5, 0.5]])
    r = gr.field_observation(ndvi, np.ones((2, 2), bool), np.ones((2, 2), bool), 0.75)
    assert r == pytest.approx({"ndvi": 0.5, "clear_fraction": 0.75, "n_pixels": 4})


def test_an_empty_field_mask_fails_loudly():
    with pytest.raises(ValueError, match="no pixel"):
        gr.field_observation(np.ones((2, 2)), np.ones((2, 2), bool), np.zeros((2, 2), bool), 0.75)


def test_the_field_mask_takes_pixels_whose_centres_are_inside():
    from rasterio.transform import from_origin
    t = from_origin(85.0, 28.0, 0.001, 0.001)                      # 0.001 deg pixels, lon/lat grid
    poly = [[85.0012, 27.9990], [85.0028, 27.9990], [85.0028, 27.9980], [85.0012, 27.9980]]
    m = gr.field_mask((5, 5), t, "EPSG:4326", poly)
    assert m.sum() == 2 and m[1, 1] and m[1, 2]                   # centres (85.0015, 27.9985) and (85.0025, 27.9985)


def test_modis_pixel_holding_a_point_in_the_sinusoidal_grid():
    R_EARTH = 6371007.181
    lat, lon = 27.690767, 85.441792
    x = R_EARTH * np.radians(lon) * np.cos(np.radians(lat))
    y = R_EARTH * np.radians(lat)
    xs = x + np.array([-463.3, -231.6, 0.4, 232.0])               # pixel centres about 231.66 m apart
    ys = y + np.array([463.0, 231.5, -0.3, -232.0])
    assert gr.modis_pixel(lat, lon, ys, xs) == (2, 2)


# ---------- daily series ----------

def _obs(pairs):
    return pd.DataFrame({"date": pd.to_datetime([d for d, _ in pairs]), "ndvi": [v for _, v in pairs]})


def test_daily_series_interpolates_between_clear_observations_and_reports_the_gap():
    d = gr.daily_series(_obs([("2020-01-01", 0.2), ("2020-01-11", 0.7)]), "2020-01-01", "2020-01-11")
    assert len(d) == 11
    assert d.loc[d["date"] == "2020-01-06", "ndvi"].item() == pytest.approx(0.45)
    assert (d["gap_days"] == [0] + [10] * 9 + [0]).all()


def test_no_value_before_the_first_or_after_the_last_observation():
    d = gr.daily_series(_obs([("2020-01-05", 0.2), ("2020-01-07", 0.4)]), "2020-01-01", "2020-01-10")
    assert d["ndvi"].isna().sum() == 7 and d.loc[d["date"] == "2020-01-06", "ndvi"].item() == pytest.approx(0.3)


def test_two_observations_on_one_day_are_averaged():
    d = gr.daily_series(_obs([("2020-01-01", 0.2), ("2020-01-01", 0.4), ("2020-01-03", 0.3)]), "2020-01-01", "2020-01-03")
    assert d["ndvi"].tolist() == pytest.approx([0.3, 0.3, 0.3])


# ---------- bare days ----------

def test_bare_days_per_year_and_month_with_uncertain_days():
    dates = pd.date_range("2020-01-01", "2020-02-29")
    d = pd.DataFrame({"date": dates, "ndvi": [0.1] * 31 + [0.5] * 29, "gap_days": [5] * 31 + [40] * 29})
    out = gr.bare_days(d, ndvi_max=0.25, uncertain_gap_days=30)
    assert out["by_year"]["2020"] == {"bare_days": 31, "days_with_value": 60, "uncertain_days": 29}
    assert out["by_month"]["2020-01"]["bare_days"] == 31 and out["by_month"]["2020-02"]["uncertain_days"] == 29


def test_a_day_without_a_value_is_neither_bare_nor_green():
    d = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "ndvi": [0.1, np.nan, 0.6], "gap_days": [0, 0, 0]})
    out = gr.bare_days(d, ndvi_max=0.25, uncertain_gap_days=30)
    assert out["by_year"]["2020"] == {"bare_days": 1, "days_with_value": 2, "uncertain_days": 0}


def test_hls_and_modis_pair_within_a_window():
    hls = _obs([("2014-01-01", 0.3), ("2014-02-01", 0.5)])
    mod = _obs([("2014-01-05", 0.35), ("2014-03-01", 0.6)])
    p = gr.pair_observations(hls, mod, max_days=8)
    assert len(p) == 1 and p.iloc[0]["ndvi_a"] == 0.3 and p.iloc[0]["ndvi_b"] == 0.35
