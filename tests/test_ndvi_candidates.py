"""HLS greenness for the placeholder search (owner, 2026-11-12): clear-sky NDVI from HLS-VI, monthly
composites, and candidate 60 m squares that are WorldCover cropland, away from buildings, and show crop
seasons in recent years. Synthetic arrays."""
import numpy as np
import pandas as pd
import pytest
from rasterio.transform import from_origin

from pipeline.diary import ndvi
from pipeline.fetch import placeholder as ph


def test_clear_pixels_have_no_cloud_shadow_snow_water_or_cirrus_bits():
    fm = np.array([0, 64, 128, 192, 1, 2, 4, 8, 16, 32, 255], dtype=float)   # aerosol bits 6-7 alone stay clear
    assert ndvi.clear_mask(fm).tolist() == [True, True, True, True] + [False] * 7


def test_ndvi_is_scaled_and_fills_become_gaps():
    out = ndvi.scale_ndvi(np.array([-19999.0, 5000.0, -1500.0]), fill=-19999.0, scale=0.0001)
    assert np.isnan(out[0]) and out[1] == pytest.approx(0.5) and out[2] == pytest.approx(-0.15)


def test_ndvi_outside_minus_one_to_one_fails_loudly():
    with pytest.raises(ValueError, match="NDVI"):
        ndvi.scale_ndvi(np.array([12000.0]), fill=-19999.0, scale=0.0001)


def test_monthly_composite_is_the_median_of_clear_values():
    stack = np.array([[[0.2]], [[0.6]], [[0.9]]])
    clear = np.array([[[True]], [[True]], [[False]]])
    months = ["2024-08", "2024-08", "2024-08"]
    comp, n, keys = ndvi.monthly_median(stack, clear, months)
    assert keys == ["2024-08"] and comp[0, 0, 0] == pytest.approx(0.4) and n[0, 0, 0] == 2


def _months(values_by_month):
    return pd.Series(values_by_month)


def test_two_crop_seasons_a_year_pass_and_a_bare_plot_fails():
    idx = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
    crop = {k: (0.7 if int(k[5:]) in (8, 9, 1, 2) else 0.2) for k in idx}           # monsoon and winter peaks
    bare = {k: 0.15 for k in idx}
    r = ph.season_check(pd.Series(crop), years=[2023, 2024, 2025], bare_ndvi=0.25)
    assert r["passes"] and r["min_peak"] == pytest.approx(0.7)
    assert not ph.season_check(pd.Series(bare), years=[2023, 2024, 2025], bare_ndvi=0.25)["passes"]


def test_a_field_built_over_in_the_last_year_fails():
    idx = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
    s = {k: (0.7 if int(k[5:]) in (8, 9, 1, 2) and k < "2025-03" else 0.15) for k in idx}
    r = ph.season_check(pd.Series(s), years=[2023, 2024, 2025], bare_ndvi=0.25)
    assert not r["passes"] and 2025 in r["failed_years"]


def test_squares_near_buildings_are_excluded():
    res = 1 / 12000
    a = np.full((200, 200), 40, dtype=np.uint8)
    a[100, 100] = 50                                  # one built-up pixel in the middle
    t = from_origin(85.0, 27.1, res, res)
    cands = ph.cropland_squares(a, t, lat=27.1, side_m=60, margin_m=30, clear_of_built_m=100)
    br = int(np.ceil(100 / (res * ph.KM_PER_DEG * 1000)))                        # 11 rows
    bc = int(np.ceil(100 / (res * ph.KM_PER_DEG * 1000 * np.cos(np.radians(27.1)))))   # 13 columns
    for c in cands:
        r0, r1, c0, c1 = c["window_rows_cols"]
        assert not (r0 - br <= 100 < r1 + br and c0 - bc <= 100 < c1 + bc)
    assert len(cands) > 0


def test_the_winter_rise_after_the_rice_harvest_is_reported():
    idx = [f"{y}-{m:02d}" for y in (2022, 2023) for m in range(1, 13)]
    s = {k: 0.3 for k in idx}
    s.update({"2022-11": 0.25, "2023-01": 0.7, "2023-08": 0.8})        # sown after harvest, green by January
    r = ph.season_check(pd.Series(s), years=[2023], bare_ndvi=0.25)
    assert r["winter_rise"] == [pytest.approx(0.45)]


def test_the_chosen_field_is_never_labelled_rejected_and_earlier_squares_come_from_the_config():
    """REVIEW_NOTES H3: the plot used to call whatever demo.yaml holds the 'rejected' construction plot."""
    from pipeline.fetch.worldcover import square_polygon
    field = {"lat": 27.690767, "lon": 85.441792, "polygon": square_polygon(27.690767, 85.441792, 60),
             "earlier_placeholders": [
                 {"lat": 27.6785, "lon": 85.427417, "side_m": 100, "why_replaced": "construction plot"},
                 {"lat": 27.690542, "lon": 85.441792, "side_m": 60, "why_replaced": "river at its southern edge"}]}
    refs = ph.reference_squares(field)
    chosen, first, second = refs
    assert chosen["role"] == "chosen" and (chosen["lat"], chosen["lon"]) == (27.690767, 85.441792)
    assert chosen["side_m"] == pytest.approx(60, abs=0.5) and "rejected" not in chosen["label"].lower()
    assert first["role"] == "earlier" and (first["lat"], first["lon"], first["side_m"]) == (27.6785, 85.427417, 100)
    assert "construction plot" in first["label"] and "river" in second["label"]


def test_a_field_without_earlier_placeholders_has_only_the_chosen_square():
    from pipeline.fetch.worldcover import square_polygon
    refs = ph.reference_squares({"lat": 27.0, "lon": 85.0, "polygon": square_polygon(27.0, 85.0, 100)})
    assert [r["role"] for r in refs] == ["chosen"] and refs[0]["side_m"] == pytest.approx(100, abs=0.5)
