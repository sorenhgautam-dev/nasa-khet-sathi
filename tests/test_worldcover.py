"""Placeholder field (owner, 2026-11-12): the demo point is in Bhaktapur's old city, so a ~100 m square of
cropland is picked from ESA WorldCover 2021 inside a ~5 km box around it. Synthetic class grids."""
import numpy as np
import pytest
from rasterio.transform import from_origin

from pipeline.fetch import worldcover as wc

RES = 1 / 12000                                  # WorldCover pixel, degrees


def _at(t, col, row):
    return t.c + t.a * col, t.f + t.e * row


def test_box_around_a_point_is_about_5_km_each_way():
    b = wc.box_around(27.67, 85.43, half_km=5.0)
    assert b[1] == pytest.approx(27.67 - 0.04497, abs=1e-4) and b[3] == pytest.approx(27.67 + 0.04497, abs=1e-4)
    assert b[0] == pytest.approx(85.43 - 0.05077, abs=2e-4) and b[2] == pytest.approx(85.43 + 0.05077, abs=2e-4)


def _grid():
    a = np.full((300, 300), 50, dtype=np.uint8)  # built-up everywhere
    a[10:60, 10:60] = 40                         # big cropland patch far from the centre
    a[170:200, 160:195] = 40                     # cropland patch near the centre
    a[150:155, 150:155] = 40                     # tiny patch at the centre: too small
    return a, from_origin(85.0, 27.1, RES, RES)


def test_the_nearest_square_that_is_cropland_with_its_margin_is_chosen():
    a, t = _grid()
    target_lon, target_lat = _at(t, 150, 150)      # (col, row) -> (lon, lat) of the grid centre
    sq = wc.find_cropland_square(a, t, target_lon, target_lat, side_m=100, margin_m=30)
    r0, r1, c0, c1 = sq["window_rows_cols"]
    assert 170 <= r0 and r1 <= 200 and 160 <= c0 and c1 <= 195
    assert (a[r0:r1, c0:c1] == 40).all()
    assert sq["cropland_fraction"] == 1.0 and sq["distance_km"] > 0


def test_the_polygon_is_four_lon_lat_corners_about_100_m_apart():
    a, t = _grid()
    sq = wc.find_cropland_square(a, t, *_at(t, 150, 150), side_m=100, margin_m=30)
    poly = sq["polygon"]
    assert len(poly) == 4 and poly[0] != poly[-1]                    # contract: ring not closed
    lons, lats = [p[0] for p in poly], [p[1] for p in poly]
    assert (max(lats) - min(lats)) * 111.195 == pytest.approx(0.100, abs=0.002)
    assert (max(lons) - min(lons)) * 111.195 * np.cos(np.radians(sq["lat"])) == pytest.approx(0.100, abs=0.002)
    assert min(lons) < sq["lon"] < max(lons) and min(lats) < sq["lat"] < max(lats)


def test_no_cropland_square_fails_loudly():
    a = np.full((100, 100), 50, dtype=np.uint8)
    t = from_origin(85.0, 27.1, RES, RES)
    with pytest.raises(ValueError, match="cropland"):
        wc.find_cropland_square(a, t, *_at(t, 50, 50), side_m=100, margin_m=30)


# --- L5 (REVIEW_NOTES): a box that crosses a 3-degree tile edge needs every tile ------------------------------

def test_a_box_inside_one_tile_needs_that_tile_only():
    assert wc.tiles_for_box([85.379227, 27.625034, 85.480773, 27.714966]) == ["N27E084"]


def test_a_box_across_tile_edges_needs_every_tile_it_touches():
    assert wc.tiles_for_box([86.95, 29.95, 87.05, 30.05]) == ["N27E084", "N27E087", "N30E084", "N30E087"]
    assert wc.tiles_for_box([-0.05, -0.05, 0.05, 0.05]) == ["S03W003", "S03E000", "N00W003", "N00E000"]


def test_a_box_ending_exactly_on_a_tile_edge_does_not_take_the_next_tile():
    assert wc.tiles_for_box([85.0, 27.5, 87.0, 30.0]) == ["N27E084"]


def test_windows_from_two_tiles_are_mosaicked_on_the_shared_grid():
    left = np.full((4, 3), 40, dtype=np.uint8)
    right = np.full((4, 2), 50, dtype=np.uint8)
    tl = from_origin(86.99975, 30.0, RES, RES)                       # 3 pixels west of 87 E
    tr = from_origin(87.0, 30.0, RES, RES)
    a, t = wc.mosaic([(left, tl), (right, tr)])
    assert a.shape == (4, 5) and (a[:, :3] == 40).all() and (a[:, 3:] == 50).all()
    assert t.c == pytest.approx(86.99975) and t.f == pytest.approx(30.0)


def test_a_mosaic_never_leaves_an_unread_gap_as_a_class():
    a, _ = wc.mosaic([(np.full((2, 2), 40, dtype=np.uint8), from_origin(0.0, 1.0, RES, RES)),
                      (np.full((2, 2), 40, dtype=np.uint8), from_origin(3 * RES, 1.0, RES, RES))])
    assert a.shape == (2, 5) and (a[:, 2] == 0).all()                # 0 = WorldCover "no data"


def test_main_never_writes_a_placeholder_field_file(tmp_path, monkeypatch):
    """REVIEW_NOTES M11/H3: the field is config/fields/<id>.yaml; worldcover.py must not write a stale field."""
    a = np.full((300, 300), 40, dtype=np.uint8)
    t = from_origin(85.0, 27.1, RES, RES)
    monkeypatch.setattr(wc, "fetch", lambda field, box, data_dir=None: {"classes": a, "transform": t, "raw": tmp_path / "x.tif",
                                                                      "counts": {"Cropland": a.size}, "card": tmp_path / "c.json"})
    field = {"id": "t", "lat": 27.09, "lon": 85.01, "fetch_box": [85.0, 27.075, 85.025, 27.1],
             "origin_point": {"lat": 27.09, "lon": 85.01}}
    assert wc.main(["--field", "t"], field=field, data_dir=tmp_path) == 0
    assert not list(tmp_path.rglob("placeholder_field.json"))
    assert wc.main(["--field", "t", "--nearest-square"], field=field, data_dir=tmp_path) == 0
    import json
    out = json.loads((tmp_path / "clean" / "t" / "worldcover_nearest_square.json").read_text())
    assert "NOT the field" in out["status"]
