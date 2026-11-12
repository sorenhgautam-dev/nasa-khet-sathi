"""SoilGrids 2.0 for the whole fetch box through ISRIC's WCS (the REST point service was down,
2026-11-12), and the field's profile from the cell holding it, or the nearest cell where EVERY map has a
prediction (REVIEW_NOTES M5: nodata read per map, never '0 = no prediction' taken as a value; bounds
checked; units checked against ISRIC's own unit blocks)."""
import json

import numpy as np
import pytest
from rasterio.transform import from_origin

from pipeline.fetch import soilgrids_wcs as sw
from pipeline.fetch.guards import DataGuardError

T = from_origin(85.40, 27.70, 0.0025, 0.0025)
UNITS = {  # verbatim from the live REST response, 2026-11-12 (also in tests/test_soilgrids.py)
    "bdod": {"d_factor": 100, "mapped_units": "cg/cm³", "target_units": "kg/dm³", "uncertainty_unit": ""},
    "clay": {"d_factor": 10, "mapped_units": "g/kg", "target_units": "%", "uncertainty_unit": ""},
    "sand": {"d_factor": 10, "mapped_units": "g/kg", "target_units": "%", "uncertainty_unit": ""},
    "soc": {"d_factor": 10, "mapped_units": "dg/kg", "target_units": "g/kg", "uncertainty_unit": ""},
    "wv0033": {"d_factor": 10, "mapped_units": "(10-2 cm³/cm³)*10", "target_units": "10-2 cm³/cm³", "uncertainty_unit": ""},
    "wv1500": {"d_factor": 10, "mapped_units": "(10-2 cm³/cm³)*10", "target_units": "10-2 cm³/cm³", "uncertainty_unit": ""},
}


def test_d_factor_conversion_matches_the_rest_service():
    assert sw.convert("wv0033", 315) == pytest.approx(0.315)          # (10-2 cm3/cm3)*10 -> m3/m3
    assert sw.convert("clay", 237) == pytest.approx(23.7)              # g/kg -> %
    assert sw.convert("bdod", 123) == pytest.approx(1.23)              # cg/cm3 -> kg/dm3
    assert sw.convert("soc", 283) == pytest.approx(28.3)               # dg/kg -> g/kg


def test_the_factors_are_checked_against_isrics_unit_blocks():
    assert sw.check_units(UNITS) == {p: u["mapped_units"] for p, u in UNITS.items()}
    with pytest.raises(DataGuardError, match="bdod"):
        sw.check_units(dict(UNITS, bdod=dict(UNITS["bdod"], d_factor=10)))
    with pytest.raises(DataGuardError, match="clay"):
        sw.check_units(dict(UNITS, clay=dict(UNITS["clay"], target_units="g/kg")))


def test_a_declared_nodata_marks_no_prediction_and_a_zero_is_then_a_value():
    assert sw.valid_mask(np.array([-32768, 0, 120]), nodata=-32768).tolist() == [False, True, True]


def test_without_a_declared_nodata_a_zero_is_never_taken_as_a_value():
    assert sw.valid_mask(np.array([0, 120]), nodata=None).tolist() == [False, True]


def test_a_cell_has_a_prediction_only_where_every_map_has_one():
    wv = np.array([[300, 300]])
    sand = np.array([[0, 250]])                                        # 0 sand where the water maps have values
    m = sw.prediction_mask({("wv0033", "0-5cm"): wv, ("sand", "0-5cm"): sand}, {("wv0033", "0-5cm"): None,
                                                                                ("sand", "0-5cm"): None})
    assert m.tolist() == [[False, True]]


def test_the_cell_holding_the_field_is_used_when_it_has_values():
    r = sw.pick_cell(np.ones((8, 8), dtype=bool), T, lat=27.6912, lon=85.4063, max_m=1000)
    assert (r["row"], r["col"]) == (3, 2) and r["distance_m"] == 0


def test_a_cell_without_a_prediction_falls_back_to_the_nearest_within_the_limit():
    valid = np.ones((8, 8), dtype=bool)
    valid[3, 2] = False
    r = sw.pick_cell(valid, T, lat=27.6912, lon=85.4063, max_m=1000)
    assert (r["row"], r["col"]) != (3, 2) and 0 < r["distance_m"] <= 400


def test_no_cell_with_values_within_the_limit_fails_loudly():
    with pytest.raises(ValueError, match="no SoilGrids cell"):
        sw.pick_cell(np.zeros((8, 8), dtype=bool), T, lat=27.6912, lon=85.4063, max_m=1000)


def test_the_error_says_how_far_the_nearest_cell_with_values_is():
    valid = np.zeros((8, 8), dtype=bool)
    valid[0, 7] = True
    with pytest.raises(ValueError, match=r"nearest is \d+ m away"):
        sw.pick_cell(valid, T, lat=27.6912, lon=85.4063, max_m=200)


@pytest.mark.parametrize("lat,lon", [(27.71, 85.41), (27.69, 85.39), (27.67, 85.41), (27.69, 85.43)])
def test_a_field_outside_the_maps_fails_loudly_instead_of_wrapping(lat, lon):
    with pytest.raises(ValueError, match="outside"):                # north, west, south, east of an 8 x 8 grid
        sw.pick_cell(np.ones((8, 8), dtype=bool), T, lat=lat, lon=lon, max_m=1000)


VALUES = {"wv0033": 330, "wv1500": 180, "sand": 380, "clay": 203, "soc": 250, "bdod": 135}


def _maps(raw, shape=(6, 6), transform=T, nodata=None):
    import rasterio
    raw.mkdir(parents=True, exist_ok=True)
    for p, v in VALUES.items():
        for d in sw.DEPTHS:
            a = np.full(shape, v, dtype="int16")
            a[2, 2] = 0                                                  # the field's cell: no prediction anywhere
            if p == "sand":
                a[2, 3] = 0                                              # nearest cell: water maps only, sand missing
            with rasterio.open(raw / f"{p}_{d}_mean.tif", "w", driver="GTiff", height=shape[0], width=shape[1],
                               count=1, dtype="int16", crs="EPSG:4326", transform=transform, nodata=nodata) as dst:
                dst.write(a, 1)


def test_the_profile_comes_from_the_nearest_cell_where_every_map_has_values(tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "requests", None)                 # from the cache: no network at all
    _maps(tmp_path / "raw" / "soilgrids" / "t" / "wcs")
    field = {"id": "t", "lat": 27.6937, "lon": 85.4062, "fetch_box": [85.40, 27.685, 85.415, 27.70]}   # cell (2, 2)
    r = sw.fetch(field, data_dir=tmp_path, rules={"soilgrids": {"nearest_cell_max_m": 3000}}, offline=True)
    assert (r["cell"]["row"], r["cell"]["col"]) not in [(2, 2), (2, 3)] and r["cell"]["distance_m"] > 0
    assert r["df"]["sand_pct"].tolist() == [38.0] * 6 and r["df"]["theta_fc_m3m3"].tolist() == [0.33] * 6
    card = json.loads(r["card"].read_text())
    assert card["location"]["distance_m"] == r["cell"]["distance_m"]
    assert (f"soil from the nearest SoilGrids cell with a prediction, {r['cell']['distance_m']} m away, "
            "not the field's own") in card["notes"]
    assert card["location"]["box_cells_without_prediction"] == 2
    assert all(v["nodata"] is None for v in card["raw_attrs"]["maps"].values())


def test_offline_refuses_to_download_a_missing_map(tmp_path):
    field = {"id": "t", "lat": 27.6937, "lon": 85.4062, "fetch_box": [85.40, 27.685, 85.415, 27.70]}
    with pytest.raises(FileNotFoundError, match="offline"):
        sw.fetch(field, data_dir=tmp_path, rules={"soilgrids": {"nearest_cell_max_m": 3000}}, offline=True)
